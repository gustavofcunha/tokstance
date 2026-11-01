"""Interface Gradio completa: Login, Cadastro e Hub Inicial de Tarefas (versao inicial do frontend)."""

from html import escape
import json
import time
from typing import Any, Dict, List, Optional, Tuple
import gradio as gr

from tokstance.backend.repositories.database import BancoDadosSQLite
from tokstance.backend.repositories.study_repo import RepositorioEstudo
from tokstance.backend.repositories.user_repo import RepositorioUsuarios
from tokstance.backend.services.admin_service import ServicoAdministracao
from tokstance.backend.services.auth_service import ServicoAutenticacao
from tokstance.backend.services.queue_service import ServicoFilaAnotacao
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
            # 3. TELA DE CRIACAO DE TAREFA (WIZARD) - Scaffolding C49
            # ==================================================================
            with gr.Column(visible=False, elem_classes="admin-panel") as painel_wizard:
                with gr.Row(elem_classes="admin-header"):
                    gr.Markdown("## Criador de Nova Tarefa de Pesquisa")
                    with gr.Row(elem_classes="admin-actions"):
                        btn_voltar_hub_wizard = gr.Button("Voltar ao Hub", elem_classes="error-btn")
                wizard_placeholder = gr.Markdown("Formulário de criação de tarefa em inicialização...")

            # ==================================================================
            # 4. TELA DE ROTULACAO (WORKSPACE) - Scaffolding C49
            # ==================================================================
            with gr.Column(visible=False, elem_classes="labeler-panel") as painel_rotulador:
                with gr.Row(elem_classes="labeler-actions"):
                    btn_voltar_hub_rotulacao = gr.Button("Salvar e sair", elem_classes="ufmg-btn")
                workspace_placeholder = gr.Markdown("Espaço do rotulador em inicialização...")

            # ==================================================================
            # 5. TELA DE ADMINISTRACAO (CONSOLE) - Scaffolding C49
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

    return app
