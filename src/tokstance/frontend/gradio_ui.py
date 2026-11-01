"""Interface Gradio completa: Login, Cadastro, Hub Inicial e Criador de Nova Tarefa (versao inicial do frontend)."""

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
from tokstance.frontend.theme import APP_CSS, obter_tema_branco


def renderizar_hub_cards_html(tarefas_admin: List[Dict[str, Any]], tarefas_rotulador: List[Dict[str, Any]]) -> Tuple[str, str]:
    """Gera o HTML dos cartoes do Hub Inicial para tarefas de administrador e de rotulador."""
    #cartoes de administrador
    if not tarefas_admin:
        html_admin = "<p class='muted'>Você ainda não criou nenhuma tarefa. Clique em '+ Criar Nova Tarefa' acima para iniciar.</p>"
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
                <div style='display:flex; justify-content:space-between; align-items:center;'>
                    <h4>{titulo}</h4>
                    <span class='hub-badge admin'>Administrador</span>
                </div>
                <div class='hub-card-meta'>
                    <div>Código de Convite: <code>{convite}</code></div>
                    <div>Vagas preenchidas: <strong>{vagas} de {total_v}</strong></div>
                    <div>Progresso geral: <strong>{prog:.0f}%</strong></div>
                </div>
            </div>
            """)
        html_admin = f"<div class='hub-grid'>{''.join(cards_admin)}</div>"

    #cartoes de rotulador
    if not tarefas_rotulador:
        html_rotulador = "<p class='muted'>Você ainda não está inscrito em nenhuma tarefa para rotular. Use o código de convite abaixo para entrar.</p>"
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
                <div style='display:flex; justify-content:space-between; align-items:center;'>
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


def gerar_tabela_penalidades_df(opcoes_texto: str) -> pd.DataFrame:
    """Gera um DataFrame com as combinacoes de pares e pesos de penalidade a partir do texto das opcoes."""
    opcoes = limpar_usuarios(opcoes_texto.splitlines())
    if len(opcoes) < 2:
        return pd.DataFrame(columns=["Opção A", "Opção B", "Penalidade"])

    #pesos padrao legados para as 4 opcoes classicas
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

    with gr.Blocks(theme=obter_tema_branco(), css=APP_CSS, title="TokStance!") as app:
        #estados de sessao
        estado_sessao = gr.State({"usuario_id": None, "nome_usuario": "", "tarefa_ativa_id": None})

        with gr.Column(elem_classes="shell"):
            gr.HTML("""
            <div class='brand-header'>
                <h1>TokStance!</h1>
                <p>Desenvolvido por Gustavo Cunha<br>
                Plataforma Colaborativa de Anotação de Vídeos Curtos</p>
            </div>
            """)

            # ==================================================================
            # 1. TELA DE ACESSO (LOGIN E CADASTRO)
            # ==================================================================
            with gr.Column(visible=True) as painel_acesso:
                with gr.Column(elem_classes="center-form"):
                    gr.HTML("<div style='text-align:center; margin-bottom: 20px;'><h3 style='margin:0; color:#333;'>Acesso ao Sistema</h3><p style='color:#666;'>Entre com suas credenciais ou crie uma conta gratuita.</p></div>")

                    with gr.Tab("Entrar"):
                        login_usuario = gr.Textbox(label="Usuário", placeholder="Seu nome de usuário", autofocus=True)
                        login_senha = gr.Textbox(label="Senha", type="password", placeholder="Sua senha")
                        btn_login = gr.Button("Entrar", elem_classes="ufmg-btn")

                    with gr.Tab("Criar Conta"):
                        cadastro_usuario = gr.Textbox(label="Novo Usuário", placeholder="Escolha seu nome de usuário")
                        cadastro_senha = gr.Textbox(label="Senha", type="password", placeholder="Mínimo 6 caracteres")
                        cadastro_confirma = gr.Textbox(label="Confirme a Senha", type="password", placeholder="Repita a senha")
                        cadastro_convite = gr.Textbox(label="Código de Convite (opcional)", placeholder="Ex: TOKSTANCE-2026")
                        btn_cadastrar = gr.Button("Cadastrar e Entrar", elem_classes="ufmg-btn")

                    mensagem_acesso = gr.Markdown()

            # ==================================================================
            # 2. HUB INICIAL DE TAREFAS (MULTI-ROLE)
            # ==================================================================
            with gr.Column(visible=False) as painel_hub:
                with gr.Row(elem_classes="admin-header"):
                    hub_saudacao = gr.Markdown("## Painel de Tarefas")
                    with gr.Row(elem_classes="admin-actions"):
                        btn_logout = gr.Button("Sair", elem_classes="error-btn")

                with gr.Row():
                    btn_ir_criar_tarefa = gr.Button("+ Criar Nova Tarefa", elem_classes="ufmg-btn")

                gr.Markdown("### Tarefas que você administra")
                hub_admin_cards_html = gr.HTML()
                with gr.Row():
                    select_tarefa_admin = gr.Dropdown(label="Selecionar Tarefa para Gerenciar", choices=[], value=None, interactive=True)
                    btn_abrir_admin = gr.Button("Abrir Console de Administração", elem_classes="ufmg-btn")

                gr.Markdown("### Tarefas atribuídas a você para rotular")
                hub_rotulador_cards_html = gr.HTML()
                with gr.Row():
                    select_tarefa_rotulador = gr.Dropdown(label="Selecionar Tarefa para Rotular", choices=[], value=None, interactive=True)
                    btn_abrir_rotulacao = gr.Button("Rotular Vídeos da Tarefa", elem_classes="ufmg-btn")

                gr.Markdown("### Ingressar em Nova Tarefa")
                with gr.Row():
                    input_codigo_convite = gr.Textbox(label="Código de Convite", placeholder="Cole o código de convite aqui", scale=3)
                    btn_entrar_convite = gr.Button("Entrar na Tarefa", elem_classes="ufmg-btn", scale=1)

                hub_mensagem = gr.Markdown()

            # ==================================================================
            # 3. TELA DE CRIACAO DE TAREFA (WIZARD)
            # ==================================================================
            with gr.Column(visible=False, elem_classes="admin-panel") as painel_wizard:
                with gr.Row(elem_classes="admin-header"):
                    gr.Markdown("## Criador de Nova Tarefa de Pesquisa")
                    with gr.Row(elem_classes="admin-actions"):
                        btn_voltar_hub_wizard = gr.Button("Voltar ao Hub", elem_classes="error-btn")

                with gr.Column(elem_classes="form-wizard-card"):
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
                        lines=5,
                    )
                    btn_atualizar_pares = gr.Button("Atualizar Matriz de Combinações", elem_classes="error-btn")

                    gr.Markdown("### 2. Matriz Par-a-Par de Penalidades (Distâncias)")
                    gr.Markdown("Edite os pesos de discordância para o cálculo do Alfa de Krippendorff ordinal:")
                    tabela_penalidades_inicial = gerar_tabela_penalidades_df("\n".join(OPCOES_TAREFA_PADRAO))
                    wizard_tabela_penalidades = gr.Dataframe(
                        value=tabela_penalidades_inicial,
                        headers=["Opção A", "Opção B", "Penalidade"],
                        datatype=["str", "str", "number"],
                        interactive=True,
                        elem_classes="pairwise-penalty-table",
                    )

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
                        btn_gerar_novo_codigo = gr.Button("Gerar Novo Código", elem_classes="error-btn", scale=1)

                    wizard_admin_como_rotulador = gr.Checkbox(
                        label="Inscrever-me automaticamente como rotulador na Vaga 1 desta tarefa",
                        value=True,
                    )

                    gr.Markdown("### 4. Pool de Vídeos e Divisão Principal / Reserva")
                    with gr.Row():
                        wizard_arquivo_videos = gr.File(
                            label="Upload do Arquivo CSV de Vídeos (opcional: se vazio, usa o pool padrão da UFMG)",
                            file_types=[".csv"],
                        )
                        wizard_qtd_principal = gr.Number(
                            label="Quantidade de Vídeos para Anotação Principal (0 ou vazio = automático)",
                            value=0,
                            precision=0,
                        )

                    btn_submeter_tarefa = gr.Button("Criar Tarefa e Atribuir Vagas", elem_classes="ufmg-btn")
                    wizard_mensagem = gr.Markdown()

            # ==================================================================
            # 4. TELA DE ROTULACAO (WORKSPACE) - Scaffolding C50
            # ==================================================================
            with gr.Column(visible=False, elem_classes="labeler-panel") as painel_rotulador:
                with gr.Row(elem_classes="labeler-actions"):
                    btn_voltar_hub_rotulacao = gr.Button("Salvar e sair", elem_classes="ufmg-btn")
                workspace_placeholder = gr.Markdown("Espaço do rotulador em inicialização...")

            # ==================================================================
            # 5. TELA DE ADMINISTRACAO (CONSOLE) - Scaffolding C50
            # ==================================================================
            with gr.Column(visible=False, elem_classes="admin-panel") as painel_admin:
                with gr.Row(elem_classes="admin-header"):
                    gr.Markdown("## Console de Administração da Tarefa")
                    with gr.Row(elem_classes="admin-actions"):
                        btn_voltar_hub_admin = gr.Button("Voltar ao Hub", elem_classes="error-btn")
                admin_console_placeholder = gr.Markdown("Console do administrador em inicialização...")

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
            saudacao = f"## Olá, **{escape(sessao.get('nome_usuario', ''))}**! Selecione ou crie uma tarefa abaixo:"
            return (
                gr.update(choices=opcoes_admin, value=val_admin),
                gr.update(choices=opcoes_rot, value=val_rot),
                html_admin,
                html_rot,
                saudacao,
            )

        def executar_login(usuario: str, senha: str) -> Tuple[Any, Any, str, Dict[str, Any], Any, Any, str, str, str]:
            try:
                dados = auth.autenticar_usuario(usuario, senha)
                sessao = {
                    "usuario_id": dados["usuario_id"],
                    "nome_usuario": dados["nome_usuario"],
                    "tarefa_ativa_id": None,
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
                    {"usuario_id": None, "nome_usuario": "", "tarefa_ativa_id": None},
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
                    {"usuario_id": None, "nome_usuario": "", "tarefa_ativa_id": None},
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
                    {"usuario_id": None, "nome_usuario": "", "tarefa_ativa_id": None},
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
            nova_sessao = {"usuario_id": None, "nome_usuario": "", "tarefa_ativa_id": None}
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
        ) -> str:
            u_id = sessao.get("usuario_id")
            if not u_id:
                return "⚠️ Usuário não autenticado."

            opcoes = limpar_usuarios(opcoes_txt.splitlines())
            if len(opcoes) < 2:
                return "⚠️ A tarefa precisa conter ao menos duas opções de resposta distintas."

            distancias = converter_df_para_distancias(tabela_df)

            #leitura do pool de videos
            if arquivo_upload is not None:
                try:
                    caminho_arq = getattr(arquivo_upload, "name", str(arquivo_upload))
                    pool_videos = pd.read_csv(caminho_arq, dtype=str).fillna("")
                except Exception as exc:
                    return f"⚠️ Erro ao ler arquivo CSV de vídeos: {str(exc)}"
            else:
                if ARQUIVO_VIDEOS.exists():
                    p_base = pd.read_csv(ARQUIVO_VIDEOS, dtype=str).fillna("")
                    p_res = pd.read_csv(ARQUIVO_VIDEOS_RESERVA, dtype=str).fillna("") if ARQUIVO_VIDEOS_RESERVA.exists() else pd.DataFrame()
                    pool_videos = pd.concat([p_base, p_res], ignore_index=True) if not p_res.empty else p_base
                else:
                    return "⚠️ Arquivos de vídeo padrão não encontrados no servidor."

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
                tot_p = tarefa["quantidade_videos_principal"]
                tot_r = tarefa["quantidade_videos_reserva"]
                return (
                    f"✅ **Tarefa criada com sucesso!**  \n"
                    f"ID: `{t_id}` | Código de Convite: `{c_convite}`  \n"
                    f"Pool dividido: **{tot_p}** principais e **{tot_r}** reservas.  \n"
                    f"Clique em 'Voltar ao Hub' para visualizar e acessar a tarefa."
                )
            except Exception as exc:
                return f"⚠️ Erro ao criar tarefa: {str(exc)}"

        #conexoes de eventos
        btn_login.click(
            executar_login,
            inputs=[login_usuario, login_senha],
            outputs=[
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
        )

        btn_cadastrar.click(
            executar_cadastro,
            inputs=[cadastro_usuario, cadastro_senha, cadastro_confirma, cadastro_convite],
            outputs=[
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
        )

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

        btn_entrar_convite.click(
            executar_entrar_convite,
            inputs=[input_codigo_convite, estado_sessao],
            outputs=[
                hub_mensagem,
                select_tarefa_admin,
                select_tarefa_rotulador,
                hub_admin_cards_html,
                hub_rotulador_cards_html,
            ],
        )

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
            outputs=[wizard_mensagem],
        )

    return app
