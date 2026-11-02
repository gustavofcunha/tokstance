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
