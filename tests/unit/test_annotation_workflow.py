"""Testes unitarios para o fluxo de rotulacao, regra dos 10s de erro e protecoes."""

from pathlib import Path

import pandas as pd
import pytest

from tokstance.backend.repositories.database import BancoDadosSQLite
from tokstance.backend.services.auth_service import ServicoAutenticacao
from tokstance.backend.services.queue_service import ServicoFilaAnotacao


def _criar_cenario_teste(tmp_path: Path):
    banco = BancoDadosSQLite(tmp_path / "workflow.db")
    servico_auth = ServicoAutenticacao(banco=banco, rodadas_bcrypt=4)
    servico_fila = ServicoFilaAnotacao(banco=banco)

    usuario = servico_auth.cadastrar_usuario("rotulador_teste", "SenhaForte123")
    pool = pd.DataFrame(
        [
            {
                "id": "1001",
                "url": "https://www.tiktok.com/@u/video/1001",
                "target": "Clima",
                "video_description": "Debate clima",
                "voice_to_text": "Transcricao 1",
                "video_duration": "20.0",
            },
            {
                "id": "1002",
                "url": "https://www.tiktok.com/@u/video/1002",
                "target": "Economia",
                "video_description": "Debate economia",
                "voice_to_text": "Transcricao 2",
                "video_duration": "15.0",
            },
            {
                "id": "9001",
                "url": "https://www.tiktok.com/@u/video/9001",
                "target": "Clima",
                "video_description": "Reserva clima",
                "voice_to_text": "Transcricao reserva",
                "video_duration": "18.0",
            },
        ]
    )
    tarefa = servico_auth.repo_estudo.criar_tarefa(
        criado_por_usuario_id=usuario["usuario_id"],
        pool_videos=pool,
        quantidade_videos_principal=2,
        numero_vagas=1,
        codigo_convite="TOK-TEST1",
    )
    servico_auth.entrar_na_tarefa_por_convite(usuario["usuario_id"], "TOK-TEST1")
    return servico_fila, tarefa, usuario


@pytest.mark.unit
def test_aviso_conteudo_sensivel_ativo_inicialmente_e_desaparece_ao_aceitar(
    tmp_path: Path,
) -> None:
    servico_fila, tarefa, usuario = _criar_cenario_teste(tmp_path)

    estado_inicial = servico_fila.obter_estado_fila(
        tarefa["tarefa_id"], usuario["nome_usuario"]
    )
    estado_aceito = servico_fila.aceitar_aviso_conteudo_sensivel(
        tarefa["tarefa_id"], usuario["nome_usuario"]
    )

    assert estado_inicial["exibir_aviso_sensivel"] is True
    assert estado_aceito["exibir_aviso_sensivel"] is False
    assert estado_aceito["video_atual"] is not None


@pytest.mark.unit
def test_salvar_anotacao_exige_selecao_previa_de_opcao_valida(
    tmp_path: Path,
) -> None:
    servico_fila, tarefa, usuario = _criar_cenario_teste(tmp_path)
    estado = servico_fila.aceitar_aviso_conteudo_sensivel(
        tarefa["tarefa_id"], usuario["nome_usuario"]
    )
    aid = estado["video_atual"]["assignment_id"]

    with pytest.raises(ValueError, match="Selecione uma opção"):
        servico_fila.salvar_anotacao_e_avancar(
            tarefa["tarefa_id"], usuario["nome_usuario"], aid, None, 15.0
        )

    with pytest.raises(ValueError, match="Selecione uma opção"):
        servico_fila.salvar_anotacao_e_avancar(
            tarefa["tarefa_id"], usuario["nome_usuario"], aid, "   ", 15.0
        )


@pytest.mark.unit
def test_salvar_anotacao_valida_persiste_e_avanca_para_proximo_video(
    tmp_path: Path,
) -> None:
    servico_fila, tarefa, usuario = _criar_cenario_teste(tmp_path)
    estado = servico_fila.aceitar_aviso_conteudo_sensivel(
        tarefa["tarefa_id"], usuario["nome_usuario"]
    )
    aid = estado["video_atual"]["assignment_id"]

    resultado = servico_fila.salvar_anotacao_e_avancar(
        tarefa["tarefa_id"], usuario["nome_usuario"], aid, "Contra", 16.5
    )
    proximo_estado = resultado["estado_fila"]

    assert resultado["anotacao_salva"]["stance"] == "Contra"
    assert proximo_estado["posicao_concluida"] == 1
    assert proximo_estado["pendentes"] == 1
    assert proximo_estado["video_atual"]["assignment_id"] != aid


@pytest.mark.unit
def test_reportar_erro_bloqueia_antes_de_dez_segundos(
    tmp_path: Path,
) -> None:
    servico_fila, tarefa, usuario = _criar_cenario_teste(tmp_path)
    estado = servico_fila.aceitar_aviso_conteudo_sensivel(
        tarefa["tarefa_id"], usuario["nome_usuario"]
    )
    aid = estado["video_atual"]["assignment_id"]

    with pytest.raises(ValueError, match="Aguarde pelo menos 10 segundos"):
        servico_fila.reportar_erro_video(
            tarefa["tarefa_id"], usuario["nome_usuario"], aid, 7.5
        )


@pytest.mark.unit
def test_reportar_erro_apos_dez_segundos_substitui_por_reserva_compativel(
    tmp_path: Path,
) -> None:
    servico_fila, tarefa, usuario = _criar_cenario_teste(tmp_path)
    estado = servico_fila.aceitar_aviso_conteudo_sensivel(
        tarefa["tarefa_id"], usuario["nome_usuario"]
    )
    aid = estado["video_atual"]["assignment_id"]

    resultado_erro = servico_fila.reportar_erro_video(
        tarefa["tarefa_id"], usuario["nome_usuario"], aid, 11.2
    )
    novo_video = resultado_erro["estado_fila"]["video_atual"]

    assert resultado_erro["status_substituicao"] == "SUBSTITUIDO_OVERLAP"
    assert novo_video["video_id"] == "9001"
    assert novo_video["target"] == "Clima"


@pytest.mark.unit
def test_parar_rotulacao_registra_evento_de_auditoria_em_logs_acesso(
    tmp_path: Path,
) -> None:
    servico_fila, tarefa, usuario = _criar_cenario_teste(tmp_path)

    resultado = servico_fila.parar_rotulacao(
        tarefa["tarefa_id"], usuario["nome_usuario"], tempo_desde_login_segundos=42.0
    )
    logs_df = servico_fila.repo_estudo.carregar_logs_acesso_df(tarefa["tarefa_id"])

    assert resultado["interrompido"] is True
    assert "parar_rotulacao" in logs_df["acao"].tolist()
