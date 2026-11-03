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
    assert "--altura-player: clamp(560px, calc(100vh - 210px), 640px);" in APP_CSS


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
    assert "--altura-player: clamp(560px, calc(100vh - 210px), 640px);" in APP_CSS
    assert ".video-context-column" in APP_CSS
    assert ".video-player-column" in APP_CSS
    assert "body:has(.labeler-panel:not(.hide):not(.hidden))" in APP_CSS
    assert "overflow-y: auto !important;" in APP_CSS
    assert "max-width: 1560px !important;" in APP_CSS


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
def test_destaque_target_vermelho_apenas_no_card_e_pergunta_com_formatacao_padrao() -> None:
    #arrange
    from tokstance.frontend.theme import APP_CSS
    from tokstance.frontend.components import formatar_pergunta_com_target, render_video_card

    item = {"target": "Lula", "url": "https://www.tiktok.com/@u/video/100"}

    #act
    pergunta_formatada = formatar_pergunta_com_target(
        "Qual a posição expressa no vídeo em relação ao target?", "Lula"
    )
    card_html = render_video_card(item, highlight_target=True)

    #assert target na pergunta segue a formatacao dela sem badge vermelho
    assert "target-name-badge" not in pergunta_formatada
    assert '"Lula"' in pergunta_formatada

    #assert target no card ao lado do video permanece com badge destacado
    assert "target-name-badge" in card_html
    assert "Lula" in card_html

    #assert css styling do badge vermelho para o card e reset neutro na pergunta
    assert ".target-name-badge" in APP_CSS
    assert ".target-question .target-name-badge" in APP_CSS
    assert "color: inherit !important;" in APP_CSS
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


@pytest.mark.unit
def test_redefinir_senha_valida_requisitos_de_complexidade_e_exibe_mensagens_explicitas(
    servicos: Dict[str, Any],
) -> None:
    auth = servicos["auth"]
    auth.cadastrar_usuario("usuario_req", "senhaSegura123", email="req@ufmg.br")
    solic = auth.solicitar_recuperacao_senha("usuario_req")
    cod = solic["codigo"]

    #senha vazia ou nula
    with pytest.raises(ValueError, match="obrigatória"):
        auth.redefinir_senha_com_codigo("usuario_req", cod, "")

    #menos de 6 caracteres
    with pytest.raises(ValueError, match="mínimo de 6 caracteres"):
        auth.redefinir_senha_com_codigo("usuario_req", cod, "123")

    #somente letras sem numeros
    with pytest.raises(ValueError, match="ao menos uma letra e um número"):
        auth.redefinir_senha_com_codigo("usuario_req", cod, "somenteletras")

    #somente numeros sem letras
    with pytest.raises(ValueError, match="ao menos uma letra e um número"):
        auth.redefinir_senha_com_codigo("usuario_req", cod, "123456")

    #senha valida redefine com sucesso
    res = auth.redefinir_senha_com_codigo("usuario_req", cod, "novaSenhaValida123")
    assert res["sucesso"] is True


@pytest.mark.unit
def test_interface_redefinicao_senha_exibe_feedback_inline_e_toast_para_requisitos_invalidos(
    servicos: Dict[str, Any],
) -> None:
    app = construir_interface(
        servico_auth=servicos["auth"],
        servico_fila=servicos["fila"],
        servico_admin=servicos["admin"],
    )
    #encontra a funcao executar_redefinir_senha registrada nos blocos
    fn_redefinir = None
    for fn in app.fns.values():
        if getattr(fn.fn, "__name__", "") == "executar_redefinir_senha":
            fn_redefinir = fn.fn
            break
    assert fn_redefinir is not None

    #testa senha vazia
    saida_vazia = fn_redefinir("usuario_teste", "123456", "", "")
    toast_vazio = saida_vazia[0]
    aviso_vazio = saida_vazia[3]
    assert "obrigatória" in toast_vazio
    assert "obrigatória" in aviso_vazio
    assert "auth-inline-error" in aviso_vazio

    #testa senha curta menos de 6 caracteres
    saida_curta = fn_redefinir("usuario_teste", "123456", "abc", "abc")
    toast_curta = saida_curta[0]
    aviso_curta = saida_curta[3]
    assert "6 caracteres" in toast_curta and "mínimo" in toast_curta
    assert "6 caracteres" in aviso_curta and "mínimo" in aviso_curta

    #testa senha sem numeros
    saida_sem_num = fn_redefinir("usuario_teste", "123456", "semnumeros", "semnumeros")
    toast_sn = saida_sem_num[0]
    aviso_sn = saida_sem_num[3]
    assert "ao menos uma letra e um número" in toast_sn
    assert "ao menos uma letra e um número" in aviso_sn

    #testa confirmacao diferente
    saida_dif = fn_redefinir("usuario_teste", "123456", "senhaValida123", "outraSenha456")
    toast_dif = saida_dif[0]
    aviso_dif = saida_dif[3]
    assert "não coincidem" in toast_dif
    assert "não coincidem" in aviso_dif


@pytest.mark.unit
def test_interface_cadastro_valida_requisitos_complexidade_senha_e_exibe_aviso(
    servicos: Dict[str, Any],
) -> None:
    app = construir_interface(
        servico_auth=servicos["auth"],
        servico_fila=servicos["fila"],
        servico_admin=servicos["admin"],
    )
    fn_cadastro = None
    for fn in app.fns.values():
        if getattr(fn.fn, "__name__", "") == "executar_cadastro":
            fn_cadastro = fn.fn
            break
    assert fn_cadastro is not None

    #testa cadastro com nome completo vazio
    saida_sem_nome = fn_cadastro("", "novo_usuario", "novo@ufmg.br", "SenhaForte123", "SenhaForte123", "")
    toast_sem_nome = saida_sem_nome[2]
    aviso_sem_nome = saida_sem_nome[8]
    assert "nome completo" in toast_sem_nome.lower()
    assert "nome completo" in aviso_sem_nome.lower()

    #testa cadastro com senha sem numeros
    saida_sn = fn_cadastro("NOME COMPLETO", "novo_usuario", "novo@ufmg.br", "somenteletras", "somenteletras", "")
    toast_sn = saida_sn[2]
    aviso_sn = saida_sn[8]
    assert "ao menos uma letra e um número" in toast_sn
    assert "ao menos uma letra e um número" in aviso_sn

    #testa cadastro com senha vazia
    saida_vazia = fn_cadastro("NOME COMPLETO", "novo_usuario", "novo@ufmg.br", "", "", "")
    toast_vazia = saida_vazia[2]
    aviso_vazia = saida_vazia[8]
    assert "obrigatória" in toast_vazia
    assert "obrigatória" in aviso_vazia


@pytest.mark.unit
def test_cadastro_com_email_duplicado_lanca_erro_impedindo_sobreposicao_de_conta(
    servicos: Dict[str, Any],
) -> None:
    auth: ServicoAutenticacao = servicos["auth"]
    auth.cadastrar_usuario("pesquisador_original", "SenhaSegura123", email="duplicado@ufmg.br")

    with pytest.raises(ValueError, match="já está em uso por outra conta"):
        auth.cadastrar_usuario("pesquisador_invasor", "OutraSenhaSegura123", email="duplicado@ufmg.br")


@pytest.mark.unit
def test_cadastro_vincula_automaticamente_atribuicoes_e_progresso_pre_existentes(
    servicos: Dict[str, Any],
) -> None:
    auth: ServicoAutenticacao = servicos["auth"]
    admin: ServicoAdministracao = servicos["admin"]

    #admin cria tarefa incluindo rotulador que ainda nao possui conta no sistema
    admin_user = auth.cadastrar_usuario("admin_pesquisa", "SenhaValida123", email="admin@ufmg.br")
    tarefa = admin.repo_estudo.criar_tarefa(
        titulo="Estudo Pré-Cadastro",
        pergunta="Qual o posicionamento?",
        opcoes_posicao=["A favor", "Contra"],
        rotuladores_iniciais=["novo_aluno"],
        numero_vagas=1,
        pool_videos=_pool_de_videos(),
        criado_por_usuario_id=admin_user["usuario_id"],
    )

    #novo_aluno cadastra sua conta definindo sua primeira senha
    aluno = auth.cadastrar_usuario("novo_aluno", "SenhaValida123", email="novoaluno@ufmg.br")
    painel = auth.obter_painel_usuario(aluno["usuario_id"])

    assert len(painel["tarefas_rotulador"]) == 1
    assert painel["tarefas_rotulador"][0]["tarefa_id"] == tarefa["tarefa_id"]
    assert painel["tarefas_rotulador"][0]["total_videos_fila"] > 0


@pytest.mark.unit
def test_definicao_e_redefinicao_senha_preserva_tarefas_admin_rotulador_e_progresso_completo(
    servicos: Dict[str, Any],
) -> None:
    auth: ServicoAutenticacao = servicos["auth"]
    admin: ServicoAdministracao = servicos["admin"]
    fila: ServicoFilaAnotacao = servicos["fila"]

    #cria usuario inicial com tarefas sob administracao e atribuicao
    u = auth.cadastrar_usuario("lider_lab", "SenhaInicial123", email="lider@ufmg.br")
    uid = u["usuario_id"]

    tarefa = admin.repo_estudo.criar_tarefa(
        titulo="Rodada de Análise Laboratório",
        pergunta="Qual o posicionamento?",
        opcoes_posicao=["A favor", "Contra"],
        rotuladores_iniciais=["lider_lab", "colega_lab"],
        numero_vagas=2,
        pool_videos=_pool_de_videos(),
        criado_por_usuario_id=uid,
    )
    tid = tarefa["tarefa_id"]

    #rotula 2 videos na fila
    f1 = fila.obter_estado_fila(tid, "lider_lab")
    v1 = f1["video_atual"]
    fila.salvar_anotacao(tid, "lider_lab", v1["assignment_id"], posicao="A favor", tempo_analise_segundos=12.0)

    f2 = fila.obter_estado_fila(tid, "lider_lab")
    v2 = f2["video_atual"]
    fila.salvar_anotacao(tid, "lider_lab", v2["assignment_id"], posicao="Contra", tempo_analise_segundos=14.0)

    #verifica estado antes da redefinicao de senha
    painel_antes = auth.obter_painel_usuario(uid)
    assert len(painel_antes["tarefas_administrador"]) == 1
    assert len(painel_antes["tarefas_rotulador"]) == 1
    assert painel_antes["tarefas_rotulador"][0]["videos_concluidos"] == 2

    #redefine senha via codigo de recuperacao
    solic = auth.solicitar_recuperacao_senha("lider@ufmg.br")
    codigo = solic["codigo"]
    res_red = auth.redefinir_senha_com_codigo("lider@ufmg.br", codigo, "NovaSenhaLab456")
    assert res_red["sucesso"] is True

    #autentica com a nova senha
    dados_login = auth.autenticar_usuario("lider_lab", "NovaSenhaLab456")
    assert len(dados_login["tarefas_administrador"]) == 1
    assert len(dados_login["tarefas_rotulador"]) == 1
    assert dados_login["tarefas_rotulador"][0]["videos_concluidos"] == 2

    #verifica que a fila continua exatamente do video 3
    f3 = fila.obter_estado_fila(tid, "lider_lab")
    assert f3["posicao_concluida"] == 2
    assert f3["video_atual"]["assignment_id"] not in {v1["assignment_id"], v2["assignment_id"]}

    #rotula o terceiro video
    fila.salvar_anotacao(tid, "lider_lab", f3["video_atual"]["assignment_id"], posicao="A favor", tempo_analise_segundos=11.0)

    #autentica usando o e-mail em maiusculas para checar preservacao total
    dados_login_email = auth.autenticar_usuario("LIDER@UFMG.BR", "NovaSenhaLab456", permitir_reassumir=True)
    assert dados_login_email["tarefas_rotulador"][0]["videos_concluidos"] == 3


@pytest.mark.unit
def test_nome_completo_obrigatorio_e_em_maiusculas_no_banco_e_label_email_limpo(servicos: Dict[str, Any]) -> None:
    #arrange
    auth = servicos["auth"]
    banco = auth.banco
    from tokstance.frontend.theme import APP_CSS

    #assert css para campo de nome em maiusculo
    assert ".campo-nome-maiusculo input" in APP_CSS
    assert "text-transform: uppercase !important;" in APP_CSS

    #act cadastro com nome completo em minusculas e espacos
    usuario = auth.cadastrar_usuario(
        nome_usuario="anotador_maiusculo",
        senha="SenhaValida123",
        email="anotador@ufmg.br",
        nome_completo="  maria silva dos santos  ",
    )

    #assert retorno do servico com nome em maiusculas
    assert usuario["nome_completo"] == "MARIA SILVA DOS SANTOS"

    #assert gravacao direta no banco de dados sqlite em maiusculas
    registro = banco.consultar_um(
        "SELECT nome_usuario, nome_completo, email FROM usuarios WHERE nome_usuario = ?;",
        ("anotador_maiusculo",),
    )
    assert registro is not None
    assert registro["nome_completo"] == "MARIA SILVA DOS SANTOS"
    assert registro["email"] == "anotador@ufmg.br"


@pytest.mark.unit
def test_botoes_utilizam_icones_vetoriais_e_sem_emojis(servicos: Dict[str, Any]) -> None:
    #arrange
    from tokstance.frontend.theme import APP_CSS
    from tokstance.frontend.gradio_ui import construir_interface, renderizar_hub_tabelas_html, renderizar_configuracao_admin_html

    #assert classes css de mascaras vetoriais para botoes
    assert ".btn-icon-copiar::before" in APP_CSS
    assert ".btn-icon-refresh::before" in APP_CSS
    assert ".btn-icon-alerta::before" in APP_CSS
    assert ".btn-icon-logout::before" in APP_CSS
    assert ".btn-icon-trash::before" in APP_CSS
    assert "button.hub-plus-btn::before" in APP_CSS

    #assert tabela do hub contem icones svg e sem emojis
    _, html_rotulador = renderizar_hub_tabelas_html([], [{"tarefa_id": 1, "titulo": "T", "videos_concluidos": 0, "total_videos_fila": 10}])
    assert "hub-btn-icon" in html_rotulador
    assert "▶" not in html_rotulador

    #assert configuracao admin usa icone svg e sem emoji de prancheta
    html_config = renderizar_configuracao_admin_html({"tarefa_id": 1, "codigo_convite": "ABC12345"})
    assert "btn-svg-icon" in html_config
    assert "📋" not in html_config

    #assert interface montada nao possui emojis em botoes de acao
    app = construir_interface(
        servico_auth=servicos["auth"],
        servico_fila=servicos["fila"],
        servico_admin=servicos["admin"],
    )
    for blk in app.blocks.values():
        if getattr(blk, "get_block_name", lambda: "")() == "button":
            valor = str(getattr(blk, "value", "") or "")
            assert "📋" not in valor
            assert "🔄" not in valor
            assert "⚠️" not in valor


@pytest.mark.unit
def test_aplicacao_utiliza_tema_branco_uniforme() -> None:
    #arrange
    from tokstance.main import criar_aplicacao
    from tokstance.frontend.theme import obter_tema_branco, APP_CSS

    #act
    tema = obter_tema_branco()

    #assert tema base compativel com versao legado e tipografia uniforme
    assert isinstance(tema, gr.themes.Base)
    assert not isinstance(tema, gr.themes.Soft)
    assert "-apple-system" in str(tema.font) or "sans-serif" in str(tema.font)

    #assert css global aplica pilha de fontes do sistema uniforme sem fontes web parciais
    assert "font-family: -apple-system, BlinkMacSystemFont" in APP_CSS
    assert '"Inter"' not in APP_CSS


#horizontal workspace utilization and metadata cards proportion


@pytest.mark.unit
def test_workspace_layout_horizontal_e_proporcoes_cards() -> None:
    #arrange
    from tokstance.frontend.theme import APP_CSS

    #assert aproveitamento horizontal total do painel de rotulacao
    assert ".labeler-panel" in APP_CSS
    assert "max-width: 100% !important;" in APP_CSS
    assert "max-width: 1200px !important;" not in APP_CSS

    #assert coluna de metadados proporcional como informacao auxiliar
    assert ".video-context-column {" in APP_CSS
    assert "min-width: 240px !important;" in APP_CSS
    assert "max-width: 360px !important;" in APP_CSS

    #assert cards de transcricao e descricao com proporcao elegante
    assert ".video-transcription.unavailable," in APP_CSS
    assert "max-height: none !important;" in APP_CSS

    #assert espacamento vertical do botao de upload no card de videos
    assert ".wizard-file-upload button.center .wrap {" in APP_CSS
    assert "margin-top: 26px !important;" in APP_CSS


@pytest.mark.unit
def test_admin_console_remove_visoes_logins_e_sessoes() -> None:
    #arrange
    from tokstance.frontend.components import agreement_summary

    #act
    html = agreement_summary(
        agreement_data={},
        assignments_df=pd.DataFrame(),
        results_df=pd.DataFrame(),
        errors_df=pd.DataFrame(),
        videos_df=pd.DataFrame(),
        logs_df=pd.DataFrame(),
        version_name="rodada_teste",
    )

    #assert
    assert "Logins por dia" not in html
    assert "Sessões por anotador" not in html
    assert "Média geral:" not in html


@pytest.mark.unit
def test_admin_service_retorna_distribuicao_por_target(servicos: Dict[str, Any]) -> None:
    #arrange
    auth = servicos["auth"]
    admin = servicos["admin"]
    u = auth.cadastrar_usuario("adm_targets", "SenhaForte123")
    pool = pd.DataFrame(
        [
            {"id": "v1", "url": "https://tiktok.com/1", "target": "Escala 6x1", "video_description": "d1", "voice_to_text": "t1", "video_duration": "10.0"},
            {"id": "v2", "url": "https://tiktok.com/2", "target": "Escala 6x1", "video_description": "d2", "voice_to_text": "t2", "video_duration": "10.0"},
            {"id": "v3", "url": "https://tiktok.com/3", "target": "Economia", "video_description": "d3", "voice_to_text": "t3", "video_duration": "10.0"},
            {"id": "v4", "url": "https://tiktok.com/4", "target": "Economia", "video_description": "d4", "voice_to_text": "t4", "video_duration": "10.0"},
        ]
    )

    #act: distribui 2 principais e 2 vao para reserva
    tarefa = admin.criar_nova_tarefa(
        usuario_administrador_id=int(u["usuario_id"]),
        pool_videos=pool,
        quantidade_videos_principal=2,
    )
    metricas = admin.obter_metricas_operacionais(tarefa_id=int(tarefa["tarefa_id"]))

    #assert
    assert metricas["total_videos_acervo"] == 4
    assert metricas["total_videos_principais"] == 2
    assert metricas["total_videos_reservas"] == 2
    distribuicao = metricas["distribuicao_targets"]
    assert len(distribuicao) == 2
    alvos = {d["target"]: d for d in distribuicao}
    assert "Escala 6x1" in alvos
    assert "Economia" in alvos
    assert alvos["Escala 6x1"]["total"] == 2
    assert alvos["Economia"]["total"] == 2
    assert alvos["Escala 6x1"]["percentual"] == 50.0


@pytest.mark.unit
def test_renderizar_visao_geral_acervo_html() -> None:
    #arrange
    from tokstance.frontend.components import renderizar_visao_geral_acervo_html

    metricas = {
        "total_videos_acervo": 60,
        "total_videos_principais": 30,
        "total_videos_reservas": 30,
        "total_atribuicoes": 42,
        "distribuicao_targets": [
            {"target": "Reforma Tributária", "principais": 15, "reservas": 15, "total": 30, "percentual": 50.0},
            {"target": "Escala 6x1", "principais": 15, "reservas": 15, "total": 30, "percentual": 50.0},
        ],
    }

    #act
    html = renderizar_visao_geral_acervo_html(metricas)

    #assert
    assert "admin-collection-overview" in html
    assert "Visão Geral do Acervo e Distribuição Temática" in html
    assert "Total no Acervo" in html
    assert "60" in html
    assert "Vídeos a Distribuir" in html
    assert "Vídeos de Reserva" in html
    assert "Reforma Tributária" in html
    assert "Escala 6x1" in html
    assert "target-distribution-table" in html
    assert "Total Geral" in html


#workspace layout refactor brand header no box question and controls expansion


@pytest.mark.unit
def test_workspace_pergunta_sem_caixa_vermelha_e_sem_borda() -> None:
    #arrange
    from tokstance.frontend.theme import APP_CSS

    #assert pergunta sem caixa e sem fundo vermelho
    assert ".target-question," in APP_CSS
    assert "background: transparent !important;" in APP_CSS
    assert "border: none !important;" in APP_CSS
    assert "border-left: none !important;" in APP_CSS
    assert "box-shadow: none !important;" in APP_CSS


@pytest.mark.unit
def test_workspace_cabecalho_tarefa_e_rotulador_acima_do_target() -> None:
    #arrange
    from tokstance.frontend.components import render_video_card

    item = {
        "target": "Fim da Escala 6x1",
        "video_description": "Manifestação contra a escala 6x1.",
        "voice_to_text": "Texto da transcricao.",
        "url": "https://www.tiktok.com/@u/video/123",
    }

    #act
    html = render_video_card(
        item,
        highlight_target=True,
        tarefa_titulo="Detecção de Posição",
        rotulador_nome="gustavo",
    )

    #assert tarefa e rotulador acima do target
    assert "labeler-header-badge-wrapper" in html
    assert "Tarefa:" in html
    assert "Detecção de Posição" in html
    assert "Rotulador:" in html
    assert "gustavo" in html
    idx_cabecalho = html.find("labeler-header-badge-wrapper")
    idx_target = html.find("video-meta")
    assert idx_cabecalho < idx_target, "cabecalho da tarefa e rotulador deve ficar acima do target"


@pytest.mark.unit
def test_workspace_inclui_brand_header_visivel_e_controles_expandidos() -> None:
    #arrange
    from tokstance.frontend.theme import APP_CSS

    #assert brand header visivel no workspace
    assert "body:has(.labeler-panel:not(.hide):not(.hidden)) .brand-header," in APP_CSS
    assert "display: block !important;" in APP_CSS

    #assert coluna de controles expandida
    assert ".labeler-controls-column {" in APP_CSS
    assert "flex: 1 1 auto !important;" in APP_CSS










