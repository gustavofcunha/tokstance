"""Regressoes dos defeitos reportados na revisao visual e funcional da interface."""

from pathlib import Path
from typing import Any, Dict

import gradio as gr
import pandas as pd
import pytest

from tokstance.backend.repositories.database import BancoDadosSQLite
from tokstance.backend.repositories.study_repo import RepositorioEstudo
from tokstance.backend.repositories.user_repo import RepositorioUsuarios
from tokstance.backend.services.admin_service import ServicoAdministracao
from tokstance.backend.services.auth_service import ServicoAutenticacao
from tokstance.backend.services.queue_service import ServicoFilaAnotacao
from tokstance.config import CAMINHOS_PADRAO, resolver_diretorio_dados
from tokstance.frontend.components import renderizar_toast_html
from tokstance.frontend.gradio_ui import (
    construir_interface,
    renderizar_configuracao_admin_html,
    renderizar_hub_tabelas_html,
)
from tokstance.frontend.theme import APP_CSS


@pytest.fixture
def servicos(tmp_path: Path) -> Dict[str, Any]:
    banco = BancoDadosSQLite(tmp_path / "feedback.db")
    repo_u = RepositorioUsuarios(banco)
    repo_e = RepositorioEstudo(banco, repo_u)
    return {
        "auth": ServicoAutenticacao(banco, repo_u, repo_e, rodadas_bcrypt=4),
        "admin": ServicoAdministracao(banco, repo_u, repo_e),
        "fila": ServicoFilaAnotacao(banco, repo_u, repo_e),
    }


def _pool_de_videos() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "id": f"v{i}",
                "url": f"https://www.tiktok.com/@canal/video/{5000 + i}",
                "target": "Tema",
                "video_description": f"Descricao {i}",
                "voice_to_text": f"Transcricao {i}",
                "video_duration": "20.0",
            }
            for i in range(1, 7)
        ]
    )


def _criar_tarefa_com_rotulador(servicos: Dict[str, Any]) -> Dict[str, Any]:
    auth, admin = servicos["auth"], servicos["admin"]
    usuario = auth.cadastrar_usuario("gustavo", "senha123", email="g@exemplo.org")
    tarefa = admin.criar_nova_tarefa(
        usuario_administrador_id=int(usuario["usuario_id"]),
        pool_videos=_pool_de_videos(),
        quantidade_videos_principal=4,
        titulo="Tarefa",
        numero_vagas=1,
        percentual_sobreposicao=0.0,
        permitir_admin_como_rotulador=True,
    )
    return {"usuario": usuario, "tarefa": tarefa}


#hub status and button actions


@pytest.mark.unit
def test_painel_do_usuario_informa_total_da_fila_do_rotulador(servicos: Dict[str, Any]) -> None:
    contexto = _criar_tarefa_com_rotulador(servicos)

    painel = servicos["auth"].obter_painel_usuario(int(contexto["usuario"]["usuario_id"]))

    assert painel["tarefas_rotulador"][0]["total_videos_fila"] == 4


@pytest.mark.unit
def test_hub_troca_para_continuar_rotulacao_apos_primeira_anotacao(servicos: Dict[str, Any]) -> None:
    contexto = _criar_tarefa_com_rotulador(servicos)
    t_id = int(contexto["tarefa"]["tarefa_id"])
    estado = servicos["fila"].obter_estado_fila(tarefa_id=t_id, nome_usuario="gustavo", aviso_sensivel_aceito=True)
    opcao = estado["opcoes_posicao"][0]
    servicos["fila"].salvar_anotacao_e_avancar(
        tarefa_id=t_id,
        nome_usuario="gustavo",
        assignment_id=estado["video_atual"]["assignment_id"],
        posicao=opcao,
        tempo_analise_segundos=12.0,
    )

    painel = servicos["auth"].obter_painel_usuario(int(contexto["usuario"]["usuario_id"]))
    _, html_rotulador = renderizar_hub_tabelas_html([], painel["tarefas_rotulador"])

    assert "Continuar Rotulação" in html_rotulador
    assert "1 de 4 (25%)" in html_rotulador
    assert "Em andamento" in html_rotulador


@pytest.mark.unit
def test_hub_sem_anotacoes_mostra_iniciar_com_total_real(servicos: Dict[str, Any]) -> None:
    contexto = _criar_tarefa_com_rotulador(servicos)

    painel = servicos["auth"].obter_painel_usuario(int(contexto["usuario"]["usuario_id"]))
    _, html_rotulador = renderizar_hub_tabelas_html([], painel["tarefas_rotulador"])

    assert "Iniciar Rotulação" in html_rotulador
    assert "0 de 4 (0%)" in html_rotulador


@pytest.mark.unit
def test_painel_do_administrador_informa_vagas_ocupadas(servicos: Dict[str, Any]) -> None:
    contexto = _criar_tarefa_com_rotulador(servicos)

    painel = servicos["auth"].obter_painel_usuario(int(contexto["usuario"]["usuario_id"]))

    assert painel["tarefas_administrador"][0]["vagas_ocupadas"] == 1


@pytest.mark.unit
def test_tabela_do_hub_nao_depende_de_rolagem_horizontal() -> None:
    assert ".hub-table-wrapper { overflow-x: visible !important; margin: 4px 0 0 0 !important; }" in APP_CSS


#password recovery flow


@pytest.mark.unit
def test_solicitar_recuperacao_com_smtp_quebrado_nao_lanca_erro_de_logger(
    servicos: Dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    servicos["auth"].cadastrar_usuario("pesquisador", "senha123", email="p@exemplo.org")
    monkeypatch.setenv("SMTP_HOST", "servidor.invalido.local")
    monkeypatch.setenv("SMTP_PORT", "1")

    resultado = servicos["auth"].solicitar_recuperacao_senha("pesquisador")

    assert resultado["smtp_configurado"] is True
    assert resultado["disparado_smtp"] is False


@pytest.mark.unit
def test_verificar_codigo_recuperacao_aceita_codigo_valido_sem_consumi_lo(servicos: Dict[str, Any]) -> None:
    servicos["auth"].cadastrar_usuario("pesquisador", "senha123", email="p@exemplo.org")
    codigo = servicos["auth"].solicitar_recuperacao_senha("pesquisador")["codigo"]

    assert servicos["auth"].verificar_codigo_recuperacao("pesquisador", codigo) is True
    resultado = servicos["auth"].redefinir_senha_com_codigo("pesquisador", codigo, "novasenha1")

    assert resultado["sucesso"] is True


@pytest.mark.unit
def test_verificar_codigo_recuperacao_rejeita_codigo_incorreto(servicos: Dict[str, Any]) -> None:
    servicos["auth"].cadastrar_usuario("pesquisador", "senha123", email="p@exemplo.org")
    servicos["auth"].solicitar_recuperacao_senha("pesquisador")

    with pytest.raises(ValueError, match="inválido ou expirado"):
        servicos["auth"].verificar_codigo_recuperacao("pesquisador", "000000")


@pytest.mark.unit
def test_verificar_codigo_recuperacao_exige_codigo_preenchido(servicos: Dict[str, Any]) -> None:
    with pytest.raises(ValueError, match="código de 6 dígitos"):
        servicos["auth"].verificar_codigo_recuperacao("qualquer", "")


@pytest.mark.unit
def test_recuperacao_para_identificador_inexistente_nao_libera_etapa_do_codigo(servicos: Dict[str, Any]) -> None:
    with pytest.raises(ValueError, match="Nenhum usuário cadastrado"):
        servicos["auth"].solicitar_recuperacao_senha("ninguem@exemplo.org")


#ephemeral toasts and ui text checks


@pytest.mark.unit
def test_toast_de_sucesso_usa_animacao_que_o_faz_sumir() -> None:
    html = renderizar_toast_html("✅ Tarefa criada")

    assert "toast-sucesso" in html and "toast-curto" in html
    assert "animation: toast-vida 5s" in APP_CSS
    assert "visibility: hidden" in APP_CSS


@pytest.mark.unit
def test_toast_de_erro_e_inferido_pelo_prefixo() -> None:
    assert "toast-erro" in renderizar_toast_html("⚠️ Credenciais inválidas.")


@pytest.mark.unit
def test_toast_vazio_nao_renderiza_nada() -> None:
    assert renderizar_toast_html("") == ""


@pytest.mark.unit
def test_toast_de_tarefa_criada_oferece_botao_para_o_console() -> None:
    html = renderizar_toast_html(
        "✅ Tarefa criada", acao_rotulo="Ir para o Console da Tarefa", acao_tipo="admin", acao_tarefa_id=7
    )

    assert "tokstanceAcao('admin', '7')" in html
    assert "Ir para o Console da Tarefa" in html


@pytest.mark.unit
def test_toast_escapa_html_da_mensagem() -> None:
    assert "<script>" not in renderizar_toast_html("⚠️ <script>alert(1)</script>")


@pytest.mark.unit
def test_toast_nao_e_comprimido_pela_regra_do_container() -> None:
    assert ".toast-slot > div:not(.tokstance-toast)" in APP_CSS


@pytest.mark.unit
def test_interface_nao_exibe_a_palavra_gratuito() -> None:
    app = construir_interface()
    textos = [str(getattr(bloco, "value", "")) + str(getattr(bloco, "label", "")) for bloco in app.blocks.values()]

    assert not any("gratuit" in texto.lower() for texto in textos)


@pytest.mark.unit
def test_interface_nao_exibe_selo_acesso_ao_sistema() -> None:
    app = construir_interface()
    textos = [str(getattr(bloco, "value", "")) for bloco in app.blocks.values()]

    assert not any("Acesso ao Sistema" in texto for texto in textos)


#admin console and join modal


@pytest.mark.unit
def test_configuracao_do_console_tem_botao_de_copiar_ao_lado_do_codigo() -> None:
    html = renderizar_configuracao_admin_html(
        {"tarefa_id": 1, "codigo_convite": "TOK-ABC12345", "pergunta": "P", "opcoes_posicao": ["A", "B"]}
    )

    assert "tokstanceCopiar('TOK-ABC12345')" in html
    assert "config-code-row" in html


@pytest.mark.unit
def test_interface_possui_popup_de_convite_no_lugar_da_barra_fixa() -> None:
    app = construir_interface()
    classes = {str(getattr(bloco, "elem_classes", "")) for bloco in app.blocks.values()}

    assert any("modal-overlay" in c for c in classes)
    assert not any("hub-join-box" in c for c in classes)


@pytest.mark.unit
def test_gatilho_das_acoes_existe_fora_dos_paineis_ocultaveis() -> None:
    app = construir_interface()
    gatilho = next(b for b in app.blocks.values() if getattr(b, "elem_id", None) == "tokstance_hub_trigger")

    assert gatilho.visible is True
    ancestral = gatilho.parent
    while ancestral is not None and not isinstance(ancestral, gr.Blocks):
        elem_id = getattr(ancestral, "elem_id", "")
        assert elem_id not in {"painel_auth", "painel_hub", "painel_rotulacao", "painel_criacao", "painel_admin"}
        ancestral = getattr(ancestral, "parent", None)
    assert ancestral is app


#labeling workspace layout


@pytest.mark.unit
def test_player_do_workspace_usa_altura_da_janela() -> None:
    assert "--altura-player: clamp(" in APP_CSS
    assert "100vh" in APP_CSS


@pytest.mark.unit
def test_cabecalho_da_marca_fica_oculto_durante_a_rotulacao() -> None:
    assert ".brand-header" in APP_CSS and "labeler-panel:not(.hide)" in APP_CSS


#test isolation check


@pytest.mark.unit
def test_testes_nao_gravam_no_diretorio_de_dados_do_projeto() -> None:
    assert "tokstance_testes_" in str(resolver_diretorio_dados())
    assert "tokstance_testes_" in str(CAMINHOS_PADRAO.arquivo_videos)


#auth feedback and wrong password display


@pytest.mark.unit
def test_alerta_inline_de_senha_incorreta_renderiza_corretamente() -> None:
    #arrange
    from tokstance.frontend.gradio_ui import renderizar_aviso_inline

    #act
    html_erro = renderizar_aviso_inline("Credenciais inválidas: senha incorreta.")

    #assert
    assert "auth-inline-error" in html_erro
    assert "senha incorreta" in html_erro
    assert "role='alert'" in html_erro


#hub progress bar rendering and styling


@pytest.mark.unit
def test_barras_de_progresso_do_painel_principal_renderizam_corretamente() -> None:
    #arrange
    from tokstance.frontend.gradio_ui import renderizar_hub_tabelas_html

    t_adm = [{
        "tarefa_id": 1,
        "titulo": "Tarefa Demo Admin",
        "codigo_convite": "TOK-DEMO1234",
        "vagas_ocupadas": 2,
        "numero_vagas": 4,
        "progresso_percentual": 50.0,
    }]
    t_rot = [{
        "tarefa_id": 1,
        "titulo": "Tarefa Demo Rot",
        "videos_concluidos": 6,
        "total_videos_fila": 12,
    }]

    #act
    h_adm, h_rot = renderizar_hub_tabelas_html(t_adm, t_rot)

    #assert
    assert "table-bar-track" in h_adm
    assert "table-bar-fill" in h_adm
    assert "width:50%" in h_adm or "width: 50%" in h_adm

    assert "table-bar-track" in h_rot
    assert "table-bar-fill" in h_rot
    assert "width:50%" in h_rot or "width: 50%" in h_rot


#widescreen labeling layout without vertical scroll


@pytest.mark.unit
def test_workspace_rotulacao_widescreen_sem_rolagem_vertical_e_player_ampliado() -> None:
    #arrange
    from tokstance.frontend.theme import APP_CSS

    #assert
    assert "--altura-player: clamp(480px" in APP_CSS
    assert "grid-template-columns: 240px 1fr" in APP_CSS
    assert ".video-context-column" in APP_CSS
    assert "overflow-y: hidden !important;" in APP_CSS
    assert "body:has(.labeler-panel:not(.hide):not(.hidden))" in APP_CSS


#bold question styling and regular alternative options


@pytest.mark.unit
def test_pergunta_em_negrito_e_alternativas_sem_negrito() -> None:
    #arrange
    from tokstance.frontend.theme import APP_CSS
    from tokstance.frontend.components import video_outputs

    fila = [{"target": "AlvoTeste", "url": "https://www.tiktok.com/@u/video/1"}]

    #act
    _, _, _, pergunta_md, _ = video_outputs(fila, 0)

    #assert
    assert "target-question" in pergunta_md
    assert "<strong>" in pergunta_md
    assert ".target-question" in APP_CSS
    assert "font-weight: 700 !important;" in APP_CSS
    assert ".wrap-radio label" in APP_CSS
    assert "font-weight: 400 !important;" in APP_CSS


#target visual prominence and embedding in question


@pytest.mark.unit
def test_destaque_target_vermelho_e_embedado_na_pergunta() -> None:
    #arrange
    from tokstance.frontend.theme import APP_CSS
    from tokstance.frontend.components import formatar_pergunta_com_target, render_video_card

    item = {"target": "Lula", "url": "https://www.tiktok.com/@u/video/100"}

    #act
    pergunta_formatada = formatar_pergunta_com_target(
        "Qual a posição expressa no vídeo em relação ao target?", "Lula"
    )
    card_html = render_video_card(item, highlight_target=True)

    #assert target embedded with badge
    assert 'target-name-badge' in pergunta_formatada
    assert '"Lula"' in pergunta_formatada
    assert 'target-name-badge' in card_html
    assert 'Lula' in card_html

    #assert css styling has intense red accents and animations
    assert ".target-name-badge" in APP_CSS
    assert "color: #9c0014 !important;" in APP_CSS
    assert "target-badge-pulse" in APP_CSS
    assert "target-highlight" in APP_CSS


@pytest.mark.unit
def test_destaque_target_transicao_primeiro_video_e_mudanca_alvo() -> None:
    #arrange
    from tokstance.frontend.components import video_outputs

    fila = [
        {"target": "AlvoInicial", "url": "https://www.tiktok.com/@u/video/1"},
        {"target": "AlvoInicial", "url": "https://www.tiktok.com/@u/video/2"},
        {"target": "NovoAlvo", "url": "https://www.tiktok.com/@u/video/3"},
    ]

    #act posicao 0 com highlight_first habilitado
    _, card0, _, perg0, _ = video_outputs(fila, 0, highlight_first=True)
    #act posicao 1 (mesmo alvo)
    _, card1, _, perg1, _ = video_outputs(fila, 1)
    #act posicao 2 (mudanca de alvo)
    _, card2, _, perg2, _ = video_outputs(fila, 2)

    #assert primeiro video com highlight ativado
    assert "target-transition" in card0
    assert "target-transition" in perg0

    #assert segundo video sem transicao
    assert "target-transition" not in card1
    assert "target-transition" not in perg1

    #assert terceiro video com mudanca de alvo ativando transicao
    assert "target-transition" in card2
    assert "target-transition" in perg2


#auth inline feedback error and success alerts


@pytest.mark.unit
def test_renderizar_aviso_inline_sucesso_e_erro() -> None:
    #arrange
    from tokstance.frontend.gradio_ui import renderizar_aviso_inline

    #act
    html_erro = renderizar_aviso_inline("A nova senha e a confirmação de senha não coincidem.", tipo="erro")
    html_sucesso = renderizar_aviso_inline("Código confirmado com sucesso.", tipo="sucesso")

    #assert erro
    assert "auth-inline-error" in html_erro
    assert "não coincidem" in html_erro
    assert "⚠️" in html_erro
    assert "role='alert'" in html_erro

    #assert sucesso
    assert "auth-inline-success" in html_sucesso
    assert "Código confirmado" in html_sucesso
    assert "✓" in html_sucesso
    assert "role='alert'" in html_sucesso


@pytest.mark.unit
def test_estilos_css_auth_inline_error_e_success() -> None:
    #arrange
    from tokstance.frontend.theme import APP_CSS

    #assert classes no css
    assert ".auth-inline-error" in APP_CSS
    assert "color: #9c0014 !important;" in APP_CSS
    assert ".auth-inline-success" in APP_CSS
    assert "color: #166534 !important;" in APP_CSS
    assert "border-left: 4px solid #16a34a !important;" in APP_CSS


@pytest.mark.unit
def test_redefinicao_senha_mantem_tarefas_administradas_atribuidas_e_progresso_salvo(
    servicos: Dict[str, Any],
) -> None:
    #arrange cadastro de usuario criador e rotulador
    auth = servicos["auth"]
    admin = servicos["admin"]
    fila = servicos["fila"]

    u_info = auth.cadastrar_usuario("pesquisador_master", "senhaAntiga123", email="master@ufmg.br")
    u_id = int(u_info["usuario_id"])

    tarefa = admin.criar_nova_tarefa(
        usuario_administrador_id=u_id,
        pool_videos=_pool_de_videos(),
        numero_vagas=2,
        percentual_sobreposicao=50.0,
        permitir_admin_como_rotulador=True,
        titulo="Estudo Eleitoral",
    )
    t_id = int(tarefa["tarefa_id"])

    #act anota um video para consolidar progresso
    estado_ini = fila.obter_estado_fila(t_id, "pesquisador_master")
    as_id = estado_ini["video_atual"]["assignment_id"]
    fila.salvar_anotacao_e_avancar(t_id, "pesquisador_master", as_id, "Neutro", 8.5)

    #painel antes da redefinicao de senha
    painel_antes = auth.obter_painel_usuario(u_id)
    assert len(painel_antes["tarefas_administrador"]) == 1
    assert len(painel_antes["tarefas_rotulador"]) == 1
    assert painel_antes["tarefas_rotulador"][0]["videos_concluidos"] == 1

    #act redefinir senha com sucesso
    res_recup = auth.solicitar_recuperacao_senha("master@ufmg.br")
    cod = res_recup["codigo"]
    auth.verificar_codigo_recuperacao("master@ufmg.br", cod)
    res_redef = auth.redefinir_senha_com_codigo("master@ufmg.br", cod, "novaSenhaForte456")

    assert res_redef["sucesso"] is True
    assert res_redef["nome_usuario"] == "pesquisador_master"

    #assert login funciona com email e com nova senha
    login_res = auth.autenticar_usuario("master@ufmg.br", "novaSenhaForte456", permitir_reassumir=True)
    assert login_res["usuario_id"] == u_id
    assert login_res["nome_usuario"] == "pesquisador_master"

    #assert tarefas e progresso permanecem salvos e intactos
    painel_depois = auth.obter_painel_usuario(u_id)
    assert len(painel_depois["tarefas_administrador"]) == 1
    assert painel_depois["tarefas_administrador"][0]["tarefa_id"] == t_id
    assert len(painel_depois["tarefas_rotulador"]) == 1
    assert painel_depois["tarefas_rotulador"][0]["tarefa_id"] == t_id
    assert painel_depois["tarefas_rotulador"][0]["videos_concluidos"] == 1
    assert painel_depois["tarefas_rotulador"][0]["pendentes"] == painel_depois["tarefas_rotulador"][0]["total_videos_fila"] - 1

    #assert fila de rotulacao continua do ponto onde parou
    estado_pos = fila.obter_estado_fila(t_id, "pesquisador_master")
    assert estado_pos["posicao_concluida"] == 1
    assert estado_pos["video_atual"]["assignment_id"] != as_id


@pytest.mark.unit
def test_autenticar_usuario_aceita_nome_ou_email_case_insensitive(
    servicos: Dict[str, Any],
) -> None:
    auth = servicos["auth"]
    auth.cadastrar_usuario("cientista_dados", "senhaSegura123", email="cientista@ufmg.br")

    #login exato por nome
    res_1 = auth.autenticar_usuario("cientista_dados", "senhaSegura123", permitir_reassumir=True)
    assert res_1["nome_usuario"] == "cientista_dados"

    #login por email
    res_2 = auth.autenticar_usuario("cientista@ufmg.br", "senhaSegura123", permitir_reassumir=True)
    assert res_2["nome_usuario"] == "cientista_dados"

    #login case-insensitive por nome
    res_3 = auth.autenticar_usuario("CIENTISTA_DADOS", "senhaSegura123", permitir_reassumir=True)
    assert res_3["nome_usuario"] == "cientista_dados"

    #login case-insensitive por email
    res_4 = auth.autenticar_usuario("CIENTISTA@UFMG.BR", "senhaSegura123", permitir_reassumir=True)
    assert res_4["nome_usuario"] == "cientista_dados"





