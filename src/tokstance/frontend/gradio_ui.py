"""Interface Gradio completa: Login, Cadastro, Painel Principal, Criador, Rotulacao e Console Admin (versao inicial do frontend)."""

from html import escape
import functools
import json
import tempfile
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
from tokstance.backend.security.password import validar_complexidade_senha
from tokstance.backend.security.validators import gerar_codigo_convite
from tokstance.backend.services.admin_service import ServicoAdministracao
from tokstance.backend.services.auth_service import ServicoAutenticacao
from tokstance.backend.services.queue_service import ServicoFilaAnotacao
from tokstance.config import ARQUIVO_VIDEOS, ARQUIVO_VIDEOS_RESERVA
from tokstance.frontend.components import (
    agreement_summary,
    formatar_pergunta_com_target,
    generate_progress_bar,
    render_video_card,
    renderizar_toast_html,
    renderizar_visao_geral_acervo_html,
    video_outputs,
)
from tokstance.frontend.theme import (
    APP_CSS,
    COR_PRIMARIA,
    JS_FORCAR_MODO_CLARO,
    obter_tema_branco,
)


def _com_toast(posicao: int):
    """Converte a mensagem de texto na posicao indicada da saida em aviso efemero."""

    def decorador(funcao):
        @functools.wraps(funcao)
        def interna(*args, **kwargs):
            resultado = list(funcao(*args, **kwargs))
            if isinstance(resultado[posicao], str):
                resultado[posicao] = renderizar_toast_html(resultado[posicao])
            return tuple(resultado)

        return interna

    return decorador


def renderizar_aviso_inline(mensagem: str, tipo: str = "erro") -> str:
    """Renderiza alerta inline em destaque no card de autenticacao."""
    if not mensagem:
        return ""
    texto = escape(str(mensagem).replace("⚠️", "").replace("✅", "").strip())
    classe_tipo = "error" if tipo in ("erro", "error") else "success"
    icone = "⚠️" if classe_tipo == "error" else "✓"
    return (
        f"<div class='auth-inline-{classe_tipo}' role='alert'>"
        f"<span class='auth-inline-icon'>{icone}</span>"
        f"<span class='auth-inline-text'>{texto}</span>"
        f"</div>"
    )


def renderizar_hub_tabelas_html(tarefas_admin: List[Dict[str, Any]], tarefas_rotulador: List[Dict[str, Any]]) -> Tuple[str, str]:
    """Renderiza tabelas modernas e responsivas para o Painel Principal com botoes diretos de acao."""
    # Tabela de Administracao
    if not tarefas_admin:
        html_admin = (
            "<div class='hub-table-empty'>"
            "Você ainda não criou nenhuma tarefa. Clique no botão '+' acima para iniciar."
            "</div>"
        )
    else:
        linhas_admin = []
        for t in tarefas_admin:
            t_id = t.get("tarefa_id", "")
            titulo = escape(str(t.get("titulo", f"Tarefa #{t_id}")))
            convite = escape(str(t.get("codigo_convite", "")))
            vagas = t.get("vagas_ocupadas", 0)
            total_v = t.get("numero_vagas", 0)
            prog = float(t.get("progresso_percentual", 0.0))
            prog_clamped = min(100.0, max(0.0, prog))
            linhas_admin.append(f"""
            <tr>
                <td>
                    <strong style="color: #0f172a; font-size: 14px;">{titulo}</strong>
                    <div style="font-size: 12px; color: #64748b;">ID #{t_id}</div>
                </td>
                <td>
                    <span class="config-val-badge convite">{convite}</span>
                </td>
                <td>
                    <span style="font-weight: 700; color: #334155;">{vagas} de {total_v}</span>
                </td>
                <td>
                    <span class="table-bar-track" style="display:inline-block; width:100px; height:8px; background:#e2e8f0; border-radius:999px; overflow:hidden; vertical-align:middle; margin-right:8px;"><span class="table-bar-fill" style="display:block; height:100%; width:{prog_clamped:.0f}%; background:#9c0014; border-radius:999px;"></span></span>
                    <span style="font-weight: 700; font-size: 13px; color: #334155;">{prog:.0f}%</span>
                </td>
                <td style="text-align: right; white-space: nowrap;">
                    <button type="button" class="hub-table-btn primary" onclick="window.tokstanceAcao('admin', '{t_id}')"><svg class="hub-btn-icon" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg> Abrir Console</button>
                    <button type="button" class="hub-table-btn danger" onclick="window.tokstanceAcao('excluir', '{t_id}')"><svg class="hub-btn-icon" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg> Excluir</button>
                </td>
            </tr>
            """)
        html_admin = f"""
        <div class="hub-table-wrapper">
            <table class="hub-table">
                <thead>
                    <tr>
                        <th>Tarefa</th>
                        <th>Código Convite</th>
                        <th>Vagas</th>
                        <th>Progresso</th>
                        <th style="text-align: right;">Ações</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(linhas_admin)}
                </tbody>
            </table>
        </div>
        """

    # Tabela de Rotulador
    if not tarefas_rotulador:
        html_rotulador = (
            "<div class='hub-table-empty'>"
            "Você ainda não está inscrito em nenhuma tarefa para rotular. Use o botão '+' acima para entrar com código de convite."
            "</div>"
        )
    else:
        linhas_rot = []
        for t in tarefas_rotulador:
            t_id = t.get("tarefa_id", "")
            titulo = escape(str(t.get("titulo", f"Tarefa #{t_id}")))
            pos = int(t.get("videos_concluidos", 0))
            tot = int(t.get("total_videos_fila", 0))
            pct = int((pos / tot) * 100) if tot > 0 else 0

            if tot == 0 or pos == 0:
                status_class = "pending"
                status_label = "Não iniciada"
                btn_class = "primary"
                btn_texto = '<svg class="hub-btn-icon" width="13" height="13" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg> Iniciar Rotulação'
            elif pos < tot:
                status_class = "in-progress"
                status_label = "Em andamento"
                btn_class = "in-progress"
                btn_texto = '<svg class="hub-btn-icon" width="13" height="13" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg> Continuar Rotulação'
            else:
                status_class = "completed"
                status_label = "Concluída"
                btn_class = "completed"
                btn_texto = '<svg class="hub-btn-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg> Ver Concluída'

            prog_txt = f"{pos} de {tot} ({pct}%)"
            linhas_rot.append(f"""
            <tr>
                <td>
                    <strong style="color: #0f172a; font-size: 14px;">{titulo}</strong>
                    <div style="font-size: 12px; color: #64748b;">ID #{t_id}</div>
                </td>
                <td>
                    <span class="table-bar-track" style="display:inline-block; width:100px; height:8px; background:#e2e8f0; border-radius:999px; overflow:hidden; vertical-align:middle; margin-right:8px;"><span class="table-bar-fill" style="display:block; height:100%; width:{pct}%; background:#9c0014; border-radius:999px;"></span></span>
                    <span style="font-weight: 700; font-size: 13px; color: #334155; white-space: nowrap;">{prog_txt}</span>
                </td>
                <td>
                    <span class="status-pill {status_class}">{status_label}</span>
                </td>
                <td style="text-align: right; white-space: nowrap;">
                    <button type="button" class="hub-table-btn {btn_class}" onclick="window.tokstanceAcao('rotular', '{t_id}')">{btn_texto}</button>
                </td>
            </tr>
            """)
        html_rotulador = f"""
        <div class="hub-table-wrapper">
            <table class="hub-table">
                <thead>
                    <tr>
                        <th>Tarefa</th>
                        <th>Progresso da Fila</th>
                        <th>Status</th>
                        <th style="text-align: right;">Ação</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(linhas_rot)}
                </tbody>
            </table>
        </div>
        """

    return html_admin, html_rotulador


# Alias retrocompativel com a versao anterior
renderizar_hub_cards_html = renderizar_hub_tabelas_html


COLUNAS_TABELA_AUDITORIA = [
    "assignment_version", "assignment_id", "labeler", "video_id", "target", "url",
    "video_description", "voice_to_text", "video_duration",
]


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
            <div class="config-item"><span class="config-label">Código de Convite:</span> <div class="config-code-row"><span class="config-val-badge convite">{convite}</span><button type="button" class="copy-code-btn" title="Copiar código de convite" aria-label="Copiar código de convite" onclick="window.tokstanceCopiar('{convite}')"><svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="btn-svg-icon"><rect width="14" height="14" x="8" y="8" rx="2" ry="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/></svg></button></div></div>
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
    """Constroi a aplicacao visual Blocks com suporte a autenticacao, painel principal, criador e workspace."""
    banco = BancoDadosSQLite()
    repo_u = RepositorioUsuarios(banco)
    repo_e = RepositorioEstudo(banco, repo_u)

    auth = servico_auth or ServicoAutenticacao(banco, repo_u, repo_e)
    fila = servico_fila or ServicoFilaAnotacao(banco, repo_u, repo_e)
    admin = servico_admin or ServicoAdministracao(banco, repo_u, repo_e)

    with gr.Blocks(title="TokStance!") as app:
        #estilos css globais injetados para compatibilidade com gradio 5 e 6
        gr.HTML(elem_classes="toast-slot", value=f"""
        <style>{APP_CSS}</style>
        <img src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
             onload="window.tokstanceAcao=function(tipo,id){{var el=document.querySelector('#tokstance_hub_trigger textarea, #tokstance_hub_trigger input'); if(el){{el.value=tipo+':'+id+':'+Date.now(); el.dispatchEvent(new Event('input',{{bubbles:true}})); el.dispatchEvent(new Event('change',{{bubbles:true}}));}}}}; window.tokstanceCopiar=function(t){{var ok=function(){{var d=document.createElement('div');d.className='tokstance-toast toast-sucesso toast-curto';d.innerHTML='<span class=toast-icone>✓</span><div class=toast-texto>Código '+t+' copiado</div>';document.body.appendChild(d);setTimeout(function(){{d.remove();}},3200);}};if(navigator.clipboard&&window.isSecureContext){{navigator.clipboard.writeText(t).then(ok);}}else{{var a=document.createElement('textarea');a.value=t;document.body.appendChild(a);a.select();document.execCommand('copy');a.remove();ok();}}}}; window.tokstanceForcarMaiusculo=function(){{document.addEventListener('input',function(e){{if(e.target&&(e.target.matches('.campo-nome-maiusculo input')||e.target.closest('.campo-nome-maiusculo'))){{var inp=e.target.tagName==='INPUT'?e.target:e.target.querySelector('input');if(inp){{var s=inp.selectionStart,end=inp.selectionEnd;inp.value=inp.value.toUpperCase();if(s!==null&&end!==null){{inp.setSelectionRange(s,end);}}}}}}}},true);}}; window.tokstanceForcarMaiusculo(); window.tokstanceAcessibilidadeBotoes=function(){{var bCop=document.querySelector('#btn_copiar_codigo_wizard, .btn-icon-copiar'); if(bCop){{bCop.setAttribute('title','Copiar código de convite');bCop.setAttribute('aria-label','Copiar código de convite');}}}}; setInterval(window.tokstanceAcessibilidadeBotoes,1500); window.tokstanceAcessibilidadeBotoes();"
             style="display:none;" />
        """)

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

        #ephemeral toast container
        toast_host = gr.HTML(elem_classes="toast-slot")
        #action trigger across views
        tokstance_hub_trigger = gr.Textbox(
            elem_id="tokstance_hub_trigger",
            elem_classes=["hidden-action-trigger"],
            visible=True,
        )
        mensagem_acesso = recuperar_mensagem = hub_mensagem = wizard_mensagem = rotulador_mensagem = toast_host

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

            #authentication panel
            with gr.Column(visible=True) as painel_acesso:
                with gr.Column(elem_classes="auth-card"):
                    gr.HTML("""
                    <div style='text-align: center; margin-bottom: 14px;'>
                        <h2 style='margin: 0 0 4px 0; color: #0f172a; font-size: 22px; font-weight: 800; letter-spacing: -0.02em;'>Bem-vindo ao TokStance!</h2>
                        <p style='color: #475569; font-size: 14px; margin: 0;'>Entre com suas credenciais ou crie uma conta</p>
                    </div>
                    """)

                    with gr.Tabs(selected="tab_entrar") as abas_autenticacao:
                        with gr.Tab("Entrar", id="tab_entrar"):
                            login_usuario = gr.Textbox(label="Nome de Usuário", placeholder="Digite seu usuário", autofocus=True)
                            login_senha = gr.Textbox(label="Senha de Acesso", type="password", placeholder="Digite sua senha", elem_id="login_senha", elem_classes=["campo-senha-com-olho"])
                            login_aviso = gr.HTML(value="", elem_classes=["auth-feedback-slot"])
                            btn_login = gr.Button("Entrar no Sistema", elem_classes="ufmg-btn", size="lg")

                        with gr.Tab("Criar Conta", id="tab_cadastro"):
                            cadastro_nome_completo = gr.Textbox(
                                label="Nome Completo",
                                placeholder="Ex: MARIA SILVA SANTOS",
                                elem_classes=["campo-nome-maiusculo", "uppercase-input"],
                            )
                            cadastro_usuario = gr.Textbox(label="Nome de Usuário", placeholder="Ex: pesquisador_1")
                            cadastro_email = gr.Textbox(label="E-mail", placeholder="Ex: usuario@dominio.com")
                            with gr.Row():
                                cadastro_senha = gr.Textbox(
                                    label="Senha de Acesso",
                                    type="password",
                                    placeholder="Mínimo 6 caracteres (letras e números)",
                                    info="Mínimo de 6 caracteres, com ao menos uma letra e um número.",
                                    scale=1,
                                    elem_classes=["campo-senha-com-olho"],
                                )
                                cadastro_confirma = gr.Textbox(
                                    label="Confirmar Senha",
                                    type="password",
                                    placeholder="Repita a senha",
                                    info="Digite novamente a senha para confirmação.",
                                    scale=1,
                                    elem_classes=["campo-senha-com-olho"],
                                )
                            cadastro_convite = gr.Textbox(label="Código de Convite (opcional)", placeholder="Ex: TOKSTANCE-2026")
                            cadastro_aviso = gr.HTML(value="", elem_classes=["auth-feedback-slot"])
                            btn_cadastrar = gr.Button("Cadastrar e Acessar", elem_classes="ufmg-btn", size="lg")

                        with gr.Tab("Recuperar Senha", id="tab_recuperar"):
                            #progressive recovery step
                            recuperar_identificador = gr.Textbox(label="Nome de Usuário ou E-mail Cadastrado", placeholder="Digite seu usuário ou e-mail")
                            recuperar_aviso_identificador = gr.HTML(value="", elem_classes=["auth-feedback-slot"])
                            btn_solicitar_recuperacao = gr.Button("Enviar Código de Recuperação", elem_classes="ufmg-btn", size="lg")

                            with gr.Column(visible=False) as recuperar_passo_codigo:
                                recuperar_codigo = gr.Textbox(label="Código de Verificação (6 dígitos)", placeholder="Ex: 123456")
                                recuperar_aviso_codigo = gr.HTML(value="", elem_classes=["auth-feedback-slot"])
                                with gr.Row(elem_classes="compact-actions"):
                                    btn_verificar_codigo = gr.Button("Verificar Código", elem_classes="ufmg-btn", size="lg")
                                    btn_trocar_identificador = gr.Button("Usar outro e-mail", elem_classes="error-btn", size="lg")

                            with gr.Column(visible=False) as recuperar_passo_senha:
                                with gr.Row():
                                    recuperar_nova_senha = gr.Textbox(
                                        label="Nova Senha",
                                        type="password",
                                        placeholder="Mínimo 6 caracteres (letras e números)",
                                        info="Mínimo de 6 caracteres, com ao menos uma letra e um número.",
                                        scale=1,
                                        elem_classes=["campo-senha-com-olho"],
                                    )
                                    recuperar_confirma_senha = gr.Textbox(
                                        label="Confirmar Nova Senha",
                                        type="password",
                                        placeholder="Repita a nova senha",
                                        info="Digite novamente a nova senha para confirmação.",
                                        scale=1,
                                        elem_classes=["campo-senha-com-olho"],
                                    )
                                recuperar_aviso_senha = gr.HTML(value="", elem_classes=["auth-feedback-slot"])
                                btn_redefinir_senha = gr.Button("Redefinir Senha", elem_classes="ufmg-btn", size="lg")

            #painel principal
            with gr.Column(visible=False) as painel_hub:
                with gr.Row(elem_classes="hub-header-bar"):
                    hub_saudacao = gr.HTML()
                    with gr.Row(elem_classes="compact-actions"):
                        btn_logout = gr.Button("Encerrar Sessão", elem_classes=["error-btn", "hub-btn", "btn-icon-logout"], scale=0, min_width=150)

                with gr.Row(elem_classes="hub-two-col"):
                    with gr.Column(scale=1, min_width=0, elem_classes="hub-section-box"):
                        with gr.Row(elem_classes="hub-box-header-row"):
                            gr.HTML("""
                            <div class="hub-box-header">
                                <h3>Tarefas sob sua Administração</h3>
                                <p>Rodadas de anotação criadas e coordenadas por você</p>
                            </div>
                            """)
                            btn_ir_criar_tarefa = gr.Button("+", elem_id="btn_ir_criar_tarefa", elem_classes=["ufmg-btn", "hub-plus-btn", "hub-plus-admin"], scale=0, min_width=38)
                        hub_admin_cards_html = gr.HTML()

                    with gr.Column(scale=1, min_width=0, elem_classes="hub-section-box"):
                        with gr.Row(elem_classes="hub-box-header-row"):
                            gr.HTML("""
                            <div class="hub-box-header">
                                <h3>Tarefas Atribuídas a Você</h3>
                                <p>Fila individual de vídeos atribuídos para sua análise</p>
                            </div>
                            """)
                            btn_abrir_convite = gr.Button("+", elem_id="btn_abrir_modal_convite", elem_classes=["ufmg-btn", "hub-plus-btn", "hub-plus-rotulador"], scale=0, min_width=38)
                        hub_rotulador_cards_html = gr.HTML()

                #invite code modal
                with gr.Column(visible=False, elem_classes="modal-overlay") as modal_convite:
                    with gr.Column(elem_classes="modal-card"):
                        gr.HTML("""
                        <div class="modal-titulo">
                            <h3>Ingressar em uma Tarefa</h3>
                            <p>Digite o código de convite compartilhado pelo administrador.</p>
                        </div>
                        """)
                        input_codigo_convite = gr.Textbox(
                            elem_id="input_codigo_convite",
                            label="Código de Convite",
                            placeholder="Ex: TOKSTANCE-2026",
                        )
                        modal_convite_aviso = gr.HTML(value="", elem_classes=["auth-feedback-slot"])
                        with gr.Row(elem_classes="compact-actions"):
                            btn_entrar_convite = gr.Button("Entrar na Tarefa", elem_classes="ufmg-btn", scale=0, min_width=160)
                            btn_cancelar_convite = gr.Button("Cancelar", elem_classes="error-btn", scale=0, min_width=110)

            # ==================================================================
            # 3. TELA DE CRIACAO DE TAREFA (WIZARD EM ETAPAS)
            # ==================================================================
            with gr.Column(visible=False, elem_classes="admin-panel") as painel_wizard:
                with gr.Row(elem_classes="admin-header"):
                    gr.Markdown("## Criar Nova Tarefa")
                    with gr.Row(elem_classes="compact-actions"):
                        btn_voltar_hub_wizard = gr.Button("← Voltar ao Painel Principal", elem_classes=["ufmg-btn", "hub-btn"], scale=0, min_width=250)

                with gr.Column(elem_classes="form-wizard-card"):
                    gr.HTML("""
                    <div class="wizard-header-banner">
                        <div class="admin-config-title">NOVA RODADA DE ROTULAÇÃO</div>
                        <div class="wizard-header-intro">
                            <div>
                                <h3 class="wizard-header-main-title">Configuração dos Parâmetros da Pesquisa</h3>
                                <p class="wizard-header-desc">Defina o tema, perguntas norteadoras, equipe de anotadores e acervo de vídeos do TikTok.</p>
                            </div>
                            <span class="config-val-badge convite">PASSO A PASSO</span>
                        </div>
                    </div>
                    """)

                    with gr.Row(elem_classes="wizard-stepper-row"):
                        btn_tab_passo1 = gr.Button("1 · Pergunta e Rótulos", elem_classes=["wizard-tab-btn", "active"], scale=1)
                        btn_tab_passo2 = gr.Button("2 · Equipe e Acesso", elem_classes=["wizard-tab-btn"], scale=1)
                        btn_tab_passo3 = gr.Button("3 · Vídeos e Reserva", elem_classes=["wizard-tab-btn"], scale=1)

                    # ETAPA 1: Pergunta Norteadora e Opcoes de Resposta
                    with gr.Column(visible=True, elem_classes=["wizard-step-container", "wizard-passo-1"]) as wizard_passo_1:
                        with gr.Row(elem_classes="wizard-step-row"):
                            with gr.Column(scale=1, min_width=0):
                                wizard_titulo = gr.Textbox(
                                    label="Título da Tarefa",
                                    value=NOME_TAREFA_PADRAO,
                                    placeholder="Ex: Detecção de Posição em Eleições",
                                )
                                wizard_pergunta = gr.Textbox(
                                    label="Pergunta (use {target} para inserir o tema)",
                                    value=PERGUNTA_TAREFA_PADRAO,
                                    placeholder='Com relação ao target "{target}", como você classifica a posição deste vídeo?',
                                )
                            with gr.Column(scale=1, min_width=0):
                                wizard_opcoes = gr.Textbox(
                                    label="Opções de Resposta (uma por linha)",
                                    value="\n".join(OPCOES_TAREFA_PADRAO),
                                    lines=5,
                                )
                        with gr.Accordion("Pesos de discordância entre opções (avançado)", open=False, elem_classes="wizard-accordion"):
                            gr.HTML("<p class='wizard-section-subtitle' style='margin-bottom: 8px;'>Defina penalidades par a par usadas no cálculo do Alfa de Krippendorff ordinal.</p>")
                            tabela_penalidades_inicial = gerar_tabela_penalidades_df("\n".join(OPCOES_TAREFA_PADRAO))
                            wizard_tabela_penalidades = gr.Dataframe(
                                value=tabela_penalidades_inicial,
                                headers=["Opção A", "Opção B", "Penalidade"],
                                datatype=["str", "str", "number"],
                                interactive=True,
                                elem_classes="pairwise-penalty-table",
                                max_height=180,
                            )
                            btn_atualizar_pares = gr.Button("Recalcular combinações", elem_classes=["ufmg-btn", "wizard-inline-btn"], scale=0)

                        with gr.Row(elem_classes="wizard-step-footer"):
                            btn_passo1_voltar_hub = gr.Button("← Voltar ao Painel Principal", elem_classes=["error-btn", "hub-btn"], scale=0, min_width=250)
                            btn_passo1_proximo = gr.Button("Próximo: Equipe e Acesso →", elem_classes=["ufmg-btn", "wizard-next-btn"], scale=0, min_width=240)

                    # ETAPA 2: Equipe, Vagas e Codigo de Convite
                    with gr.Column(visible=False, elem_classes=["wizard-step-container", "wizard-passo-2"]) as wizard_passo_2:
                        with gr.Row(elem_classes="wizard-slider-row"):
                            wizard_vagas = gr.Slider(
                                label="Vagas de Rotuladores",
                                minimum=1,
                                maximum=20,
                                value=3,
                                step=1,
                                scale=1,
                            )
                            wizard_overlap = gr.Slider(
                                label="Sobreposição (%)",
                                minimum=0.0,
                                maximum=100.0,
                                value=20.0,
                                step=5.0,
                                scale=1,
                            )

                        with gr.Row(elem_classes="wizard-second-row"):
                            with gr.Row(elem_classes="wizard-action-row", scale=1):
                                wizard_convite = gr.Textbox(
                                    label="Código de Convite",
                                    value=gerar_codigo_convite(),
                                    scale=1,
                                )
                                btn_copiar_codigo = gr.Button(
                                    value="",
                                    elem_id="btn_copiar_codigo_wizard",
                                    elem_classes=["wizard-icon-btn", "wizard-tool-btn", "btn-icon-copiar"],
                                    scale=0,
                                    min_width=42,
                                )
                            with gr.Column(elem_classes="wizard-checkbox-card", scale=1):
                                wizard_admin_como_rotulador = gr.Checkbox(
                                    label="Participar também como rotulador (Vaga 1)",
                                    value=True,
                                    elem_classes="wizard-checkbox",
                                )

                        with gr.Row(elem_classes="wizard-step-footer"):
                            btn_passo2_voltar = gr.Button("← Voltar ao Passo 1", elem_classes=["error-btn", "hub-btn"], scale=0, min_width=200)
                            btn_passo2_proximo = gr.Button("Próximo: Vídeos e Reserva →", elem_classes=["ufmg-btn", "wizard-next-btn"], scale=0, min_width=240)

                    # ETAPA 3: Videos e Reserva Tecnica
                    with gr.Column(visible=False, elem_classes=["wizard-step-container", "wizard-passo-3"]) as wizard_passo_3:
                        gr.HTML("""
                        <div class="wizard-info-callout">
                            <strong>Coleção Padrão Integrada:</strong> Caso nenhum arquivo CSV seja enviado, o TokStance carrega automaticamente o acervo oficial de 60 vídeos autênticos do TikTok.
                        </div>
                        """)
                        with gr.Row(elem_classes="wizard-step-row"):
                            with gr.Column(scale=1, min_width=0):
                                wizard_qtd_principal = gr.Number(
                                    label="Quantidade de vídeos a distribuir",
                                    info="O restante dos vídeos da coleção será direcionado para a reserva técnica.",
                                    value=30,
                                    precision=0,
                                    minimum=1,
                                    elem_classes=["wizard-number-input"],
                                )
                            with gr.Column(scale=1, min_width=0):
                                wizard_arquivo_videos = gr.File(
                                    label="CSV de Vídeos (opcional)",
                                    file_types=[".csv"],
                                    height=100,
                                    elem_classes=["wizard-file-upload"],
                                )

                        wizard_aviso = gr.HTML(value="", elem_classes=["auth-feedback-slot", "wizard-feedback-slot"])

                        with gr.Row(elem_classes="wizard-step-footer"):
                            btn_passo3_voltar = gr.Button("← Voltar ao Passo 2", elem_classes=["error-btn", "hub-btn"], scale=0, min_width=160)
                            btn_submeter_tarefa = gr.Button("Criar Tarefa e Atribuir Vagas", elem_classes=["ufmg-btn", "wizard-submit-btn"], scale=0, min_width=260)

            # ==================================================================
            # 4. TELA DE ROTULACAO (WORKSPACE DO ROTULADOR)
            # ==================================================================
            with gr.Column(visible=False, elem_classes="labeler-panel") as painel_rotulador:
                with gr.Row(elem_classes="labeler-header-bar"):
                    rotulador_tarefa_meta_topo = gr.HTML("<div class='workspace-header-title'><h2>Workspace de Rotulação</h2></div>", scale=1)
                    btn_voltar_hub_rotulacao = gr.Button("← Sair", elem_classes=["ufmg-btn", "labeler-exit-btn"], scale=0)

                with gr.Column(elem_classes="labeler-workspace-container"):
                    with gr.Column(visible=False, elem_classes="sensitive-warning-wrapper") as painel_aviso_sensivel:
                        with gr.Column(elem_classes="sensitive-warning-card"):
                            gr.HTML("""
                                <div class="sensitive-warning-header">
                                    <div class="sensitive-warning-badge"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="btn-svg-icon" style="margin-right: 4px;"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>Aviso de Conteúdo</div>
                                    <h2>Possível Conteúdo Sensível ou Nocivo</h2>
                                </div>
                                <div class="sensitive-warning-body">
                                    <p>O conteúdo dos vídeos e seus metadados (tema, descrição e transcrição) podem envolver assuntos sensíveis, controversos ou potencialmente desconfortáveis.</p>
                                    <p>Deseja visualizar o material completo e prosseguir com a rotulação?</p>
                                </div>
                            """)
                            with gr.Row(elem_classes="sensitive-warning-actions"):
                                btn_parar_sensivel = gr.Button("Sair", elem_classes=["secondary-btn", "sensitive-btn-stop"])
                                btn_continuar_sensivel = gr.Button("Continuar", elem_classes=["ufmg-btn", "sensitive-btn-continue"])

                    with gr.Row(elem_classes="labeler-layout"):
                        with gr.Column(scale=0, min_width=640, elem_classes="video-column"):
                            rotulador_video_html = gr.HTML()

                        with gr.Column(scale=1, min_width=380, elem_classes="labeler-controls-column"):
                            rotulador_cabecalho = gr.HTML(visible=False, elem_classes=["hidden-cabecalho"])
                            rotulador_progresso = gr.HTML()

                            with gr.Column(visible=False, elem_classes="annotation-controls") as painel_controles_anotacao:
                                gr.HTML("<div class='labeler-warning-stack'><div>⏳ O player do TikTok pode demorar alguns segundos para carregar.</div><div>🔊 Certifique-se de que o som do vídeo está habilitado clicando no ícone de som do player do TikTok.</div></div>")

                                rotulador_pergunta_html = gr.HTML()
                                rotulador_radio = gr.Radio(choices=[], label="Selecione uma opção:", elem_classes="wrap-radio")

                                btn_salvar_resposta = gr.Button("Salvar Resposta e Avançar", elem_classes="ufmg-btn")
                                btn_erro_video = gr.Button("O vídeo não carregou", elem_classes=["error-btn", "btn-icon-alerta"])


            # ==================================================================
            # 5. TELA DE ADMINISTRACAO (CONSOLE DA TAREFA)
            # ==================================================================
            with gr.Column(visible=False, elem_classes="admin-panel") as painel_admin:
                with gr.Row(elem_classes="admin-header"):
                    admin_titulo_tarefa = gr.Markdown("## Console de Administração da Tarefa")
                    with gr.Row(elem_classes="compact-actions"):
                        btn_excluir_tarefa_admin = gr.Button("Excluir esta Tarefa", elem_classes=["ufmg-btn", "hub-btn", "btn-icon-trash"], scale=0, min_width=170)
                        btn_voltar_hub_admin = gr.Button("← Voltar ao Painel Principal", elem_classes=["ufmg-btn", "hub-btn"], scale=0, min_width=250)

                #primeira visao oficial: visao geral do acervo e distribuicao por target
                admin_configuracao_view = gr.HTML(elem_classes="admin-configuration")
                admin_visao_acervo_html = gr.HTML(elem_classes="admin-collection-overview-container")

                gr.Markdown("### Dados Coletados e Análise Operacional")
                admin_dashboard_html = gr.HTML()

                with gr.Row(elem_classes="admin-downloads"):
                    admin_download_resultados = gr.File(label="Resultados Anotação (CSV)")
                    admin_download_erros = gr.File(label="Vídeos com Erro (CSV)")
                    admin_download_concordancia = gr.File(label="Concordância (JSON)")

                gr.Markdown("### Auditoria de Atribuições", elem_classes="admin-audit")
                admin_tabela_atribuicoes = gr.Dataframe(
                    headers=["assignment_version", "assignment_id", "labeler", "video_id", "target", "url", "video_description", "voice_to_text", "video_duration"],
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
        def atualizar_visoes_hub(sessao: Dict[str, Any]) -> Tuple[str, str, str]:
            u_id = sessao.get("usuario_id")
            if not u_id:
                return "", "", ""
            painel = auth.obter_painel_usuario(int(u_id))
            admin_tarefas = painel["tarefas_administrador"]
            rot_tarefas = painel["tarefas_rotulador"]

            html_admin, html_rot = renderizar_hub_tabelas_html(admin_tarefas, rot_tarefas)
            nome_display = escape(str(sessao.get("nome_completo") or sessao.get("nome_usuario", "")))
            saudacao = (
                f"<div>"
                f"<span style='font-size:12px; font-weight:700; color:#9c0014; text-transform:uppercase; letter-spacing:0.06em;'>Painel Principal</span>"
                f"<h2 style='margin:2px 0 0; color:#0f172a; font-size:24px; font-weight:800;'>Olá, {nome_display}!</h2>"
                f"<p style='color:#475569; font-size:14px; margin:4px 0 0;'>Gerencie suas rodadas de pesquisa ou rotule vídeos atribuídos à sua fila.</p>"
                f"</div>"
            )
            return html_admin, html_rot, saudacao

        campos_acesso = [
            login_usuario, login_senha,
            cadastro_nome_completo, cadastro_usuario, cadastro_email, cadastro_senha, cadastro_confirma, cadastro_convite,
            recuperar_identificador, recuperar_codigo, recuperar_nova_senha, recuperar_confirma_senha,
        ]
        saidas_formularios = campos_acesso + [recuperar_passo_codigo, recuperar_passo_senha]

        def sessao_vazia() -> Dict[str, Any]:
            return {"usuario_id": None, "nome_usuario": "", "nome_completo": "", "tarefa_ativa_id": None, "login_time": 0.0, "start_time": 0.0, "assignment_id": "", "pergunta_template": "", "opcoes_posicao": [], "previous_target": ""}

        def formularios_limpos(usuario_padrao: str = "") -> List[Any]:
            #reset form inputs and collapse recovery steps
            valores: List[Any] = [""] * len(campos_acesso)
            if usuario_padrao:
                valores[0] = usuario_padrao
            idx_identificador = campos_acesso.index(recuperar_identificador)
            idx_codigo = campos_acesso.index(recuperar_codigo)
            valores[idx_identificador] = gr.update(value="", interactive=True)
            valores[idx_codigo] = gr.update(value="", interactive=True)
            return valores + [gr.update(visible=False), gr.update(visible=False)]

        def formularios_mantidos() -> List[Any]:
            return [gr.update() for _ in range(len(campos_acesso) + 2)]

        def resposta_acesso_falha(mensagem: str, origem: str = "login") -> Tuple[Any, ...]:
            aviso_inline_html = renderizar_aviso_inline(mensagem, tipo="erro")
            aviso_login = aviso_inline_html if origem == "login" else ""
            aviso_cadastro = aviso_inline_html if origem == "cadastro" else ""
            return (
                gr.update(visible=True),
                gr.update(visible=False),
                renderizar_toast_html(f"⚠️ {mensagem}"),
                sessao_vazia(),
                "",
                "",
                "",
                aviso_login,
                aviso_cadastro,
                "",  #recuperar_aviso_identificador
                "",  #recuperar_aviso_codigo
                "",  #recuperar_aviso_senha
                *formularios_mantidos(),
            )

        def executar_login(usuario: str, senha: str) -> Tuple[Any, ...]:
            try:
                dados = auth.autenticar_usuario(usuario, senha, permitir_reassumir=True)
            except Exception as exc:
                return resposta_acesso_falha(str(exc), origem="login")
            sessao = {
                "usuario_id": dados["usuario_id"],
                "nome_usuario": dados["nome_usuario"],
                "nome_completo": dados.get("nome_completo", ""),
                "tarefa_ativa_id": None,
                "login_time": time.time(),
                "start_time": time.time(),
                "assignment_id": "",
                "pergunta_template": "",
                "opcoes_posicao": [],
                "previous_target": "",
            }
            h_adm, h_rot, saudacao = atualizar_visoes_hub(sessao)
            return (
                gr.update(visible=False),
                gr.update(visible=True),
                "",
                sessao,
                h_adm,
                h_rot,
                saudacao,
                "",  #login_aviso
                "",  #cadastro_aviso
                "",  #recuperar_aviso_identificador
                "",  #recuperar_aviso_codigo
                "",  #recuperar_aviso_senha
                *formularios_limpos(),
            )

        def executar_cadastro(nome_completo: str, usuario: str, email: str, senha: str, confirma: str, convite: str) -> Tuple[Any, ...]:
            nome_completo_limpo = str(nome_completo or "").strip().upper()
            if not nome_completo_limpo:
                return resposta_acesso_falha("O preenchimento do nome completo é obrigatório.", origem="cadastro")
            if not usuario or not str(usuario).strip():
                return resposta_acesso_falha("O nome de usuário é obrigatório.", origem="cadastro")
            if not email or not str(email).strip():
                return resposta_acesso_falha("O preenchimento do e-mail é obrigatório.", origem="cadastro")
            if not senha or not str(senha).strip():
                return resposta_acesso_falha("A senha de acesso é obrigatória (mínimo de 6 caracteres, com ao menos uma letra e um número).", origem="cadastro")
            try:
                validar_complexidade_senha(senha)
            except ValueError as exc:
                return resposta_acesso_falha(str(exc), origem="cadastro")
            if senha != confirma:
                return resposta_acesso_falha("As senhas digitadas não coincidem.", origem="cadastro")
            try:
                auth.cadastrar_usuario(
                    nome_usuario=usuario,
                    senha=senha,
                    email=email,
                    nome_completo=nome_completo_limpo,
                    codigo_convite=convite or None,
                )
            except Exception as exc:
                return resposta_acesso_falha(str(exc), origem="cadastro")
            return executar_login(usuario, senha)

        def executar_solicitar_recuperacao(identificador: str) -> Tuple[Any, ...]:
            sem_mudanca = (gr.update(), gr.update(), gr.update())
            try:
                res = auth.solicitar_recuperacao_senha(identificador)
            except Exception as exc:
                msg_erro = str(exc)
                return (
                    renderizar_toast_html(f"⚠️ {msg_erro}"),
                    renderizar_aviso_inline(msg_erro, tipo="erro"),
                    *sem_mudanca,
                )
            if res.get("smtp_configurado") and not res.get("disparado_smtp"):
                msg_erro = "Não foi possível enviar o e-mail agora. Tente novamente em instantes."
                return (
                    renderizar_toast_html(f"⚠️ {msg_erro}"),
                    renderizar_aviso_inline(msg_erro, tipo="erro"),
                    *sem_mudanca,
                )
            if res.get("disparado_smtp"):
                msg = "Enviamos um código de 6 dígitos para o seu e-mail. Ele expira em 15 minutos."
            else:
                msg = "Código gerado. O envio de e-mail não está configurado: consulte o terminal do servidor."
            return (
                renderizar_toast_html(f"✅ {msg}"),
                renderizar_aviso_inline(msg, tipo="sucesso"),
                gr.update(visible=True),
                gr.update(visible=False),
                gr.update(interactive=False),
            )

        def executar_verificar_codigo(identificador: str, codigo: str) -> Tuple[Any, ...]:
            try:
                auth.verificar_codigo_recuperacao(identificador, codigo)
            except Exception as exc:
                msg_erro = str(exc)
                return (
                    renderizar_toast_html(f"⚠️ {msg_erro}"),
                    renderizar_aviso_inline(msg_erro, tipo="erro"),
                    gr.update(),
                    gr.update(),
                )
            return (
                renderizar_toast_html("✅ Código confirmado. Defina sua nova senha."),
                "",
                gr.update(visible=True),
                gr.update(interactive=False),
            )

        def executar_trocar_identificador() -> Tuple[Any, ...]:
            return (
                "",
                "",
                "",
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(interactive=True),
                gr.update(value="", interactive=True),
                gr.update(value=""),
                gr.update(value=""),
            )

        def executar_redefinir_senha(identificador: str, codigo: str, nova_senha: str, confirma: str) -> Tuple[Any, ...]:
            if not nova_senha or not str(nova_senha).strip():
                msg_erro = "A nova senha é obrigatória (mínimo de 6 caracteres, com ao menos uma letra e um número)."
                aviso_html = renderizar_aviso_inline(msg_erro, tipo="erro")
                return (
                    renderizar_toast_html(f"⚠️ {msg_erro}"),
                    gr.update(),
                    gr.update(),
                    aviso_html,
                    gr.update(),
                    gr.update(),
                    *[gr.update() for _ in range(len(campos_acesso) + 2)],
                )
            try:
                validar_complexidade_senha(nova_senha)
            except ValueError as exc:
                msg_erro = str(exc).replace("A senha ", "A nova senha ")
                aviso_html = renderizar_aviso_inline(msg_erro, tipo="erro")
                return (
                    renderizar_toast_html(f"⚠️ {msg_erro}"),
                    gr.update(),
                    gr.update(),
                    aviso_html,
                    gr.update(),
                    gr.update(),
                    *[gr.update() for _ in range(len(campos_acesso) + 2)],
                )
            if nova_senha != confirma:
                msg_erro = "A nova senha e a confirmação de senha não coincidem."
                aviso_html = renderizar_aviso_inline(msg_erro, tipo="erro")
                return (
                    renderizar_toast_html(f"⚠️ {msg_erro}"),
                    gr.update(),
                    gr.update(),
                    aviso_html,
                    gr.update(),
                    gr.update(),
                    *[gr.update() for _ in range(len(campos_acesso) + 2)],
                )
            try:
                res = auth.redefinir_senha_com_codigo(identificador, codigo, nova_senha)
            except Exception as exc:
                msg_erro = str(exc)
                aviso_html = renderizar_aviso_inline(msg_erro, tipo="erro")
                return (
                    renderizar_toast_html(f"⚠️ {msg_erro}"),
                    gr.update(),
                    gr.update(),
                    aviso_html,
                    gr.update(),
                    gr.update(),
                    *[gr.update() for _ in range(len(campos_acesso) + 2)],
                )
            aviso_login_sucesso = renderizar_aviso_inline(
                "Senha redefinida com sucesso! Você já pode entrar com sua nova senha.", tipo="sucesso"
            )
            usuario_login = res.get("nome_usuario") or identificador
            return (
                renderizar_toast_html(f"✅ {res['mensagem']}"),
                "",
                "",
                "",
                gr.update(selected="tab_entrar"),
                aviso_login_sucesso,
                *formularios_limpos(usuario_padrao=usuario_login),
            )

        def executar_logout(sessao: Dict[str, Any]) -> Tuple[Any, ...]:
            nome_u = sessao.get("nome_usuario", "")
            if nome_u:
                auth.encerrar_sessao(nome_u)
            return (
                gr.update(visible=True),
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=False),
                renderizar_toast_html("✅ Sessão encerrada com sucesso."),
                sessao_vazia(),
                "",
                "",
                "",
                "",
                "",
                gr.update(selected="tab_entrar"),
                *formularios_limpos(),
            )

        def abrir_modal_convite() -> Tuple[Any, Any, str]:
            return gr.update(visible=True), gr.update(value=""), ""

        def fechar_modal_convite() -> Tuple[Any, str]:
            return gr.update(visible=False), ""

        def executar_entrar_convite(codigo: str, sessao: Dict[str, Any]) -> Tuple[Any, ...]:
            u_id = sessao.get("usuario_id")
            if not u_id:
                msg_erro = "Sessão inválida."
                return (
                    renderizar_toast_html(f"⚠️ {msg_erro}"),
                    renderizar_aviso_inline(msg_erro, tipo="erro"),
                    gr.update(),
                    gr.update(),
                    gr.update(),
                    gr.update(),
                    gr.update(),
                )
            try:
                auth.entrar_na_tarefa_por_convite(int(u_id), codigo)
            except Exception as exc:
                msg_erro = str(exc)
                return (
                    renderizar_toast_html(f"⚠️ {msg_erro}"),
                    renderizar_aviso_inline(msg_erro, tipo="erro"),
                    gr.update(),
                    gr.update(),
                    gr.update(),
                    gr.update(visible=True),
                    gr.update(),
                )
            h_adm, h_rot, saudacao = atualizar_visoes_hub(sessao)
            return (
                renderizar_toast_html("✅ Você entrou na tarefa com sucesso!"),
                "",
                h_adm,
                h_rot,
                saudacao,
                gr.update(visible=False),
                gr.update(value=""),
            )

        #funcoes do wizard de criacao de tarefa em etapas
        def ir_para_passo(passo: int) -> Tuple[Any, Any, Any, Any, Any, Any]:
            if passo == 1:
                return (
                    gr.update(visible=True),
                    gr.update(visible=False),
                    gr.update(visible=False),
                    gr.update(elem_classes=["wizard-tab-btn", "active"]),
                    gr.update(elem_classes=["wizard-tab-btn"]),
                    gr.update(elem_classes=["wizard-tab-btn"]),
                )
            elif passo == 2:
                return (
                    gr.update(visible=False),
                    gr.update(visible=True),
                    gr.update(visible=False),
                    gr.update(elem_classes=["wizard-tab-btn", "completed"]),
                    gr.update(elem_classes=["wizard-tab-btn", "active"]),
                    gr.update(elem_classes=["wizard-tab-btn"]),
                )
            else:
                return (
                    gr.update(visible=False),
                    gr.update(visible=False),
                    gr.update(visible=True),
                    gr.update(elem_classes=["wizard-tab-btn", "completed"]),
                    gr.update(elem_classes=["wizard-tab-btn", "completed"]),
                    gr.update(elem_classes=["wizard-tab-btn", "active"]),
                )

        def abrir_wizard_criacao() -> Tuple[Any, Any, str, Any, str, Any, Any, Any, Any, Any, Any]:
            novo_codigo = gerar_codigo_convite()
            tabela_df = gerar_tabela_penalidades_df("\n".join(OPCOES_TAREFA_PADRAO))
            p1, p2, p3, t1, t2, t3 = ir_para_passo(1)
            return (
                gr.update(visible=False),
                gr.update(visible=True),
                novo_codigo,
                tabela_df,
                "",
                p1,
                p2,
                p3,
                t1,
                t2,
                t3,
            )

        def voltar_hub_de_wizard(sessao: Dict[str, Any]) -> Tuple[Any, Any, str, str, str, str]:
            h_adm, h_rot, saudacao = atualizar_visoes_hub(sessao)
            return (
                gr.update(visible=True),
                gr.update(visible=False),
                h_adm,
                h_rot,
                saudacao,
                "",
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
        ) -> Tuple[str, Any, str]:
            u_id = sessao.get("usuario_id")
            if not u_id:
                msg = "⚠️ Usuário não autenticado."
                return renderizar_toast_html(msg), gr.update(), renderizar_aviso_inline("Usuário não autenticado.", tipo="erro")

            opcoes = limpar_usuarios(opcoes_txt.splitlines())
            if len(opcoes) < 2:
                msg = "⚠️ A tarefa precisa conter ao menos duas opções de resposta distintas."
                return renderizar_toast_html(msg), gr.update(), renderizar_aviso_inline("A tarefa precisa conter ao menos duas opções de resposta distintas.", tipo="erro")

            distancias = converter_df_para_distancias(tabela_df)

            #leitura do pool de videos
            if arquivo_upload is not None:
                try:
                    caminho_arq = getattr(arquivo_upload, "name", str(arquivo_upload))
                    pool_videos = pd.read_csv(caminho_arq, dtype=str).fillna("")
                except Exception as exc:
                    msg = f"⚠️ Erro ao ler arquivo CSV de vídeos: {str(exc)}"
                    return renderizar_toast_html(msg), gr.update(), renderizar_aviso_inline(f"Erro ao ler arquivo CSV de vídeos: {str(exc)}", tipo="erro")
                reserva_df = None
            else:
                if ARQUIVO_VIDEOS.exists():
                    pool_videos = pd.read_csv(ARQUIVO_VIDEOS, dtype=str).fillna("")
                    reserva_df = (
                        pd.read_csv(ARQUIVO_VIDEOS_RESERVA, dtype=str).fillna("")
                        if ARQUIVO_VIDEOS_RESERVA.exists()
                        else None
                    )
                else:
                    msg = "⚠️ Arquivos de vídeo padrão não encontrados no servidor."
                    return renderizar_toast_html(msg), gr.update(), renderizar_aviso_inline("Arquivos de vídeo padrão não encontrados no servidor.", tipo="erro")

            total_disponivel = len(pool_videos)

            #verificacoes de integridade da quantidade de videos a distribuir
            try:
                qtd_distribuir = int(qtd_principal) if qtd_principal is not None else total_disponivel
            except (ValueError, TypeError):
                msg = "⚠️ Quantidade de vídeos a distribuir inválida."
                return renderizar_toast_html(msg), gr.update(), renderizar_aviso_inline("Quantidade de vídeos a distribuir inválida.", tipo="erro")

            if qtd_distribuir <= 0:
                msg = "⚠️ A quantidade de vídeos a distribuir deve ser maior que zero."
                return renderizar_toast_html(msg), gr.update(), renderizar_aviso_inline("A quantidade de vídeos a distribuir deve ser maior que zero.", tipo="erro")

            if qtd_distribuir > total_disponivel:
                msg = f"⚠️ A quantidade de vídeos a distribuir ({qtd_distribuir}) não pode ser maior que o total disponível ({total_disponivel})."
                return renderizar_toast_html(msg), gr.update(), renderizar_aviso_inline(f"A quantidade de vídeos a distribuir ({qtd_distribuir}) não pode ser maior que o total disponível na coleção ({total_disponivel}).", tipo="erro")

            qtd_p = qtd_distribuir

            try:
                tarefa = admin.criar_nova_tarefa(
                    usuario_administrador_id=int(u_id),
                    pool_videos=pool_videos,
                    quantidade_videos_principal=qtd_p,
                    videos_reserva_explicitos=reserva_df,
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
                msg_sucesso = (
                    f"Tarefa criada com sucesso! Código de convite: {c_convite} "
                    f"({tot_p} vídeos principais e {tot_r} de reserva)."
                )
                return (
                    renderizar_toast_html(
                        f"✅ Tarefa criada com sucesso!\nCódigo de convite: **{c_convite}**\n"
                        f"{tot_p} vídeos principais e {tot_r} de reserva.",
                        acao_rotulo="Ir para o Console da Tarefa",
                        acao_tipo="admin",
                        acao_tarefa_id=t_id,
                    ),
                    gr.update(value=novo_convite),
                    renderizar_aviso_inline(msg_sucesso, tipo="sucesso"),
                )
            except ValueError as ve:
                novo_convite = gerar_codigo_convite()
                msg_erro = f"{str(ve)} Geramos um novo código no campo de convite; tente novamente."
                return (
                    renderizar_toast_html(f"⚠️ {msg_erro}"),
                    gr.update(value=novo_convite),
                    renderizar_aviso_inline(msg_erro, tipo="erro"),
                )
            except Exception as exc:
                msg_erro = f"Erro ao criar tarefa: {str(exc)}"
                return (
                    renderizar_toast_html(f"⚠️ {msg_erro}"),
                    gr.update(),
                    renderizar_aviso_inline(msg_erro, tipo="erro"),
                )

        # ======================================================================
        # CONTROLE DO WORKSPACE DO ROTULADOR
        # ======================================================================
        def renderizar_video_rotulador(
            video_item: Optional[Dict[str, Any]],
            posicao: int,
            total: int,
            pergunta_template: str,
            previous_target: str,
            tarefa_titulo: str = "",
            rotulador_nome: str = "",
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
            texto_pergunta = formatar_pergunta_com_target(pergunta_template, target)
            target_mudou = (posicao == 0) or bool(previous_target and previous_target != target)
            transicao_classe = " target-transition" if target_mudou else ""
            pergunta_html = f'<div class="target-question{transicao_classe}"><strong>{texto_pergunta}</strong></div>'
            pb = generate_progress_bar(posicao, total)
            v_html = render_video_card(
                video_item,
                target_mudou,
                tarefa_titulo=tarefa_titulo,
                rotulador_nome=rotulador_nome,
            )
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
            prev_target = str(estado_f.get("target_anterior", "") or "")
            t_titulo = str(estado_f.get("titulo", "") or "")

            v_html, p_html, pb, novo_target = renderizar_video_rotulador(
                video_item=vid,
                posicao=pos,
                total=tot,
                pergunta_template=pergunta,
                previous_target=prev_target,
                tarefa_titulo=t_titulo,
                rotulador_nome=str(nome_u),
            )

            cabecalho_txt = (
                f"<div class='labeler-info-badge'>"
                f"<div><span>Tarefa:</span> <strong>{escape(t_titulo)}</strong></div>"
                f"<div><span>Rotulador:</span> <span class='user-pill'>{escape(str(nome_u))}</span></div>"
                f"</div>"
            )
            sessao_atualizada = dict(sessao)
            sessao_atualizada["tarefa_ativa_id"] = t_id
            sessao_atualizada["tarefa_titulo"] = t_titulo
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

        def parar_rotulacao_sensivel(sessao: Dict[str, Any]) -> Tuple[Any, Any, str, str, str, Dict[str, Any]]:
            t_id = sessao.get("tarefa_ativa_id")
            nome_u = sessao.get("nome_usuario", "")
            if t_id and nome_u:
                fila.parar_rotulacao(tarefa_id=int(t_id), nome_usuario=nome_u)
            sessao_atualizada = dict(sessao)
            sessao_atualizada["tarefa_ativa_id"] = None
            h_adm, h_rot, saudacao = atualizar_visoes_hub(sessao_atualizada)
            return (
                gr.update(visible=True), #painel_hub
                gr.update(visible=False), #painel_rotulador
                h_adm,
                h_rot,
                saudacao,
                sessao_atualizada,
            )

        @_com_toast(4)
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
            prev_t = sessao.get("previous_target", "") or str(estado_f.get("target_anterior", "") or "")
            v_html, p_html, pb, novo_target = renderizar_video_rotulador(
                video_item=vid,
                posicao=pos,
                total=tot,
                pergunta_template=sessao.get("pergunta_template", ""),
                previous_target=prev_t,
                tarefa_titulo=str(sessao.get("tarefa_titulo", "") or estado_f.get("titulo", "")),
                rotulador_nome=str(nome_u),
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

        @_com_toast(4)
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
            prev_t = sessao.get("previous_target", "") or str(estado_f.get("target_anterior", "") or "")
            v_html, p_html, pb, novo_target = renderizar_video_rotulador(
                video_item=vid,
                posicao=pos,
                total=tot,
                pergunta_template=sessao.get("pergunta_template", ""),
                previous_target=prev_t,
                tarefa_titulo=str(sessao.get("tarefa_titulo", "") or estado_f.get("titulo", "")),
                rotulador_nome=str(nome_u),
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
                arquivos = admin.exportar_arquivos_console(
                    tarefa_id=t_id, diretorio_destino=tempfile.mkdtemp(prefix="tokstance_console_")
                )
            except Exception as exc:
                return gr.update(), gr.update(), f"⚠️ Erro ao abrir console: {str(exc)}", "", "", "", gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), sessao

            tarefa_meta = repo_e.buscar_tarefa_por_id(t_id) or {}
            titulo_tela = f"## Console de Administração: **{escape(str(tarefa_meta.get('titulo', f'Tarefa #{t_id}')))}**"
            config_view = renderizar_configuracao_admin_html(tarefa_meta)
            visao_acervo_html = renderizar_visao_geral_acervo_html(metricas, tarefa_meta)

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
                visao_acervo_html,
                dashboard_html,
                gr.update(value=res_path),
                gr.update(value=log_path),
                gr.update(value=err_path),
                gr.update(value=agr_path),
                df_atrib[[c for c in COLUNAS_TABELA_AUDITORIA if c in df_atrib.columns]] if not df_atrib.empty else df_atrib,
                sessao_atualizada,
            )

        def voltar_hub_de_admin(sessao: Dict[str, Any]) -> Tuple[Any, Any, str, str, str, Dict[str, Any]]:
            sessao_atualizada = dict(sessao)
            sessao_atualizada["tarefa_ativa_id"] = None
            h_adm, h_rot, saudacao = atualizar_visoes_hub(sessao_atualizada)
            return (
                gr.update(visible=True),
                gr.update(visible=False),
                h_adm,
                h_rot,
                saudacao,
                sessao_atualizada,
            )

        @_com_toast(2)
        def excluir_tarefa_pelo_admin(
            sessao: Dict[str, Any],
        ) -> Tuple[Any, Any, str, str, str, str, Dict[str, Any]]:
            u_id = sessao.get("usuario_id")
            t_id = sessao.get("tarefa_ativa_id")
            if not u_id or not t_id:
                return gr.update(visible=True), gr.update(visible=False), "⚠️ Sessão inválida para exclusão.", "", "", "", sessao
            try:
                admin.excluir_tarefa(tarefa_id=int(t_id), usuario_administrador_id=int(u_id))
                sessao_atualizada = dict(sessao)
                sessao_atualizada["tarefa_ativa_id"] = None
                h_adm, h_rot, saudacao = atualizar_visoes_hub(sessao_atualizada)
                return (
                    gr.update(visible=True),
                    gr.update(visible=False),
                    f"✅ Tarefa #{t_id} excluída com sucesso.",
                    h_adm,
                    h_rot,
                    saudacao,
                    sessao_atualizada,
                )
            except Exception as exc:
                h_adm, h_rot, saudacao = atualizar_visoes_hub(sessao)
                return (
                    gr.update(),
                    gr.update(),
                    f"⚠️ Erro ao excluir tarefa: {str(exc)}",
                    h_adm,
                    h_rot,
                    saudacao,
                    sessao,
                )

        nomes_saida_hub = [
            "painel_hub", "painel_wizard", "painel_rotulador", "painel_admin", "painel_aviso", "painel_controles",
            "radio", "cabecalho", "video", "pergunta", "progresso",
            "adm_titulo", "adm_config", "adm_status", "adm_dashboard",
            "adm_res", "adm_err", "adm_agr", "adm_tabela",
            "hub_admin", "hub_rot", "saudacao", "toast", "sessao",
        ]
        saidas_hub = [
            painel_hub, painel_wizard, painel_rotulador, painel_admin, painel_aviso_sensivel, painel_controles_anotacao,
            rotulador_radio, rotulador_cabecalho, rotulador_video_html, rotulador_pergunta_html, rotulador_progresso,
            admin_titulo_tarefa, admin_configuracao_view, admin_visao_acervo_html, admin_dashboard_html,
            admin_download_resultados, admin_download_erros, admin_download_concordancia,
            admin_tabela_atribuicoes,
            hub_admin_cards_html, hub_rotulador_cards_html, hub_saudacao, toast_host, estado_sessao,
        ]

        def montar_saida_hub(**valores: Any) -> Tuple[Any, ...]:
            return tuple(valores.get(nome, gr.update()) for nome in nomes_saida_hub)

        def processar_acao_hub(comando: str, sessao: Dict[str, Any]) -> Tuple[Any, ...]:
            if not comando or ":" not in comando:
                return montar_saida_hub(sessao=sessao)
            partes = comando.split(":")
            acao = partes[0].strip()
            tarefa_id_str = partes[1].strip()

            if acao == "rotular":
                (p_hub, p_rot, p_aviso, p_ctrl, r_radio, r_cab, v_html, p_html, pb, sessao_nova) = abrir_rotulacao_tarefa(tarefa_id_str, sessao)
                return montar_saida_hub(
                    painel_hub=p_hub, painel_wizard=gr.update(visible=False), painel_rotulador=p_rot,
                    painel_aviso=p_aviso, painel_controles=p_ctrl, radio=r_radio, cabecalho=r_cab,
                    video=v_html, pergunta=p_html, progresso=pb, sessao=sessao_nova,
                )

            if acao == "admin":
                (p_hub, p_adm, a_tit, a_cfg, a_stat, a_dash, d_res, d_log, d_err, d_agr, df_atrib, sessao_nova) = abrir_admin_console(tarefa_id_str, sessao)
                erro_ao_abrir = isinstance(a_tit, str) and a_tit.startswith("⚠️")
                return montar_saida_hub(
                    painel_hub=p_hub, painel_wizard=gr.update(visible=False), painel_admin=p_adm,
                    adm_titulo=gr.update() if erro_ao_abrir else a_tit, adm_config=a_cfg, adm_status=a_stat,
                    adm_dashboard=a_dash, adm_res=d_res, adm_err=d_err, adm_agr=d_agr,
                    adm_tabela=df_atrib, toast=renderizar_toast_html(a_tit) if erro_ao_abrir else gr.update(),
                    sessao=sessao_nova,
                )

            if acao == "excluir":
                u_id = sessao.get("usuario_id")
                msg = ""
                if u_id and tarefa_id_str:
                    try:
                        admin.excluir_tarefa(tarefa_id=int(tarefa_id_str), usuario_administrador_id=int(u_id))
                        msg = f"✅ Tarefa #{tarefa_id_str} excluída com sucesso."
                    except Exception as exc:
                        msg = f"⚠️ Erro ao excluir tarefa: {str(exc)}"
                h_adm, h_rot, saudacao = atualizar_visoes_hub(sessao)
                return montar_saida_hub(
                    painel_hub=gr.update(visible=True), painel_wizard=gr.update(visible=False),
                    painel_rotulador=gr.update(visible=False), painel_admin=gr.update(visible=False),
                    hub_admin=h_adm, hub_rot=h_rot, saudacao=saudacao,
                    toast=renderizar_toast_html(msg), sessao=sessao,
                )

            return montar_saida_hub(sessao=sessao)

        # ======================================================================
        # CONEXOES DE EVENTOS (WIRING)
        # ======================================================================
        saidas_acesso = [
            painel_acesso,
            painel_hub,
            mensagem_acesso,
            estado_sessao,
            hub_admin_cards_html,
            hub_rotulador_cards_html,
            hub_saudacao,
            login_aviso,
            cadastro_aviso,
            recuperar_aviso_identificador,
            recuperar_aviso_codigo,
            recuperar_aviso_senha,
        ] + saidas_formularios
        handler_login_params = {
            "fn": executar_login,
            "inputs": [login_usuario, login_senha],
            "outputs": saidas_acesso,
        }
        btn_login.click(**handler_login_params)
        login_usuario.submit(**handler_login_params)
        login_senha.submit(**handler_login_params)


        handler_cadastro_params = {
            "fn": executar_cadastro,
            "inputs": [cadastro_nome_completo, cadastro_usuario, cadastro_email, cadastro_senha, cadastro_confirma, cadastro_convite],
            "outputs": saidas_acesso,
        }
        btn_cadastrar.click(**handler_cadastro_params)
        cadastro_nome_completo.submit(**handler_cadastro_params)
        cadastro_usuario.submit(**handler_cadastro_params)
        cadastro_email.submit(**handler_cadastro_params)
        cadastro_senha.submit(**handler_cadastro_params)
        cadastro_confirma.submit(**handler_cadastro_params)
        cadastro_convite.submit(**handler_cadastro_params)

        handler_solicitar_params = {
            "fn": executar_solicitar_recuperacao,
            "inputs": [recuperar_identificador],
            "outputs": [recuperar_mensagem, recuperar_aviso_identificador, recuperar_passo_codigo, recuperar_passo_senha, recuperar_identificador],
        }
        btn_solicitar_recuperacao.click(**handler_solicitar_params)
        recuperar_identificador.submit(**handler_solicitar_params)

        handler_verificar_params = {
            "fn": executar_verificar_codigo,
            "inputs": [recuperar_identificador, recuperar_codigo],
            "outputs": [recuperar_mensagem, recuperar_aviso_codigo, recuperar_passo_senha, recuperar_codigo],
        }
        btn_verificar_codigo.click(**handler_verificar_params)
        recuperar_codigo.submit(**handler_verificar_params)

        btn_trocar_identificador.click(
            executar_trocar_identificador,
            inputs=[],
            outputs=[
                recuperar_aviso_identificador,
                recuperar_aviso_codigo,
                recuperar_aviso_senha,
                recuperar_passo_codigo,
                recuperar_passo_senha,
                recuperar_identificador,
                recuperar_codigo,
                recuperar_nova_senha,
                recuperar_confirma_senha,
            ],
        )

        handler_redefinir_params = {
            "fn": executar_redefinir_senha,
            "inputs": [recuperar_identificador, recuperar_codigo, recuperar_nova_senha, recuperar_confirma_senha],
            "outputs": [
                recuperar_mensagem,
                recuperar_aviso_identificador,
                recuperar_aviso_codigo,
                recuperar_aviso_senha,
                abas_autenticacao,
                login_aviso,
            ] + saidas_formularios,
        }
        btn_redefinir_senha.click(**handler_redefinir_params)
        recuperar_nova_senha.submit(**handler_redefinir_params)
        recuperar_confirma_senha.submit(**handler_redefinir_params)

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
                login_aviso,
                cadastro_aviso,
                recuperar_aviso_identificador,
                recuperar_aviso_codigo,
                recuperar_aviso_senha,
                abas_autenticacao,
            ] + saidas_formularios,
        )

        btn_abrir_convite.click(abrir_modal_convite, inputs=[], outputs=[modal_convite, input_codigo_convite, modal_convite_aviso])
        btn_cancelar_convite.click(fechar_modal_convite, inputs=[], outputs=[modal_convite, modal_convite_aviso])
        handler_convite_params = {
            "fn": executar_entrar_convite,
            "inputs": [input_codigo_convite, estado_sessao],
            "outputs": [hub_mensagem, modal_convite_aviso, hub_admin_cards_html, hub_rotulador_cards_html, hub_saudacao, modal_convite, input_codigo_convite],
        }
        btn_entrar_convite.click(**handler_convite_params)
        input_codigo_convite.submit(**handler_convite_params)

        #unified table and toast action trigger
        tokstance_hub_trigger.change(
            processar_acao_hub,
            inputs=[tokstance_hub_trigger, estado_sessao],
            outputs=saidas_hub,
        )

        wizard_passo_outputs = [
            wizard_passo_1,
            wizard_passo_2,
            wizard_passo_3,
            btn_tab_passo1,
            btn_tab_passo2,
            btn_tab_passo3,
        ]

        btn_ir_criar_tarefa.click(
            abrir_wizard_criacao,
            inputs=[],
            outputs=[
                painel_hub,
                painel_wizard,
                wizard_convite,
                wizard_tabela_penalidades,
                wizard_aviso,
                wizard_passo_1,
                wizard_passo_2,
                wizard_passo_3,
                btn_tab_passo1,
                btn_tab_passo2,
                btn_tab_passo3,
            ],
        )

        btn_voltar_hub_wizard.click(
            voltar_hub_de_wizard,
            inputs=[estado_sessao],
            outputs=[
                painel_hub,
                painel_wizard,
                hub_admin_cards_html,
                hub_rotulador_cards_html,
                hub_saudacao,
                wizard_aviso,
            ],
        )

        btn_passo1_voltar_hub.click(
            voltar_hub_de_wizard,
            inputs=[estado_sessao],
            outputs=[
                painel_hub,
                painel_wizard,
                hub_admin_cards_html,
                hub_rotulador_cards_html,
                hub_saudacao,
                wizard_aviso,
            ],
        )

        btn_passo1_proximo.click(lambda: ir_para_passo(2), inputs=[], outputs=wizard_passo_outputs)
        btn_passo2_voltar.click(lambda: ir_para_passo(1), inputs=[], outputs=wizard_passo_outputs)
        btn_passo2_proximo.click(lambda: ir_para_passo(3), inputs=[], outputs=wizard_passo_outputs)
        btn_passo3_voltar.click(lambda: ir_para_passo(2), inputs=[], outputs=wizard_passo_outputs)

        btn_tab_passo1.click(lambda: ir_para_passo(1), inputs=[], outputs=wizard_passo_outputs)
        btn_tab_passo2.click(lambda: ir_para_passo(2), inputs=[], outputs=wizard_passo_outputs)
        btn_tab_passo3.click(lambda: ir_para_passo(3), inputs=[], outputs=wizard_passo_outputs)

        def atualizar_qtd_videos_upload(arquivo_upload: Any) -> Any:
            """Atualiza dinamicamente a contagem pre-preenchida de videos a distribuir conforme upload."""
            if arquivo_upload is None:
                return gr.update(
                    value=30,
                    info="O restante dos vídeos da coleção padrão será direcionado para a reserva técnica.",
                )
            try:
                caminho = getattr(arquivo_upload, "name", str(arquivo_upload))
                df = pd.read_csv(caminho, dtype=str).fillna("")
                total = len(df.drop_duplicates(subset=["id"] if "id" in df.columns else None))
                if total <= 0:
                    return gr.update(
                        value=0,
                        info="⚠️ Arquivo CSV vazio ou sem registros válidos.",
                    )
                return gr.update(
                    value=total,
                    info=f"Coleção carregada com {total} vídeos. O restante irá para a reserva técnica.",
                )
            except Exception as exc:
                return gr.update(
                    info=f"⚠️ Erro ao processar CSV: {str(exc)}",
                )

        wizard_arquivo_videos.change(
            atualizar_qtd_videos_upload,
            inputs=[wizard_arquivo_videos],
            outputs=[wizard_qtd_principal],
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
            js="(codigo) => { if (codigo) { window.tokstanceCopiar(codigo); } }",
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
            outputs=[wizard_mensagem, wizard_convite, wizard_aviso],
        )

        #eventos da tela de rotulacao
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
        btn_voltar_hub_admin.click(
            voltar_hub_de_admin,
            inputs=[estado_sessao],
            outputs=[
                painel_hub,
                painel_admin,
                hub_admin_cards_html,
                hub_rotulador_cards_html,
                hub_saudacao,
                estado_sessao,
            ],
        )

        btn_excluir_tarefa_admin.click(
            excluir_tarefa_pelo_admin,
            inputs=[estado_sessao],
            outputs=[
                painel_hub,
                painel_admin,
                hub_mensagem,
                hub_admin_cards_html,
                hub_rotulador_cards_html,
                hub_saudacao,
                estado_sessao,
            ],
        )

        #carregamento de scripts no cliente para modo claro e alternancia de visualizacao de senha
        app.load(fn=None, js=JS_FORCAR_MODO_CLARO)

    return app
