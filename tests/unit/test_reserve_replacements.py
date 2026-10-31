"""Testes unitarios para substituicao por videos reserva e rebalanceamento de sobreposicao."""

import pandas as pd
import pytest

from tokstance.backend.domain.assignments import gerar_atribuicoes
from tokstance.backend.domain.models import (
    COLUNAS_ERRO,
    COLUNAS_RESULTADO,
    carregar_videos,
)
from tokstance.backend.domain.replacements import (
    aplicar_substituicoes_reserva,
    carregar_atribuicoes,
    garantir_esquema_resultados,
    ler_erros_atribuicoes,
    ler_resultados,
)


def _gravar_linhas_erro(arquivo_erros, linhas: list[dict[str, str]]) -> None:
    pd.DataFrame(linhas, columns=list(COLUNAS_ERRO)).to_csv(arquivo_erros, index=False)


@pytest.mark.unit
def test_aplicar_substituicoes_reserva_substitui_video_individual_por_reserva_compativel(
    caminhos_estudo,
) -> None:
    videos = carregar_videos(caminhos_estudo.arquivo_videos)
    config = {"rotuladores": ["alice", "bob"], "percentual_sobreposicao": 0.0}
    atribuicoes = gerar_atribuicoes(
        config,
        videos,
        persistir=True,
        arquivo_atribuicoes=caminhos_estudo.arquivo_atribuicoes,
    )
    linha_falha = atribuicoes[
        (atribuicoes["labeler"] == "alice")
        & (atribuicoes["video_id"] == "7100000000000000001")
    ].iloc[0]
    _gravar_linhas_erro(
        caminhos_estudo.arquivo_erros,
        [
            {
                "timestamp": "2026-10-31 12:00:00",
                "video_id": str(linha_falha["video_id"]),
                "url": str(linha_falha["url"]),
                "labeler": "alice",
                "assignment_id": str(linha_falha["assignment_id"]),
                "replacement_video_id": "",
                "replacement_url": "",
                "replacement_assignment_id": "",
                "replacement_status": "",
            }
        ],
    )

    atualizadas = aplicar_substituicoes_reserva(
        atribuicoes, diretorio_dados=caminhos_estudo.diretorio_base
    )
    erros_persistidos = ler_erros_atribuicoes(caminhos_estudo.arquivo_erros)

    assert erros_persistidos.loc[0, "replacement_video_id"] == "7900000000000000001"
    assert erros_persistidos.loc[0, "replacement_status"] == "SUBSTITUIDO_OVERLAP"
    assert "7900000000000000001" in set(
        atualizadas[atualizadas["labeler"] == "alice"]["video_id"]
    )


@pytest.mark.unit
def test_aplicar_substituicoes_reserva_nao_reutiliza_reserva_consumida_em_falhas_distintas(
    caminhos_estudo,
) -> None:
    videos = carregar_videos(caminhos_estudo.arquivo_videos)
    config = {"rotuladores": ["alice", "bob"], "percentual_sobreposicao": 0.0}
    atribuicoes = gerar_atribuicoes(
        config,
        videos,
        persistir=True,
        arquivo_atribuicoes=caminhos_estudo.arquivo_atribuicoes,
    )
    primeiro_clima = atribuicoes[
        atribuicoes["video_id"] == "7100000000000000001"
    ].iloc[0]
    segundo_clima = atribuicoes[
        atribuicoes["video_id"] == "7100000000000000002"
    ].iloc[0]
    _gravar_linhas_erro(
        caminhos_estudo.arquivo_erros,
        [
            {
                "timestamp": "2026-10-31 12:00:00",
                "video_id": str(primeiro_clima["video_id"]),
                "url": str(primeiro_clima["url"]),
                "labeler": str(primeiro_clima["labeler"]),
                "assignment_id": str(primeiro_clima["assignment_id"]),
                "replacement_video_id": "",
                "replacement_url": "",
                "replacement_assignment_id": "",
                "replacement_status": "",
            },
            {
                "timestamp": "2026-10-31 12:01:00",
                "video_id": str(segundo_clima["video_id"]),
                "url": str(segundo_clima["url"]),
                "labeler": str(segundo_clima["labeler"]),
                "assignment_id": str(segundo_clima["assignment_id"]),
                "replacement_video_id": "",
                "replacement_url": "",
                "replacement_assignment_id": "",
                "replacement_status": "",
            },
        ],
    )

    aplicar_substituicoes_reserva(
        atribuicoes, diretorio_dados=caminhos_estudo.diretorio_base
    )
    erros_persistidos = ler_erros_atribuicoes(caminhos_estudo.arquivo_erros)

    assert erros_persistidos.loc[0, "replacement_video_id"] == "7900000000000000001"
    assert erros_persistidos.loc[1, "replacement_video_id"] == ""
    assert erros_persistidos.loc[1, "replacement_status"] == "SEM_RESERVA_COMPATIVEL"


@pytest.mark.unit
def test_aplicar_substituicoes_reserva_registra_sem_reserva_compativel_quando_target_ausente(
    caminhos_estudo,
) -> None:
    pd.DataFrame(
        [
            {
                "id": "7900000000000000099",
                "url": "https://www.tiktok.com/@reserve/video/7900000000000000099",
                "target": "Esportes",
            }
        ]
    ).to_csv(caminhos_estudo.arquivo_videos_reserva, index=False)
    videos = carregar_videos(caminhos_estudo.arquivo_videos)
    config = {"rotuladores": ["alice"], "percentual_sobreposicao": 0.0}
    atribuicoes = gerar_atribuicoes(
        config,
        videos,
        persistir=True,
        arquivo_atribuicoes=caminhos_estudo.arquivo_atribuicoes,
    )
    linha_falha = atribuicoes.iloc[0]
    _gravar_linhas_erro(
        caminhos_estudo.arquivo_erros,
        [
            {
                "timestamp": "2026-10-31 12:00:00",
                "video_id": str(linha_falha["video_id"]),
                "url": str(linha_falha["url"]),
                "labeler": "alice",
                "assignment_id": str(linha_falha["assignment_id"]),
                "replacement_video_id": "",
                "replacement_url": "",
                "replacement_assignment_id": "",
                "replacement_status": "",
            }
        ],
    )

    aplicar_substituicoes_reserva(
        atribuicoes, diretorio_dados=caminhos_estudo.diretorio_base
    )
    erros_persistidos = ler_erros_atribuicoes(caminhos_estudo.arquivo_erros)

    assert erros_persistidos.loc[0, "replacement_status"] == "SEM_RESERVA_COMPATIVEL"


@pytest.mark.unit
def test_aplicar_substituicoes_reserva_registra_sem_reserva_disponivel_quando_reservas_esgotadas(
    caminhos_estudo,
) -> None:
    pd.DataFrame(
        [
            {
                "id": "7100000000000000001",
                "url": "https://www.tiktok.com/@creator1/video/7100000000000000001",
                "target": "Clima",
            }
        ]
    ).to_csv(caminhos_estudo.arquivo_videos_reserva, index=False)
    videos = carregar_videos(caminhos_estudo.arquivo_videos)
    config = {"rotuladores": ["alice"], "percentual_sobreposicao": 0.0}
    atribuicoes = gerar_atribuicoes(
        config,
        videos,
        persistir=True,
        arquivo_atribuicoes=caminhos_estudo.arquivo_atribuicoes,
    )
    linha_falha = atribuicoes.iloc[0]
    _gravar_linhas_erro(
        caminhos_estudo.arquivo_erros,
        [
            {
                "timestamp": "2026-10-31 12:00:00",
                "video_id": str(linha_falha["video_id"]),
                "url": str(linha_falha["url"]),
                "labeler": "alice",
                "assignment_id": str(linha_falha["assignment_id"]),
                "replacement_video_id": "",
                "replacement_url": "",
                "replacement_assignment_id": "",
                "replacement_status": "",
            }
        ],
    )

    aplicar_substituicoes_reserva(
        atribuicoes, diretorio_dados=caminhos_estudo.diretorio_base
    )
    erros_persistidos = ler_erros_atribuicoes(caminhos_estudo.arquivo_erros)

    assert erros_persistidos.loc[0, "replacement_status"] == "SEM_RESERVA_DISPONIVEL"


@pytest.mark.unit
def test_aplicar_substituicoes_reserva_compartilha_mesma_reserva_em_grupo_sobreposicao_nao_anotado(
    caminhos_estudo,
) -> None:
    videos = carregar_videos(caminhos_estudo.arquivo_videos)
    config = {"rotuladores": ["alice", "bob"], "percentual_sobreposicao": 100.0}
    atribuicoes = gerar_atribuicoes(
        config,
        videos,
        persistir=True,
        arquivo_atribuicoes=caminhos_estudo.arquivo_atribuicoes,
    )
    linha_alice = atribuicoes[
        (atribuicoes["labeler"] == "alice")
        & (atribuicoes["video_id"] == "7100000000000000001")
    ].iloc[0]
    _gravar_linhas_erro(
        caminhos_estudo.arquivo_erros,
        [
            {
                "timestamp": "2026-10-31 12:00:00",
                "video_id": str(linha_alice["video_id"]),
                "url": str(linha_alice["url"]),
                "labeler": "alice",
                "assignment_id": str(linha_alice["assignment_id"]),
                "replacement_video_id": "",
                "replacement_url": "",
                "replacement_assignment_id": "",
                "replacement_status": "",
            }
        ],
    )

    atualizadas = aplicar_substituicoes_reserva(
        atribuicoes, diretorio_dados=caminhos_estudo.diretorio_base
    )
    videos_alice = set(atualizadas[atualizadas["labeler"] == "alice"]["video_id"])
    videos_bob = set(atualizadas[atualizadas["labeler"] == "bob"]["video_id"])

    assert "7900000000000000001" in videos_alice
    assert "7900000000000000001" in videos_bob
    assert "7100000000000000001" not in videos_alice
    assert "7100000000000000001" not in videos_bob


@pytest.mark.unit
def test_aplicar_substituicoes_reserva_promove_video_individual_concluido_em_sobreposicao_parcial(
    caminhos_estudo,
) -> None:
    videos = carregar_videos(caminhos_estudo.arquivo_videos)
    config = {"rotuladores": ["alice", "bob"], "percentual_sobreposicao": 50.0}
    atribuicoes = gerar_atribuicoes(
        config,
        videos,
        persistir=True,
        arquivo_atribuicoes=caminhos_estudo.arquivo_atribuicoes,
    )
    alice_sobreposicao = atribuicoes[
        (atribuicoes["labeler"] == "alice")
        & (atribuicoes["video_id"] == "7100000000000000001")
    ].iloc[0]
    bob_sobreposicao = atribuicoes[
        (atribuicoes["labeler"] == "bob")
        & (atribuicoes["video_id"] == "7100000000000000001")
    ].iloc[0]
    alice_individual = atribuicoes[
        (atribuicoes["labeler"] == "alice")
        & (atribuicoes["video_id"] == "7100000000000000002")
    ].iloc[0]
    pd.DataFrame(
        [
            {
                "timestamp": "2026-10-31 12:00:00",
                "labeler": "alice",
                "video_id": str(alice_sobreposicao["video_id"]),
                "url": str(alice_sobreposicao["url"]),
                "target": str(alice_sobreposicao["target"]),
                "stance": "Contra",
                "tempo_analise_segundos": "21.0",
                "video_duration": "25.0",
                "assignment_id": str(alice_sobreposicao["assignment_id"]),
            },
            {
                "timestamp": "2026-10-31 12:01:00",
                "labeler": "alice",
                "video_id": str(alice_individual["video_id"]),
                "url": str(alice_individual["url"]),
                "target": str(alice_individual["target"]),
                "stance": "A Favor",
                "tempo_analise_segundos": "28.0",
                "video_duration": "30.0",
                "assignment_id": str(alice_individual["assignment_id"]),
            },
        ],
        columns=list(COLUNAS_RESULTADO),
    ).to_csv(caminhos_estudo.arquivo_resultados, index=False)
    _gravar_linhas_erro(
        caminhos_estudo.arquivo_erros,
        [
            {
                "timestamp": "2026-10-31 12:02:00",
                "video_id": str(bob_sobreposicao["video_id"]),
                "url": str(bob_sobreposicao["url"]),
                "labeler": "bob",
                "assignment_id": str(bob_sobreposicao["assignment_id"]),
                "replacement_video_id": "",
                "replacement_url": "",
                "replacement_assignment_id": "",
                "replacement_status": "",
            }
        ],
    )

    atualizadas = aplicar_substituicoes_reserva(
        atribuicoes, diretorio_dados=caminhos_estudo.diretorio_base
    )
    erros_persistidos = ler_erros_atribuicoes(caminhos_estudo.arquivo_erros)

    assert (
        erros_persistidos.loc[0, "replacement_status"]
        == "SUBSTITUIDO_OVERLAP_REBALANCEADO"
    )
    assert erros_persistidos.loc[0, "replacement_video_id"] == "7100000000000000002"
    assert "7100000000000000002" in set(
        atualizadas[atualizadas["labeler"] == "bob"]["video_id"]
    )


@pytest.mark.unit
def test_aplicar_substituicoes_reserva_propaga_video_promovido_a_todos_membros_pendentes(
    caminhos_estudo,
) -> None:
    videos = carregar_videos(caminhos_estudo.arquivo_videos)
    config = {"rotuladores": ["alice", "bob", "carol"], "percentual_sobreposicao": 50.0}
    atribuicoes = gerar_atribuicoes(
        config,
        videos,
        persistir=True,
        arquivo_atribuicoes=caminhos_estudo.arquivo_atribuicoes,
    )
    alice_sobreposicao = atribuicoes[
        (atribuicoes["labeler"] == "alice")
        & (atribuicoes["video_id"] == "7100000000000000001")
    ].iloc[0]
    bob_sobreposicao = atribuicoes[
        (atribuicoes["labeler"] == "bob")
        & (atribuicoes["video_id"] == "7100000000000000001")
    ].iloc[0]
    alice_individual = atribuicoes[
        (atribuicoes["labeler"] == "alice")
        & (atribuicoes["video_id"] == "7100000000000000002")
    ].iloc[0]
    pd.DataFrame(
        [
            {
                "timestamp": "2026-10-31 12:00:00",
                "labeler": "alice",
                "video_id": str(alice_sobreposicao["video_id"]),
                "url": str(alice_sobreposicao["url"]),
                "target": str(alice_sobreposicao["target"]),
                "stance": "Contra",
                "tempo_analise_segundos": "21.0",
                "video_duration": "25.0",
                "assignment_id": str(alice_sobreposicao["assignment_id"]),
            },
            {
                "timestamp": "2026-10-31 12:01:00",
                "labeler": "alice",
                "video_id": str(alice_individual["video_id"]),
                "url": str(alice_individual["url"]),
                "target": str(alice_individual["target"]),
                "stance": "Neutro",
                "tempo_analise_segundos": "25.0",
                "video_duration": "30.0",
                "assignment_id": str(alice_individual["assignment_id"]),
            },
        ],
        columns=list(COLUNAS_RESULTADO),
    ).to_csv(caminhos_estudo.arquivo_resultados, index=False)
    _gravar_linhas_erro(
        caminhos_estudo.arquivo_erros,
        [
            {
                "timestamp": "2026-10-31 12:02:00",
                "video_id": str(bob_sobreposicao["video_id"]),
                "url": str(bob_sobreposicao["url"]),
                "labeler": "bob",
                "assignment_id": str(bob_sobreposicao["assignment_id"]),
                "replacement_video_id": "",
                "replacement_url": "",
                "replacement_assignment_id": "",
                "replacement_status": "",
            }
        ],
    )

    atualizadas = aplicar_substituicoes_reserva(
        atribuicoes, diretorio_dados=caminhos_estudo.diretorio_base
    )
    videos_carol = set(atualizadas[atualizadas["labeler"] == "carol"]["video_id"])

    assert "7100000000000000002" in videos_carol
    assert "7100000000000000001" not in videos_carol


@pytest.mark.unit
def test_aplicar_substituicoes_reserva_emite_critico_overlap_inconsistente_sem_candidato_promocao(
    caminhos_estudo,
) -> None:
    videos = carregar_videos(caminhos_estudo.arquivo_videos)
    config = {"rotuladores": ["alice", "bob"], "percentual_sobreposicao": 100.0}
    atribuicoes = gerar_atribuicoes(
        config,
        videos,
        persistir=True,
        arquivo_atribuicoes=caminhos_estudo.arquivo_atribuicoes,
    )
    alice_sobreposicao = atribuicoes[
        (atribuicoes["labeler"] == "alice")
        & (atribuicoes["video_id"] == "7100000000000000001")
    ].iloc[0]
    bob_sobreposicao = atribuicoes[
        (atribuicoes["labeler"] == "bob")
        & (atribuicoes["video_id"] == "7100000000000000001")
    ].iloc[0]
    pd.DataFrame(
        [
            {
                "timestamp": "2026-10-31 12:00:00",
                "labeler": "alice",
                "video_id": str(alice_sobreposicao["video_id"]),
                "url": str(alice_sobreposicao["url"]),
                "target": str(alice_sobreposicao["target"]),
                "stance": "Contra",
                "tempo_analise_segundos": "22.0",
                "video_duration": "25.0",
                "assignment_id": str(alice_sobreposicao["assignment_id"]),
            }
        ],
        columns=list(COLUNAS_RESULTADO),
    ).to_csv(caminhos_estudo.arquivo_resultados, index=False)
    _gravar_linhas_erro(
        caminhos_estudo.arquivo_erros,
        [
            {
                "timestamp": "2026-10-31 12:02:00",
                "video_id": str(bob_sobreposicao["video_id"]),
                "url": str(bob_sobreposicao["url"]),
                "labeler": "bob",
                "assignment_id": str(bob_sobreposicao["assignment_id"]),
                "replacement_video_id": "",
                "replacement_url": "",
                "replacement_assignment_id": "",
                "replacement_status": "",
            }
        ],
    )

    atualizadas = aplicar_substituicoes_reserva(
        atribuicoes, diretorio_dados=caminhos_estudo.diretorio_base
    )
    erros_persistidos = ler_erros_atribuicoes(caminhos_estudo.arquivo_erros)

    assert (
        erros_persistidos.loc[0, "replacement_status"] == "CRITICO_OVERLAP_INCONSISTENTE"
    )
    assert "7100000000000000001" in set(
        atualizadas[atualizadas["labeler"] == "alice"]["video_id"]
    )
    assert "7900000000000000001" in set(
        atualizadas[atualizadas["labeler"] == "bob"]["video_id"]
    )


@pytest.mark.unit
def test_carregar_atribuicoes_reaproveita_atribuicoes_persistidas_da_mesma_versao(
    caminhos_estudo,
) -> None:
    videos = carregar_videos(caminhos_estudo.arquivo_videos)
    config = {"rotuladores": ["alice", "bob"], "percentual_sobreposicao": 50.0}
    iniciais = gerar_atribuicoes(
        config,
        videos,
        persistir=True,
        arquivo_atribuicoes=caminhos_estudo.arquivo_atribuicoes,
    )
    linha_falha = iniciais[
        (iniciais["labeler"] == "alice")
        & (iniciais["video_id"] == "7100000000000000001")
    ].iloc[0]
    _gravar_linhas_erro(
        caminhos_estudo.arquivo_erros,
        [
            {
                "timestamp": "2026-10-31 12:00:00",
                "video_id": str(linha_falha["video_id"]),
                "url": str(linha_falha["url"]),
                "labeler": "alice",
                "assignment_id": str(linha_falha["assignment_id"]),
                "replacement_video_id": "",
                "replacement_url": "",
                "replacement_assignment_id": "",
                "replacement_status": "",
            }
        ],
    )

    carregadas = carregar_atribuicoes(
        config, videos, diretorio_dados=caminhos_estudo.diretorio_base
    )

    assert "7900000000000000001" in set(carregadas["video_id"])


@pytest.mark.unit
def test_garantir_esquema_resultados_preenche_duracao_e_id_legado_ausentes(
    caminhos_estudo,
) -> None:
    pd.DataFrame(
        [
            {
                "timestamp": "2026-10-31 12:00:00",
                "labeler": "alice",
                "video_id": "7100000000000000001",
                "url": "https://www.tiktok.com/@creator1/video/7100000000000000001",
                "target": "Clima",
                "stance": "Contra",
                "tempo_analise_segundos": "20.0",
            }
        ]
    ).to_csv(caminhos_estudo.arquivo_resultados, index=False)

    garantir_esquema_resultados(diretorio_dados=caminhos_estudo.diretorio_base)
    migrados = ler_resultados(caminhos_estudo.arquivo_resultados)

    assert migrados.loc[0, "video_duration"] == "25.0"
    assert migrados.loc[0, "assignment_id"] == "legacy:alice:7100000000000000001"
