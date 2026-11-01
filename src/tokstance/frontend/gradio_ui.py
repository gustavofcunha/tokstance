"""Interface Gradio completa: Login, Cadastro, Hub Inicial, Criador, Rotulacao e Console Admin (versao inicial do frontend)."""

from html import escape
import json
import time
from typing import Any, Dict, List, Optional, Tuple
import gradio as gr
import pandas as pd

from tokstance.backend.domain.models import (
    NOME_TAREFA_PADRAO,
    OPCOES_TAREFA_PADRAO,
    PERGUNTA_TAREFA_PADRAO,
    chave_par_rotulos,
    gerar_combinacoes_rotulos,
    limpar_usuarios,
)
from tokstance.backend.repositories.database import BancoDadosSQLite
from tokstance.backend.repositories.study_repo import RepositorioEstudo
from tokstance.backend.repositories.user_repo import RepositorioUsuarios
from tokstance.backend.security.validators import gerar_codigo_convite
from tokstance.backend.services.admin_service import ServicoAdministracao
from tokstance.backend.services.auth_service import ServicoAutenticacao
from tokstance.backend.services.queue_service import ServicoFilaAnotacao
from tokstance.config import ARQUIVO_VIDEOS, ARQUIVO_VIDEOS_RESERVA
from tokstance.frontend.components import (
    agreement_summary,
    generate_progress_bar,
    render_video_card,
    video_outputs,
)
from tokstance.frontend.theme import (
    APP_CSS,
    COR_PRIMARIA,
    JS_FORCAR_MODO_CLARO,
    obter_tema_branco,
)


def renderizar_hub_cards_html(tarefas_admin: List[Dict[str, Any]], tarefas_rotulador: List[Dict[str, Any]]) -> Tuple[str, str]:
    """Gera o HTML dos cartoes do Hub Inicial para tarefas de administrador e de rotulador."""
    #cartoes de administrador
    if not tarefas_admin:
        html_admin = "<p class='muted'>Você ainda não criou nenhuma tarefa. Clique no botão '+ Criar Nova Tarefa' acima para iniciar.</p>"
    else:
        cards_admin = []
        for t in tarefas_admin:
            t_id = t.get("tarefa_id", "")
            titulo = escape(str(t.get("titulo", f"Tarefa #{t_id}")))
            convite = escape(str(t.get("codigo_convite", "")))
            vagas = t.get("vagas_ocupadas", 0)
            total_v = t.get("numero_vagas", 0)
            prog = t.get("progresso_percentual", 0.0)
            cards_admin.append(f"""
            <div class='hub-card admin'>
                <div style='display: flex; justify-content: space-between; align-items: flex-start; gap: 10px;'>
                    <h4>{titulo}</h4>
                    <span class='hub-badge admin'>Administrador</span>
                </div>
                <div class='hub-card-meta'>
                    <div>Código de Convite: <span class='config-val-badge convite'>{convite}</span></div>
                    <div>Vagas preenchidas: <strong>{vagas} de {total_v}</strong></div>
                    <div>Progresso da rodada: <strong>{prog:.0f}%</strong></div>
                </div>
            </div>
            """)
        html_admin = f"<div class='hub-grid'>{''.join(cards_admin)}</div>"

    #cartoes de rotulador
    if not tarefas_rotulador:
        html_rotulador = "<p class='muted'>Você ainda não está inscrito em nenhuma tarefa para rotular. Use o campo de código de convite abaixo para entrar.</p>"
    else:
        cards_rot = []
        for t in tarefas_rotulador:
            t_id = t.get("tarefa_id", "")
            titulo = escape(str(t.get("titulo", f"Tarefa #{t_id}")))
            pos = t.get("posicao_concluida", 0)
            tot = t.get("total_videos", 0)
            pct = int((pos / tot) * 100) if tot > 0 else 100
            status_txt = "Concluída" if pos >= tot and tot > 0 else f"{pos} de {tot} vídeos ({pct}%)"
            cards_rot.append(f"""
            <div class='hub-card'>
                <div style='display: flex; justify-content: space-between; align-items: flex-start; gap: 10px;'>
                    <h4>{titulo}</h4>
                    <span class='hub-badge rotulador'>Rotulador</span>
                </div>
                <div class='hub-card-meta'>
                    <div>Status da sua fila: <strong>{status_txt}</strong></div>
                </div>
            </div>
            """)
        html_rotulador = f"<div class='hub-grid'>{''.join(cards_rot)}</div>"

    return html_admin, html_rotulador


def renderizar_configuracao_admin_html(tarefa_meta: Dict[str, Any]) -> str:
    """Renderiza a configuracao vigente da tarefa em cartao HTML de alto contraste sem blocos escuros."""
    t_id = tarefa_meta.get("tarefa_id", "")
    convite = escape(str(tarefa_meta.get("codigo_convite", "")))
    pergunta = escape(str(tarefa_meta.get("pergunta", "")))
    opcoes = escape(", ".join(str(op) for op in tarefa_meta.get("opcoes_posicao", [])))
    vagas = tarefa_meta.get("numero_vagas", 0)
    overlap = tarefa_meta.get("percentual_sobreposicao", 0)

    return f"""
    <div class="admin-config-card">
        <div class="admin-config-title">Configuração Vigente da Rodada (Somente Leitura)</div>
        <div class="admin-config-grid">
            <div class="config-item"><span class="config-label">ID da Tarefa:</span> <span class="config-val-badge">#{t_id}</span></div>
            <div class="config-item"><span class="config-label">Código de Convite:</span> <span class="config-val-badge convite">{convite}</span></div>
            <div class="config-item"><span class="config-label">Vagas de Rotuladores:</span> <span class="config-val-badge">{vagas}</span></div>
            <div class="config-item"><span class="config-label">Sobreposição (Overlap):</span> <span class="config-val-badge">{overlap}%</span></div>
            <div class="config-item full-width"><span class="config-label">Pergunta Norteadora:</span> <div class="config-val-text">{pergunta}</div></div>
            <div class="config-item full-width"><span class="config-label">Opções de Resposta:</span> <div class="config-val-text">{opcoes}</div></div>
        </div>
    </div>
    """


def gerar_tabela_penalidades_df(opcoes_texto: str) -> pd.DataFrame:
    """Gera um DataFrame com as combinacoes de pares e pesos de penalidade a partir do texto das opcoes."""
    opcoes = limpar_usuarios(opcoes_texto.splitlines())
    if len(opcoes) < 2:
        return pd.DataFrame(columns=["Opção A", "Opção B", "Penalidade"])

    pesos_conhecidos = {
        "Contra|Neutro": 1.0,
        "Neutro|A Favor": 1.0,
        "A Favor|Neutro": 1.0,
        "Contra|A Favor": 4.0,
        "A Favor|Contra": 4.0,
        "Vídeo não relacionado ao target|Contra": 3.0,
        "Vídeo não relacionado ao target|Neutro": 3.0,
        "Vídeo não relacionado ao target|A Favor": 3.0,
    }

    combinacoes = gerar_combinacoes_rotulos(opcoes, distancias_existentes=pesos_conhecidos)
    linhas = []
    for chave, peso in combinacoes.items():
        partes = chave.split("|", maxsplit=1)
        if len(partes) == 2:
            linhas.append({
                "Opção A": partes[0],
                "Opção B": partes[1],
                "Penalidade": float(peso),
            })
    return pd.DataFrame(linhas)


def converter_df_para_distancias(df_penalidades: Any) -> Dict[str, float]:
    """Converte o DataFrame de penalidades do wizard em um dicionario com chaves no formato OpcaoA|OpcaoB."""
    distancias: Dict[str, float] = {}
    if df_penalidades is None:
        return distancias
    if not isinstance(df_penalidades, pd.DataFrame):
        try:
            df_penalidades = pd.DataFrame(df_penalidades)
        except Exception:
            return distancias

    if df_penalidades.empty or not {"Opção A", "Opção B", "Penalidade"}.issubset(df_penalidades.columns):
        return distancias

    for _, row in df_penalidades.iterrows():
        a = str(row["Opção A"]).strip()
        b = str(row["Opção B"]).strip()
        if a and b and a != b:
            chave = chave_par_rotulos(a, b)
            try:
                peso = float(row["Penalidade"])
            except (ValueError, TypeError):
                peso = 1.0
            distancias[chave] = peso
    return distancias


def construir_interface(
    servico_auth: Optional[ServicoAutenticacao] = None,
    servico_fila: Optional[ServicoFilaAnotacao] = None,
    servico_admin: Optional[ServicoAdministracao] = None,
) -> gr.Blocks:
    """Constroi a aplicacao visual Blocks com suporte a autenticacao, hub, criador e workspace."""
    banco = BancoDadosSQLite()
    repo_u = RepositorioUsuarios(banco)
    repo_e = RepositorioEstudo(banco, repo_u)

    auth = servico_auth or ServicoAutenticacao(banco, repo_u, repo_e)
    fila = servico_fila or ServicoFilaAnotacao(banco, repo_u, repo_e)
    admin = servico_admin or ServicoAdministracao(banco, repo_u, repo_e)

    auth.garantir_conta_admin_padrao()

    with gr.Blocks(title="TokStance!") as app:
        #estilos css globais injetados para compatibilidade com gradio 5 e 6
        gr.HTML(f"<style>{APP_CSS}</style>")

        #estado completo da sessao do usuario
        estado_sessao = gr.State({
            "usuario_id": None,
            "nome_usuario": "",
            "tarefa_ativa_id": None,
            "login_time": 0.0,
            "start_time": 0.0,
            "assignment_id": "",
            "pergunta_template": "",
            "opcoes_posicao": [],
            "previous_target": "",
        })

        with gr.Column(elem_classes="shell"):
            gr.HTML("""
            <div class='brand-header'>
                <div style='display: flex; align-items: baseline; gap: 12px;'>
                    <h1>TokStance!</h1>
                    <span style='font-size: 13px; font-weight: 700; color: #9c0014; background: #fff0f2; border: 1px solid #ffd6dc; padding: 2px 8px; border-radius: 12px;'>v1.0</span>
                </div>
                <p>Plataforma open source de rotulação e análise de posicionamento em vídeos</p>
            </div>
            """)

            # ==================================================================
            # 1. TELA DE ACESSO (LOGIN E CADASTRO)
            # ==================================================================
            with gr.Column(visible=True) as painel_acesso:
                with gr.Column(elem_classes="auth-card"):
                    gr.HTML("""
                    <div style='text-align: center; margin-bottom: 18px;'>
                        <div style='display: inline-block; padding: 4px 12px; background: #fff0f2; border: 1px solid #ffd6dc; border-radius: 20px; color: #9c0014; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px;'>Acesso ao Sistema</div>
                        <h2 style='margin: 0 0 4px 0; color: #0f172a; font-size: 22px; font-weight: 800; letter-spacing: -0.02em;'>Bem-vindo ao TokStance</h2>
                        <p style='color: #475569; font-size: 14px; margin: 0;'>Entre com suas credenciais ou crie uma conta para participar</p>
                    </div>
                    """)

                    with gr.Tab("Entrar"):
                        login_usuario = gr.Textbox(label="Nome de Usuário", placeholder="Digite seu usuário", autofocus=True)
                        login_senha = gr.Textbox(label="Senha de Acesso", type="password", placeholder="Digite sua senha")
                        btn_login = gr.Button("Entrar no Sistema", elem_classes="ufmg-btn", size="lg")

                    with gr.Tab("Criar Conta"):
                        cadastro_usuario = gr.Textbox(label="Escolha seu Nome de Usuário", placeholder="Ex: pesquisador_1")
                        cadastro_senha = gr.Textbox(label="Senha de Acesso", type="password", placeholder="Mínimo 6 caracteres")
                        cadastro_confirma = gr.Textbox(label="Confirme a Senha", type="password", placeholder="Repita a senha")
                        cadastro_convite = gr.Textbox(label="Código de Convite (opcional)", placeholder="Ex: TOKSTANCE-2026")
                        btn_cadastrar = gr.Button("Cadastrar e Acessar", elem_classes="ufmg-btn", size="lg")

                    mensagem_acesso = gr.Markdown()

            # ==================================================================
            # 2. HUB INICIAL DE TAREFAS (MULTI-ROLE)
            # ==================================================================
            with gr.Column(visible=False) as painel_hub:
                with gr.Row(elem_classes="hub-header-bar"):
                    hub_saudacao = gr.HTML()
                    with gr.Row(scale=0):
                        btn_ir_criar_tarefa = gr.Button("+ Criar Nova Tarefa", elem_classes="ufmg-btn")
                        btn_logout = gr.Button("Encerrar Sessão", elem_classes="error-btn")

                # Secoes de tarefas organizadas lado a lado em duas colunas responsivas
                with gr.Row(elem_classes="hub-two-col"):
                    # Secao de tarefas de administrador
                    with gr.Column(scale=1, elem_classes="hub-section-box"):
                        gr.HTML("""
                        <div style="margin-bottom: 12px;">
                            <h3 style="margin: 0; font-size: 19px; font-weight: 800; color: #0f172a;">Tarefas sob sua Administração</h3>
                            <p style="margin: 4px 0 0; font-size: 14px; color: #475569;">Rodadas de anotação criadas e coordenadas por você</p>
                        </div>
                        """)
                        hub_admin_cards_html = gr.HTML()
                        with gr.Row(elem_classes="hub-action-row"):
                            select_tarefa_admin = gr.Dropdown(
                                label="Selecionar Tarefa para Gerenciar",
                                choices=[],
                                value=None,
                                interactive=True,
                                scale=4,
                            )
                            btn_abrir_admin = gr.Button("Abrir Console de Administração", elem_classes=["ufmg-btn", "hub-btn"], scale=2)
                            btn_excluir_tarefa_hub = gr.Button("🗑️ Excluir Tarefa", elem_classes=["error-btn", "hub-btn"], scale=1)

                    # Secao de tarefas de rotulador
                    with gr.Column(scale=1, elem_classes="hub-section-box"):
                        gr.HTML("""
                        <div style="margin-bottom: 12px;">
                            <h3 style="margin: 0; font-size: 19px; font-weight: 800; color: #0f172a;">Tarefas Atribuídas a Você para Rotular</h3>
                            <p style="margin: 4px 0 0; font-size: 14px; color: #475569;">Fila individual de vídeos atribuídos para sua análise</p>
                        </div>
                        """)
                        hub_rotulador_cards_html = gr.HTML()
                        with gr.Row(elem_classes="hub-action-row"):
                            select_tarefa_rotulador = gr.Dropdown(
                                label="Selecionar Tarefa para Rotular",
                                choices=[],
                                value=None,
                                interactive=True,
                                scale=4,
                            )
                            btn_abrir_rotulacao = gr.Button("Rotular Vídeos da Tarefa", elem_classes=["ufmg-btn", "hub-btn"], scale=2)

                # Secao de ingresso por codigo de convite (barra horizontal compacta para widescreen)
                with gr.Column(elem_classes="hub-join-box"):
                    with gr.Row(elem_classes="hub-join-row"):
                        with gr.Column(scale=2, min_width=260):
                            gr.HTML("""
                            <div>
                                <h4 style="margin: 0; font-size: 16px; font-weight: 800; color: #0f172a;">🔑 Ingressar com Código de Convite</h4>
                                <p style="margin: 2px 0 0; font-size: 13px; color: #475569;">Insira o código compartilhado pelo administrador para assumir uma vaga</p>
                            </div>
                            """)
                        with gr.Row(scale=3, elem_classes="hub-action-row"):
                            input_codigo_convite = gr.Textbox(
                                label="Código de Convite",
                                placeholder="Ex: TOKSTANCE-2026",
                                scale=4,
                            )
                            btn_entrar_convite = gr.Button("Entrar na Tarefa", elem_classes=["ufmg-btn", "hub-btn"], scale=2)
                    hub_mensagem = gr.Markdown()

            # ==================================================================
            # 3. TELA DE CRIACAO DE TAREFA (WIZARD)
            # ==================================================================
            with gr.Column(visible=False, elem_classes="admin-panel") as painel_wizard:
                with gr.Row(elem_classes="admin-header"):
                    gr.Markdown("## Criador de Nova Tarefa de Pesquisa")
                    with gr.Row(elem_classes="admin-actions"):
                        btn_voltar_hub_wizard = gr.Button("← Voltar ao Hub", elem_classes="error-btn")

                with gr.Column(elem_classes="form-wizard-card"):
                    with gr.Row(elem_classes="wizard-grid"):
                        # Coluna Esquerda: Questoes da pesquisa, rotulos e vagas
                        with gr.Column(scale=1, elem_classes="wizard-col"):
                            gr.Markdown("### 1. Definição da Pergunta e Rótulos")
                            wizard_titulo = gr.Textbox(
                                label="Título da Tarefa",
                                value=NOME_TAREFA_PADRAO,
                                placeholder="Ex: Detecção de Posição em Eleições",
                            )
                            wizard_pergunta = gr.Textbox(
                                label="Pergunta Norteadora da Anotação (use {target} para interpolar o tema)",
                                value=PERGUNTA_TAREFA_PADRAO,
                                placeholder='Com relação ao target "{target}", como você classifica a posição deste vídeo?',
                            )
                            wizard_opcoes = gr.Textbox(
                                label="Opções de Resposta (uma por linha)",
                                value="\n".join(OPCOES_TAREFA_PADRAO),
                                lines=4,
                            )
                            btn_atualizar_pares = gr.Button("Atualizar Matriz de Combinações", elem_classes="error-btn")

                            gr.Markdown("### 3. Vagas, Sobreposição e Código de Convite")
                            with gr.Row():
                                wizard_vagas = gr.Slider(
                                    label="Número de Vagas de Rotuladores",
                                    minimum=1,
                                    maximum=20,
                                    value=3,
                                    step=1,
                                )
                                wizard_overlap = gr.Slider(
                                    label="Percentual de Sobreposição (Overlap %)",
                                    minimum=0.0,
                                    maximum=100.0,
                                    value=20.0,
                                    step=5.0,
                                )
                            with gr.Row():
                                wizard_convite = gr.Textbox(
                                    label="Código de Convite da Tarefa",
                                    value=gerar_codigo_convite(),
                                    scale=3,
                                )
                                btn_copiar_codigo = gr.Button("📋 Copiar Código", elem_classes="error-btn", scale=1)
                                btn_gerar_novo_codigo = gr.Button("Gerar Novo Código", elem_classes="error-btn", scale=1)

                            wizard_admin_como_rotulador = gr.Checkbox(
                                label="Inscrever-me automaticamente como rotulador na Vaga 1 desta tarefa",
                                value=True,
                            )

                        # Coluna Direita: Matriz par-a-par de distancias ordinais e pool de videos
                        with gr.Column(scale=1, elem_classes="wizard-col"):
                            gr.Markdown("### 2. Matriz Par-a-Par de Penalidades (Distâncias)")
                            gr.Markdown("Edite os pesos de discordância para o cálculo do Alfa de Krippendorff ordinal:")
                            tabela_penalidades_inicial = gerar_tabela_penalidades_df("\n".join(OPCOES_TAREFA_PADRAO))
                            wizard_tabela_penalidades = gr.Dataframe(
                                value=tabela_penalidades_inicial,
                                headers=["Opção A", "Opção B", "Penalidade"],
                                datatype=["str", "str", "number"],
                                interactive=True,
                                elem_classes="pairwise-penalty-table",
                                max_height=220,
                            )

                            gr.Markdown("### 4. Pool de Vídeos e Divisão Principal / Reserva")
                            with gr.Row():
                                wizard_arquivo_videos = gr.File(
                                    label="Upload do Arquivo CSV de Vídeos (opcional: se vazio, utiliza a coleção padrão do sistema)",
                                    file_types=[".csv"],
                                    scale=2,
                                )
                                wizard_qtd_principal = gr.Number(
                                    label="Quantidade de Vídeos para Anotação Principal (0 = automático)",
                                    info="Define a quantidade de vídeos únicos da rodada que serão distribuídos para os rotuladores. Deixe 0 para calcular automaticamente o máximo possível com base no pool e na taxa de sobreposição (overlap).",
                                    value=0,
                                    precision=0,
                                    scale=1,
                                )

                    with gr.Row(elem_classes="wizard-submit-row"):
                        btn_submeter_tarefa = gr.Button("Criar Tarefa e Atribuir Vagas", elem_classes=["ufmg-btn", "wizard-submit-btn"])
                    wizard_mensagem = gr.Markdown()

            # ==================================================================
            # 4. TELA DE ROTULACAO (WORKSPACE DO ROTULADOR)
            # ==================================================================
            with gr.Column(visible=False, elem_classes="labeler-panel") as painel_rotulador:
                with gr.Row(elem_classes="labeler-header-bar"):
                    rotulador_tarefa_meta_topo = gr.HTML("<div class='workspace-header-title'><h2>Workspace de Rotulação</h2></div>", scale=1)
                    btn_voltar_hub_rotulacao = gr.Button("← Sair do Workspace", elem_classes=["ufmg-btn", "labeler-exit-btn"], scale=0)

                with gr.Column(elem_classes="labeler-workspace-container"):
                    with gr.Column(visible=False, elem_classes="sensitive-warning-wrapper") as painel_aviso_sensivel:
                        with gr.Column(elem_classes="sensitive-warning-card"):
                            gr.HTML("""
                                <div class="sensitive-warning-header">
                                    <div class="sensitive-warning-badge">⚠️ Aviso de Conteúdo</div>
                                    <h2>Possível Conteúdo Sensível ou Nocivo</h2>
                                </div>
                                <div class="sensitive-warning-body">
                                    <p>O conteúdo dos vídeos e seus metadados (tema, descrição e transcrição) podem envolver assuntos sensíveis, controversos ou potencialmente desconfortáveis.</p>
                                    <p>Deseja visualizar o material completo e prosseguir com a rotulação?</p>
                                </div>
                            """)
                            with gr.Row(elem_classes="sensitive-warning-actions"):
                                btn_continuar_sensivel = gr.Button("Continuar", elem_classes=["ufmg-btn", "sensitive-btn-continue"])
                                btn_parar_sensivel = gr.Button("Parar de rotular", elem_classes=["error-btn", "sensitive-btn-stop"])

                    with gr.Row(elem_classes="labeler-layout"):
                        with gr.Column(scale=6, min_width=320, elem_classes="video-column"):
                            rotulador_video_html = gr.HTML()

                        with gr.Column(scale=5, min_width=280, elem_classes="labeler-controls-column"):
                            rotulador_cabecalho = gr.HTML(elem_classes="labeler-header-badge-wrapper")
                            rotulador_progresso = gr.HTML()

                            with gr.Column(visible=False, elem_classes="annotation-controls") as painel_controles_anotacao:
                                gr.HTML("<div class='labeler-warning-stack'><div>⏳ O player do TikTok pode demorar alguns segundos para carregar.</div><div>🔊 Certifique-se de que o som do vídeo está habilitado clicando no ícone de som do player do TikTok.</div></div>")

                                rotulador_pergunta_html = gr.HTML()
                                rotulador_radio = gr.Radio(choices=[], label="Selecione uma opção:", elem_classes="wrap-radio")

                                btn_salvar_resposta = gr.Button("Salvar Resposta e Avançar", elem_classes="ufmg-btn")
                                btn_erro_video = gr.Button("⚠️ O vídeo não carregou", elem_classes="error-btn")

                                rotulador_mensagem = gr.Markdown(elem_classes="warning-text")

            # ==================================================================
            # 5. TELA DE ADMINISTRACAO (CONSOLE DA TAREFA)
            # ==================================================================
            with gr.Column(visible=False, elem_classes="admin-panel") as painel_admin:
                with gr.Row(elem_classes="admin-header"):
                    admin_titulo_tarefa = gr.Markdown("## Console de Administração da Tarefa")
                    with gr.Row(elem_classes="admin-actions"):
                        btn_excluir_tarefa_admin = gr.Button("🗑️ Excluir esta Tarefa", elem_classes="error-btn")
                        btn_voltar_hub_admin = gr.Button("← Voltar ao Hub", elem_classes="error-btn")

                admin_configuracao_view = gr.HTML(elem_classes="admin-configuration")
                admin_status_view = gr.Markdown(elem_classes="admin-status")

                gr.Markdown("### Dados Coletados e Análise Operacional")
                admin_dashboard_html = gr.HTML()

                with gr.Row(elem_classes="admin-downloads"):
                    admin_download_resultados = gr.File(label="Resultados Anotação (CSV)")
                    admin_download_logs = gr.File(label="Metadados e Tempos (CSV)")
                    admin_download_erros = gr.File(label="Vídeos com Erro (CSV)")
                    admin_download_concordancia = gr.File(label="Concordância (JSON)")

                gr.Markdown("### Auditoria de Atribuições", elem_classes="admin-audit")
                admin_tabela_atribuicoes = gr.Dataframe(
                    headers=["assignment_version", "assignment_id", "labeler", "video_id", "url", "target", "video_description", "voice_to_text", "video_duration"],
                    interactive=False,
                    elem_classes="assignment-table",
                    max_height=380,
                    wrap=True,
                )

            # Rodapé Institucional e Metadados do Projeto
            gr.HTML("""
            <div class="app-footer">
                <div>
                    <strong>TokStance</strong> · Plataforma open source de rotulação e análise de posicionamento em vídeos
                </div>
                <div class="footer-links">
                    <span>Desenvolvido por: <strong>Gustavo Cunha</strong></span>
                    <span>•</span>
                    <a href="mailto:gustavocunha@dcc.ufmg.br">gustavocunha@dcc.ufmg.br</a>
                    <span>•</span>
                    <a href="https://github.com/gustavofcunha/tokstance" target="_blank" rel="noopener noreferrer">GitHub: gustavofcunha/tokstance</a>
                </div>
            </div>
            """)

        # ======================================================================
        # FUNCOES DE CONTROLE E TRANSICAO DE TELAS
        # ======================================================================
        def atualizar_visoes_hub(sessao: Dict[str, Any]) -> Tuple[Any, Any, str, str, str]:
            u_id = sessao.get("usuario_id")
            if not u_id:
                return gr.update(choices=[], value=None), gr.update(choices=[], value=None), "", "", ""
            painel = auth.obter_painel_usuario(int(u_id))
            admin_tarefas = painel["tarefas_administrador"]
            rot_tarefas = painel["tarefas_rotulador"]

            opcoes_admin = [(f"{t['titulo']} (ID: {t['tarefa_id']})", str(t["tarefa_id"])) for t in admin_tarefas]
            opcoes_rot = [(f"{t['titulo']} (ID: {t['tarefa_id']})", str(t["tarefa_id"])) for t in rot_tarefas]

            val_admin = opcoes_admin[0][1] if opcoes_admin else None
            val_rot = opcoes_rot[0][1] if opcoes_rot else None

            html_admin, html_rot = renderizar_hub_cards_html(admin_tarefas, rot_tarefas)
            nome_display = escape(sessao.get("nome_usuario", ""))
            saudacao = f"<div><span style='font-size:12px; font-weight:700; color:#9c0014; text-transform:uppercase; letter-spacing:0.06em;'>Painel Principal</span><h2 style='margin:2px 0 0; color:#0f172a; font-size:24px; font-weight:800;'>Olá, {nome_display}!</h2><p style='color:#475569; font-size:14px; margin:4px 0 0;'>Gerencie suas rodadas de pesquisa ou rotule vídeos atribuídos à sua fila.</p></div>"
            return (
                gr.update(choices=opcoes_admin, value=val_admin),
                gr.update(choices=opcoes_rot, value=val_rot),
                html_admin,
                html_rot,
                saudacao,
            )

        def executar_login(usuario: str, senha: str) -> Tuple[Any, Any, str, Dict[str, Any], Any, Any, str, str, str]:
            try:
                dados = auth.autenticar_usuario(usuario, senha, permitir_reassumir=True)
                sessao = {
                    "usuario_id": dados["usuario_id"],
                    "nome_usuario": dados["nome_usuario"],
                    "tarefa_ativa_id": None,
                    "login_time": time.time(),
                    "start_time": time.time(),
                    "assignment_id": "",
                    "pergunta_template": "",
                    "opcoes_posicao": [],
                    "previous_target": "",
                }
                opt_admin, opt_rot, h_adm, h_rot, saudacao = atualizar_visoes_hub(sessao)
                return (
                    gr.update(visible=False),
                    gr.update(visible=True),
                    "",
                    sessao,
                    opt_admin,
                    opt_rot,
                    h_adm,
                    h_rot,
                    saudacao,
                )
            except Exception as exc:
                return (
                    gr.update(visible=True),
                    gr.update(visible=False),
                    f"⚠️ {str(exc)}",
                    {"usuario_id": None, "nome_usuario": "", "tarefa_ativa_id": None, "login_time": 0.0, "start_time": 0.0, "assignment_id": "", "pergunta_template": "", "opcoes_posicao": [], "previous_target": ""},
                    gr.update(),
                    gr.update(),
                    "",
                    "",
                    "",
                )

        def executar_cadastro(usuario: str, senha: str, confirma: str, convite: str) -> Tuple[Any, Any, str, Dict[str, Any], Any, Any, str, str, str]:
            if senha != confirma:
                return (
                    gr.update(visible=True),
                    gr.update(visible=False),
                    "⚠️ As senhas digitadas não coincidem.",
                    {"usuario_id": None, "nome_usuario": "", "tarefa_ativa_id": None, "login_time": 0.0, "start_time": 0.0, "assignment_id": "", "pergunta_template": "", "opcoes_posicao": [], "previous_target": ""},
                    gr.update(),
                    gr.update(),
                    "",
                    "",
                    "",
                )
            try:
                auth.cadastrar_usuario(usuario, senha, codigo_convite=convite or None)
                return executar_login(usuario, senha)
            except Exception as exc:
                return (
                    gr.update(visible=True),
                    gr.update(visible=False),
                    f"⚠️ {str(exc)}",
                    {"usuario_id": None, "nome_usuario": "", "tarefa_ativa_id": None, "login_time": 0.0, "start_time": 0.0, "assignment_id": "", "pergunta_template": "", "opcoes_posicao": [], "previous_target": ""},
                    gr.update(),
                    gr.update(),
                    "",
                    "",
                    "",
                )

        def executar_logout(sessao: Dict[str, Any]) -> Tuple[Any, Any, Any, Any, Any, str, Dict[str, Any]]:
            nome_u = sessao.get("nome_usuario", "")
            if nome_u:
                auth.encerrar_sessao(nome_u)
            nova_sessao = {"usuario_id": None, "nome_usuario": "", "tarefa_ativa_id": None, "login_time": 0.0, "start_time": 0.0, "assignment_id": "", "pergunta_template": "", "opcoes_posicao": [], "previous_target": ""}
            return (
                gr.update(visible=True),
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=False),
                "Sessão encerrada com sucesso.",
                nova_sessao,
            )

        def executar_entrar_convite(codigo: str, sessao: Dict[str, Any]) -> Tuple[str, Any, Any, str, str]:
            u_id = sessao.get("usuario_id")
            if not u_id:
                return "⚠️ Sessão inválida.", gr.update(), gr.update(), "", ""
            try:
                auth.entrar_na_tarefa_por_convite(int(u_id), codigo)
                opt_admin, opt_rot, h_adm, h_rot, _ = atualizar_visoes_hub(sessao)
                return "✅ Você entrou na tarefa com sucesso!", opt_admin, opt_rot, h_adm, h_rot
            except Exception as exc:
                opt_admin, opt_rot, h_adm, h_rot, _ = atualizar_visoes_hub(sessao)
                return f"⚠️ {str(exc)}", opt_admin, opt_rot, h_adm, h_rot

        #funcoes do wizard de criacao de tarefa
        def abrir_wizard_criacao() -> Tuple[Any, Any, str, Any]:
            novo_codigo = gerar_codigo_convite()
            tabela_df = gerar_tabela_penalidades_df("\n".join(OPCOES_TAREFA_PADRAO))
            return gr.update(visible=False), gr.update(visible=True), novo_codigo, tabela_df

        def voltar_hub_de_wizard(sessao: Dict[str, Any]) -> Tuple[Any, Any, Any, Any, str, str, str]:
            opt_admin, opt_rot, h_adm, h_rot, saudacao = atualizar_visoes_hub(sessao)
            return (
                gr.update(visible=True),
                gr.update(visible=False),
                opt_admin,
                opt_rot,
                h_adm,
                h_rot,
                saudacao,
            )

        def atualizar_matriz_pares(opcoes_txt: str) -> pd.DataFrame:
            return gerar_tabela_penalidades_df(opcoes_txt)

        def gerar_novo_codigo_convite_handler() -> str:
            return gerar_codigo_convite()

        def submeter_nova_tarefa(
            sessao: Dict[str, Any],
            titulo: str,
            pergunta: str,
            opcoes_txt: str,
            tabela_df: Any,
            vagas: float,
            overlap: float,
            codigo_convite: str,
            admin_como_rotulador: bool,
            arquivo_upload: Any,
            qtd_principal: float,
        ) -> Tuple[str, Any]:
            u_id = sessao.get("usuario_id")
            if not u_id:
                return "⚠️ Usuário não autenticado.", gr.update()

            opcoes = limpar_usuarios(opcoes_txt.splitlines())
            if len(opcoes) < 2:
                return "⚠️ A tarefa precisa conter ao menos duas opções de resposta distintas.", gr.update()

            distancias = converter_df_para_distancias(tabela_df)

            #leitura do pool de videos
            if arquivo_upload is not None:
                try:
                    caminho_arq = getattr(arquivo_upload, "name", str(arquivo_upload))
                    pool_videos = pd.read_csv(caminho_arq, dtype=str).fillna("")
                except Exception as exc:
                    return f"⚠️ Erro ao ler arquivo CSV de vídeos: {str(exc)}", gr.update()
            else:
                if ARQUIVO_VIDEOS.exists():
                    p_base = pd.read_csv(ARQUIVO_VIDEOS, dtype=str).fillna("")
                    p_res = pd.read_csv(ARQUIVO_VIDEOS_RESERVA, dtype=str).fillna("") if ARQUIVO_VIDEOS_RESERVA.exists() else pd.DataFrame()
                    pool_videos = pd.concat([p_base, p_res], ignore_index=True) if not p_res.empty else p_base
                else:
                    return "⚠️ Arquivos de vídeo padrão não encontrados no servidor.", gr.update()

            qtd_p = int(qtd_principal) if qtd_principal and int(qtd_principal) > 0 else None

            try:
                tarefa = admin.criar_nova_tarefa(
                    usuario_administrador_id=int(u_id),
                    pool_videos=pool_videos,
                    quantidade_videos_principal=qtd_p,
                    titulo=titulo or NOME_TAREFA_PADRAO,
                    pergunta=pergunta or PERGUNTA_TAREFA_PADRAO,
                    opcoes_posicao=opcoes,
                    distancias_rotulos=distancias,
                    numero_vagas=int(vagas),
                    percentual_sobreposicao=float(overlap),
                    codigo_convite=codigo_convite or None,
                    permitir_admin_como_rotulador=bool(admin_como_rotulador),
                )
                t_id = tarefa["tarefa_id"]
                c_convite = tarefa["codigo_convite"]
                tot_p = tarefa.get("quantidade_videos_principal", len(pool_videos))
                tot_r = tarefa.get("quantidade_videos_reserva", 0)
                novo_convite = gerar_codigo_convite()
                return (
                    f"✅ **Tarefa criada com sucesso!**  \n"
                    f"ID: `{t_id}` | Código de Convite: `<strong>{c_convite}</strong>`  \n"
                    f"Pool dividido: **{tot_p}** vídeos principais e **{tot_r}** vídeos reservas.  \n"
                    f"Clique em '← Voltar ao Hub' para visualizar e acessar a tarefa.",
                    gr.update(value=novo_convite),
                )
            except ValueError as ve:
                novo_convite = gerar_codigo_convite()
                return (
                    f"⚠️ {str(ve)} Geramos um novo código no campo acima; tente clicar novamente.",
                    gr.update(value=novo_convite),
                )
            except Exception as exc:
                return f"⚠️ Erro ao criar tarefa: {str(exc)}", gr.update()

        # ======================================================================
        # CONTROLE DO WORKSPACE DO ROTULADOR
        # ======================================================================
        def renderizar_video_rotulador(
            video_item: Optional[Dict[str, Any]],
            posicao: int,
            total: int,
            pergunta_template: str,
            previous_target: str,
        ) -> Tuple[str, str, str, str]:
            if not video_item or posicao >= total:
                html_fim = (
                    '<div class="empty-video">'
                    '<h2 style="color:#9c0014; margin-top:0;">Fila Concluída</h2>'
                    '<p>Você rotulou todos os vídeos atribuídos a você nesta rodada. Aguarde novas instruções. Obrigado!</p>'
                    '</div>'
                )
                pb = generate_progress_bar(total, total)
                return html_fim, "", pb, previous_target

            target = str(video_item.get("target", "") or "").strip()
            if "{target}" in pergunta_template:
                texto_pergunta = escape(pergunta_template.replace("{target}", target))
            elif pergunta_template:
                texto_pergunta = escape(pergunta_template)
            else:
                texto_pergunta = f'Com relação ao target <strong>"{escape(target)}"</strong>, como você classifica a posição deste vídeo?'

            pergunta_html = f'<div class="target-question">{texto_pergunta}</div>'
            pb = generate_progress_bar(posicao, total)
            target_mudou = bool(previous_target and previous_target != target)
            v_html = render_video_card(video_item, target_mudou)
            return v_html, pergunta_html, pb, target

        def abrir_rotulacao_tarefa(tarefa_id_str: str, sessao: Dict[str, Any]) -> Tuple[Any, Any, Any, Any, Any, str, str, str, str, Dict[str, Any]]:
            if not tarefa_id_str:
                return gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), "", "", "", "", sessao
            t_id = int(tarefa_id_str)
            nome_u = sessao.get("nome_usuario", "")

            estado_f = fila.obter_estado_fila(tarefa_id=t_id, nome_usuario=nome_u)
            exibir_aviso = estado_f["exibir_aviso_sensivel"]
            pos = estado_f["posicao_concluida"]
            tot = estado_f["total_videos"]
            vid = estado_f["video_atual"]
            opcoes = estado_f["opcoes_posicao"]
            pergunta = estado_f["pergunta"]

            v_html, p_html, pb, novo_target = renderizar_video_rotulador(
                video_item=vid,
                posicao=pos,
                total=tot,
                pergunta_template=pergunta,
                previous_target="",
            )

            cabecalho_txt = (
                f"<div class='labeler-info-badge'>"
                f"<span>Tarefa:</span> <strong style='color:#0f172a; font-size:15px;'>{escape(str(estado_f['titulo']))}</strong>"
                f"<span style='margin-left:14px;'>Rotulador:</span> <span class='user-pill'>{escape(str(nome_u))}</span>"
                f"</div>"
            )
            sessao_atualizada = dict(sessao)
            sessao_atualizada["tarefa_ativa_id"] = t_id
            sessao_atualizada["start_time"] = time.time()
            sessao_atualizada["assignment_id"] = vid.get("assignment_id", "") if vid else ""
            sessao_atualizada["pergunta_template"] = pergunta
            sessao_atualizada["opcoes_posicao"] = opcoes
            sessao_atualizada["previous_target"] = novo_target

            controles_visiveis = not exibir_aviso and not estado_f["concluida"]

            return (
                gr.update(visible=False), #painel_hub
                gr.update(visible=True),  #painel_rotulador
                gr.update(visible=exibir_aviso), #painel_aviso_sensivel
                gr.update(visible=controles_visiveis), #painel_controles_anotacao
                gr.update(choices=opcoes, value=None), #rotulador_radio
                cabecalho_txt,
                v_html,
                p_html,
                pb,
                sessao_atualizada,
            )

        def continuar_aviso_sensivel(sessao: Dict[str, Any]) -> Tuple[Any, Any, Dict[str, Any]]:
            t_id = sessao.get("tarefa_ativa_id")
            nome_u = sessao.get("nome_usuario", "")
            if t_id and nome_u:
                fila.aceitar_aviso_conteudo_sensivel(tarefa_id=int(t_id), nome_usuario=nome_u)
            sessao_atualizada = dict(sessao)
            sessao_atualizada["start_time"] = time.time()
            return gr.update(visible=False), gr.update(visible=True), sessao_atualizada

        def parar_rotulacao_sensivel(sessao: Dict[str, Any]) -> Tuple[Any, Any, Any, Any, str, str, str, Dict[str, Any]]:
            t_id = sessao.get("tarefa_ativa_id")
            nome_u = sessao.get("nome_usuario", "")
            if t_id and nome_u:
                fila.parar_rotulacao(tarefa_id=int(t_id), nome_usuario=nome_u)
            sessao_atualizada = dict(sessao)
            sessao_atualizada["tarefa_ativa_id"] = None
            opt_admin, opt_rot, h_adm, h_rot, saudacao = atualizar_visoes_hub(sessao_atualizada)
            return (
                gr.update(visible=True), #painel_hub
                gr.update(visible=False), #painel_rotulador
                opt_admin,
                opt_rot,
                h_adm,
                h_rot,
                saudacao,
                sessao_atualizada,
            )

        def salvar_resposta_rotulador(
            escolha_posicao: str,
            sessao: Dict[str, Any],
        ) -> Tuple[str, str, str, Any, str, Any, Dict[str, Any]]:
            t_id = sessao.get("tarefa_ativa_id")
            nome_u = sessao.get("nome_usuario", "")
            as_id = sessao.get("assignment_id", "")
            if not t_id or not nome_u:
                return "", "", "", gr.update(), "⚠️ Sessão de tarefa inválida.", gr.update(), sessao

            if not escolha_posicao:
                return (
                    gr.update(),
                    gr.update(),
                    gr.update(),
                    gr.update(),
                    "⚠️ Selecione uma opção antes de salvar.",
                    gr.update(),
                    sessao,
                )

            agora = time.time()
            start_t = sessao.get("start_time", agora)
            login_t = sessao.get("login_time", agora)
            tempo_analise = max(0.1, agora - start_t)
            tempo_login = max(0.0, agora - login_t)

            try:
                fila.salvar_anotacao_e_avancar(
                    tarefa_id=int(t_id),
                    nome_usuario=nome_u,
                    assignment_id=as_id,
                    posicao=escolha_posicao,
                    tempo_analise_segundos=tempo_analise,
                )
            except Exception as exc:
                return (
                    gr.update(),
                    gr.update(),
                    gr.update(),
                    gr.update(),
                    f"⚠️ {str(exc)}",
                    gr.update(),
                    sessao,
                )

            estado_f = fila.obter_estado_fila(tarefa_id=int(t_id), nome_usuario=nome_u, aviso_sensivel_aceito=True)
            pos = estado_f["posicao_concluida"]
            tot = estado_f["total_videos"]
            vid = estado_f["video_atual"]
            v_html, p_html, pb, novo_target = renderizar_video_rotulador(
                video_item=vid,
                posicao=pos,
                total=tot,
                pergunta_template=sessao.get("pergunta_template", ""),
                previous_target=sessao.get("previous_target", ""),
            )

            sessao_atualizada = dict(sessao)
            sessao_atualizada["start_time"] = time.time()
            sessao_atualizada["assignment_id"] = vid.get("assignment_id", "") if vid else ""
            sessao_atualizada["previous_target"] = novo_target
            controles_visiveis = not estado_f["concluida"]

            return (
                v_html,
                p_html,
                pb,
                gr.update(value=None),
                "",
                gr.update(visible=controles_visiveis),
                sessao_atualizada,
            )

        def reportar_erro_rotulador(sessao: Dict[str, Any]) -> Tuple[str, str, str, Any, str, Any, Dict[str, Any]]:
            t_id = sessao.get("tarefa_ativa_id")
            nome_u = sessao.get("nome_usuario", "")
            as_id = sessao.get("assignment_id", "")
            if not t_id or not nome_u:
                return "", "", "", gr.update(), "⚠️ Sessão de tarefa inválida.", gr.update(), sessao

            agora = time.time()
            start_t = sessao.get("start_time", agora)
            login_t = sessao.get("login_time", agora)
            tempo_analise = max(0.1, agora - start_t)
            tempo_login = max(0.0, agora - login_t)

            try:
                fila.reportar_erro_video(
                    tarefa_id=int(t_id),
                    nome_usuario=nome_u,
                    assignment_id=as_id,
                    tempo_analise_segundos=tempo_analise,
                )
            except Exception as exc:
                return (
                    gr.update(),
                    gr.update(),
                    gr.update(),
                    gr.update(),
                    f"⚠️ {str(exc)}",
                    gr.update(),
                    sessao,
                )

            estado_f = fila.obter_estado_fila(tarefa_id=int(t_id), nome_usuario=nome_u, aviso_sensivel_aceito=True)
            pos = estado_f["posicao_concluida"]
            tot = estado_f["total_videos"]
            vid = estado_f["video_atual"]
            v_html, p_html, pb, novo_target = renderizar_video_rotulador(
                video_item=vid,
                posicao=pos,
                total=tot,
                pergunta_template=sessao.get("pergunta_template", ""),
                previous_target=sessao.get("previous_target", ""),
            )

            sessao_atualizada = dict(sessao)
            sessao_atualizada["start_time"] = time.time()
            sessao_atualizada["assignment_id"] = vid.get("assignment_id", "") if vid else ""
            sessao_atualizada["previous_target"] = novo_target
            controles_visiveis = not estado_f["concluida"]

            return (
                v_html,
                p_html,
                pb,
                gr.update(value=None),
                "⚠️ O vídeo reportado com erro foi substituído por uma reserva da mesma classe.",
                gr.update(visible=controles_visiveis),
                sessao_atualizada,
            )

        # ======================================================================
        # CONTROLE DO CONSOLE DE ADMINISTRACAO
        # ======================================================================
        def abrir_admin_console(tarefa_id_str: str, sessao: Dict[str, Any]) -> Tuple[Any, Any, str, str, str, str, Any, Any, Any, Any, Any, Dict[str, Any]]:
            if not tarefa_id_str:
                return gr.update(), gr.update(), "", "", "", "", gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), sessao
            t_id = int(tarefa_id_str)
            nome_u = sessao.get("nome_usuario", "")

            try:
                metricas = admin.obter_metricas_operacionais(tarefa_id=t_id)
                arquivos = admin.exportar_arquivos_console(tarefa_id=t_id)
            except Exception as exc:
                return gr.update(), gr.update(), f"⚠️ Erro ao abrir console: {str(exc)}", "", "", "", gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), sessao

            tarefa_meta = repo_e.buscar_tarefa_por_id(t_id) or {}
            titulo_tela = f"## Console de Administração: **{escape(str(tarefa_meta.get('titulo', f'Tarefa #{t_id}')))}**"
            config_view = renderizar_configuracao_admin_html(tarefa_meta)

            status_msg = (
                f"{metricas['total_videos_principais']} vídeos principais | "
                f"{metricas['total_videos_reservas']} vídeos reserva | "
                f"{metricas['total_anotacoes']} anotações registradas | "
                f"{metricas['total_atribuicoes']} atribuições na rodada."
            )

            df_atrib = repo_e.carregar_atribuicoes_tarefa_df(t_id)
            df_anot = repo_e.carregar_anotacoes_tarefa_df(t_id)
            df_err = repo_e.carregar_erros_videos_tarefa_df(t_id)
            df_vid = repo_e.carregar_videos_tarefa_df(t_id)
            df_log = repo_e.carregar_logs_acesso_df(tarefa_id=t_id)

            dashboard_html = agreement_summary(
                agreement_data=metricas.get("concordancia", {}),
                assignments_df=df_atrib,
                results_df=df_anot,
                errors_df=df_err,
                videos_df=df_vid,
                logs_df=df_log,
                version_name=f"rodada_tarefa_{t_id}",
                opcoes_tarefa=list(tarefa_meta.get("opcoes_posicao", [])),
                total_reservas=metricas.get("total_videos_reservas", 0),
            )

            res_path = str(arquivos.arquivo_resultados) if arquivos.arquivo_resultados.exists() else None
            log_path = str(arquivos.arquivo_log) if arquivos.arquivo_log.exists() else None
            err_path = str(arquivos.arquivo_erros) if arquivos.arquivo_erros.exists() else None
            agr_path = str(arquivos.arquivo_concordancia) if arquivos.arquivo_concordancia.exists() else None

            sessao_atualizada = dict(sessao)
            sessao_atualizada["tarefa_ativa_id"] = t_id

            return (
                gr.update(visible=False), #painel_hub
                gr.update(visible=True),  #painel_admin
                titulo_tela,
                config_view,
                status_msg,
                dashboard_html,
                gr.update(value=res_path),
                gr.update(value=log_path),
                gr.update(value=err_path),
                gr.update(value=agr_path),
                df_atrib,
                sessao_atualizada,
            )

        def excluir_tarefa_pelo_hub(
            tarefa_id_str: str,
            sessao: Dict[str, Any],
        ) -> Tuple[str, Any, Any, str, str, str]:
            u_id = sessao.get("usuario_id")
            if not u_id or not tarefa_id_str:
                return "⚠️ Selecione uma tarefa na lista acima para excluir.", gr.update(), gr.update(), gr.update(), gr.update(), gr.update()
            try:
                t_id = int(tarefa_id_str)
                admin.excluir_tarefa(tarefa_id=t_id, usuario_administrador_id=int(u_id))
                opt_admin, opt_rot, h_adm, h_rot, saudacao = atualizar_visoes_hub(sessao)
                return f"✅ Tarefa #{t_id} excluída com sucesso.", opt_admin, opt_rot, h_adm, h_rot, saudacao
            except Exception as exc:
                return f"⚠️ Erro ao excluir tarefa: {str(exc)}", gr.update(), gr.update(), gr.update(), gr.update(), gr.update()

        def excluir_tarefa_pelo_admin(
            sessao: Dict[str, Any],
        ) -> Tuple[Any, Any, str, Any, Any, str, str, str]:
            u_id = sessao.get("usuario_id")
            t_id = sessao.get("tarefa_ativa_id")
            if not u_id or not t_id:
                return gr.update(visible=True), gr.update(visible=False), "⚠️ Sessão inválida para exclusão.", gr.update(), gr.update(), gr.update(), gr.update(), gr.update()
            try:
                admin.excluir_tarefa(tarefa_id=int(t_id), usuario_administrador_id=int(u_id))
                opt_admin, opt_rot, h_adm, h_rot, saudacao = atualizar_visoes_hub(sessao)
                return (
                    gr.update(visible=True),
                    gr.update(visible=False),
                    f"✅ Tarefa #{t_id} excluída com sucesso.",
                    opt_admin,
                    opt_rot,
                    h_adm,
                    h_rot,
                    saudacao,
                )
            except Exception as exc:
                return (
                    gr.update(),
                    gr.update(),
                    f"⚠️ Erro ao excluir tarefa: {str(exc)}",
                    gr.update(),
                    gr.update(),
                    gr.update(),
                    gr.update(),
                    gr.update(),
                )

        # ======================================================================
        # CONEXOES DE EVENTOS (WIRING)
        # ======================================================================
        handler_login_params = {
            "fn": executar_login,
            "inputs": [login_usuario, login_senha],
            "outputs": [
                painel_acesso,
                painel_hub,
                mensagem_acesso,
                estado_sessao,
                select_tarefa_admin,
                select_tarefa_rotulador,
                hub_admin_cards_html,
                hub_rotulador_cards_html,
                hub_saudacao,
            ],
        }
        btn_login.click(**handler_login_params)
        login_usuario.submit(**handler_login_params)
        login_senha.submit(**handler_login_params)

        handler_cadastro_params = {
            "fn": executar_cadastro,
            "inputs": [cadastro_usuario, cadastro_senha, cadastro_confirma, cadastro_convite],
            "outputs": [
                painel_acesso,
                painel_hub,
                mensagem_acesso,
                estado_sessao,
                select_tarefa_admin,
                select_tarefa_rotulador,
                hub_admin_cards_html,
                hub_rotulador_cards_html,
                hub_saudacao,
            ],
        }
        btn_cadastrar.click(**handler_cadastro_params)
        cadastro_usuario.submit(**handler_cadastro_params)
        cadastro_senha.submit(**handler_cadastro_params)
        cadastro_confirma.submit(**handler_cadastro_params)
        cadastro_convite.submit(**handler_cadastro_params)

        btn_logout.click(
            executar_logout,
            inputs=[estado_sessao],
            outputs=[
                painel_acesso,
                painel_hub,
                painel_wizard,
                painel_rotulador,
                painel_admin,
                mensagem_acesso,
                estado_sessao,
            ],
        )

        handler_convite_params = {
            "fn": executar_entrar_convite,
            "inputs": [input_codigo_convite, estado_sessao],
            "outputs": [
                hub_mensagem,
                select_tarefa_admin,
                select_tarefa_rotulador,
                hub_admin_cards_html,
                hub_rotulador_cards_html,
            ],
        }
        btn_entrar_convite.click(**handler_convite_params)
        input_codigo_convite.submit(**handler_convite_params)

        btn_ir_criar_tarefa.click(
            abrir_wizard_criacao,
            inputs=[],
            outputs=[painel_hub, painel_wizard, wizard_convite, wizard_tabela_penalidades],
        )

        btn_voltar_hub_wizard.click(
            voltar_hub_de_wizard,
            inputs=[estado_sessao],
            outputs=[
                painel_hub,
                painel_wizard,
                select_tarefa_admin,
                select_tarefa_rotulador,
                hub_admin_cards_html,
                hub_rotulador_cards_html,
                hub_saudacao,
            ],
        )

        btn_atualizar_pares.click(
            atualizar_matriz_pares,
            inputs=[wizard_opcoes],
            outputs=[wizard_tabela_penalidades],
        )

        btn_copiar_codigo.click(
            None,
            inputs=[wizard_convite],
            outputs=[],
            js="""
            (codigo) => {
                if (codigo) {
                    navigator.clipboard.writeText(codigo);
                    const toast = document.createElement('div');
                    toast.innerText = '📋 Código ' + codigo + ' copiado com sucesso!';
                    toast.style.position = 'fixed';
                    toast.style.bottom = '24px';
                    toast.style.right = '24px';
                    toast.style.background = '#0f172a';
                    toast.style.color = '#ffffff';
                    toast.style.padding = '12px 20px';
                    toast.style.borderRadius = '8px';
                    toast.style.boxShadow = '0 8px 24px rgba(0,0,0,0.2)';
                    toast.style.zIndex = '9999';
                    toast.style.fontWeight = '700';
                    toast.style.fontSize = '14px';
                    document.body.appendChild(toast);
                    setTimeout(() => toast.remove(), 2500);
                }
            }
            """,
        )

        btn_gerar_novo_codigo.click(
            gerar_novo_codigo_convite_handler,
            inputs=[],
            outputs=[wizard_convite],
        )

        btn_submeter_tarefa.click(
            submeter_nova_tarefa,
            inputs=[
                estado_sessao,
                wizard_titulo,
                wizard_pergunta,
                wizard_opcoes,
                wizard_tabela_penalidades,
                wizard_vagas,
                wizard_overlap,
                wizard_convite,
                wizard_admin_como_rotulador,
                wizard_arquivo_videos,
                wizard_qtd_principal,
            ],
            outputs=[wizard_mensagem, wizard_convite],
        )

        #eventos da tela de rotulacao
        btn_abrir_rotulacao.click(
            abrir_rotulacao_tarefa,
            inputs=[select_tarefa_rotulador, estado_sessao],
            outputs=[
                painel_hub,
                painel_rotulador,
                painel_aviso_sensivel,
                painel_controles_anotacao,
                rotulador_radio,
                rotulador_cabecalho,
                rotulador_video_html,
                rotulador_pergunta_html,
                rotulador_progresso,
                estado_sessao,
            ],
        )

        btn_continuar_sensivel.click(
            continuar_aviso_sensivel,
            inputs=[estado_sessao],
            outputs=[painel_aviso_sensivel, painel_controles_anotacao, estado_sessao],
        )

        btn_parar_sensivel.click(
            parar_rotulacao_sensivel,
            inputs=[estado_sessao],
            outputs=[
                painel_hub,
                painel_rotulador,
                select_tarefa_admin,
                select_tarefa_rotulador,
                hub_admin_cards_html,
                hub_rotulador_cards_html,
                hub_saudacao,
                estado_sessao,
            ],
        )

        btn_voltar_hub_rotulacao.click(
            parar_rotulacao_sensivel,
            inputs=[estado_sessao],
            outputs=[
                painel_hub,
                painel_rotulador,
                select_tarefa_admin,
                select_tarefa_rotulador,
                hub_admin_cards_html,
                hub_rotulador_cards_html,
                hub_saudacao,
                estado_sessao,
            ],
        )

        btn_salvar_resposta.click(
            salvar_resposta_rotulador,
            inputs=[rotulador_radio, estado_sessao],
            outputs=[
                rotulador_video_html,
                rotulador_pergunta_html,
                rotulador_progresso,
                rotulador_radio,
                rotulador_mensagem,
                painel_controles_anotacao,
                estado_sessao,
            ],
        )

        btn_erro_video.click(
            reportar_erro_rotulador,
            inputs=[estado_sessao],
            outputs=[
                rotulador_video_html,
                rotulador_pergunta_html,
                rotulador_progresso,
                rotulador_radio,
                rotulador_mensagem,
                painel_controles_anotacao,
                estado_sessao,
            ],
        )

        #eventos do console de administracao
        btn_abrir_admin.click(
            abrir_admin_console,
            inputs=[select_tarefa_admin, estado_sessao],
            outputs=[
                painel_hub,
                painel_admin,
                admin_titulo_tarefa,
                admin_configuracao_view,
                admin_status_view,
                admin_dashboard_html,
                admin_download_resultados,
                admin_download_logs,
                admin_download_erros,
                admin_download_concordancia,
                admin_tabela_atribuicoes,
                estado_sessao,
            ],
        )

        btn_voltar_hub_admin.click(
            voltar_hub_de_wizard,
            inputs=[estado_sessao],
            outputs=[
                painel_hub,
                painel_admin,
                select_tarefa_admin,
                select_tarefa_rotulador,
                hub_admin_cards_html,
                hub_rotulador_cards_html,
                hub_saudacao,
            ],
        )

        btn_excluir_tarefa_hub.click(
            excluir_tarefa_pelo_hub,
            inputs=[select_tarefa_admin, estado_sessao],
            outputs=[
                hub_mensagem,
                select_tarefa_admin,
                select_tarefa_rotulador,
                hub_admin_cards_html,
                hub_rotulador_cards_html,
                hub_saudacao,
            ],
        )

        btn_excluir_tarefa_admin.click(
            excluir_tarefa_pelo_admin,
            inputs=[estado_sessao],
            outputs=[
                painel_hub,
                painel_admin,
                hub_mensagem,
                select_tarefa_admin,
                select_tarefa_rotulador,
                hub_admin_cards_html,
                hub_rotulador_cards_html,
                hub_saudacao,
            ],
        )

    return app
