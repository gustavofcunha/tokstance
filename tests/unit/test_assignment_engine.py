"""Testes unitarios para o motor de atribuicoes balanceado por target e sobreposicao."""

import pandas as pd
import pytest

from tokstance.backend.domain.assignments import (
    gerar_atribuicoes,
    identificador_atribuicao,
    versao_atribuicao,
    vincular_ou_alocar_vaga_rotulador,
)
from tokstance.backend.domain.models import COLUNAS_ATRIBUICAO, carregar_videos


@pytest.mark.unit
def test_gerar_atribuicoes_sem_rotuladores_retorna_dataframe_vazio(
    caminhos_estudo,
) -> None:
    videos = carregar_videos(caminhos_estudo.arquivo_videos)
    config = {"rotuladores": [], "percentual_sobreposicao": 50.0}

    atribuidos = gerar_atribuicoes(config, videos, persistir=False)

    assert atribuidos.empty
    assert tuple(atribuidos.columns) == COLUNAS_ATRIBUICAO


@pytest.mark.unit
def test_gerar_atribuicoes_sobreposicao_zero_particiona_todos_os_videos_sem_duplicar(
    caminhos_estudo,
) -> None:
    videos = carregar_videos(caminhos_estudo.arquivo_videos)
    config = {"rotuladores": ["alice", "bob"], "percentual_sobreposicao": 0.0}

    atribuidos = gerar_atribuicoes(config, videos, persistir=False)
    ids_alice = set(atribuidos[atribuidos["labeler"] == "alice"]["video_id"])
    ids_bob = set(atribuidos[atribuidos["labeler"] == "bob"]["video_id"])

    assert len(ids_alice) == 2
    assert len(ids_bob) == 2
    assert ids_alice.isdisjoint(ids_bob)
    assert ids_alice.union(ids_bob) == set(videos["id"])


@pytest.mark.unit
def test_gerar_atribuicoes_cinquenta_porcento_sobreposicao_compartilha_metade_e_divide_restante(
    caminhos_estudo,
) -> None:
    videos = carregar_videos(caminhos_estudo.arquivo_videos)
    config = {"rotuladores": ["alice", "bob"], "percentual_sobreposicao": 50.0}

    atribuidos = gerar_atribuicoes(config, videos, persistir=False)
    ids_alice = set(atribuidos[atribuidos["labeler"] == "alice"]["video_id"])
    ids_bob = set(atribuidos[atribuidos["labeler"] == "bob"]["video_id"])

    assert len(ids_alice) == 3
    assert len(ids_bob) == 3
    assert len(ids_alice.intersection(ids_bob)) == 2
    assert ids_alice.union(ids_bob) == set(videos["id"])


@pytest.mark.unit
def test_gerar_atribuicoes_cem_porcento_sobreposicao_atribui_todos_os_videos_a_cada_rotulador(
    caminhos_estudo,
) -> None:
    videos = carregar_videos(caminhos_estudo.arquivo_videos)
    config = {"rotuladores": ["alice", "bob"], "percentual_sobreposicao": 100.0}

    atribuidos = gerar_atribuicoes(config, videos, persistir=False)
    ids_alice = list(atribuidos[atribuidos["labeler"] == "alice"]["video_id"])
    ids_bob = list(atribuidos[atribuidos["labeler"] == "bob"]["video_id"])

    assert len(ids_alice) == 4
    assert ids_alice == ids_bob


@pytest.mark.unit
def test_gerar_atribuicoes_agrupa_fila_de_cada_rotulador_em_blocos_contiguos_de_target() -> None:
    videos = pd.DataFrame(
        [
            {"id": "1", "url": "https://tiktok.com/@a/video/1", "target": "Clima"},
            {"id": "2", "url": "https://tiktok.com/@a/video/2", "target": "Economia"},
            {"id": "3", "url": "https://tiktok.com/@a/video/3", "target": " Clima "},
            {"id": "4", "url": "https://tiktok.com/@a/video/4", "target": "Economia"},
        ]
    )
    config = {"rotuladores": ["alice"], "percentual_sobreposicao": 100.0}

    atribuidos = gerar_atribuicoes(config, videos, persistir=False)
    targets_normalizados = atribuidos["target"].astype(str).str.strip().tolist()

    assert targets_normalizados == ["Clima", "Clima", "Economia", "Economia"]


@pytest.mark.unit
def test_gerar_atribuicoes_equilibra_alocacao_por_target_entre_rotuladores(
    caminhos_estudo,
) -> None:
    videos = carregar_videos(caminhos_estudo.arquivo_videos)
    config = {"rotuladores": ["alice", "bob"], "percentual_sobreposicao": 0.0}

    atribuidos = gerar_atribuicoes(config, videos, persistir=False)
    targets_alice = sorted(
        atribuidos[atribuidos["labeler"] == "alice"]["target"]
        .astype(str)
        .str.strip()
        .tolist()
    )
    targets_bob = sorted(
        atribuidos[atribuidos["labeler"] == "bob"]["target"]
        .astype(str)
        .str.strip()
        .tolist()
    )

    assert targets_alice == ["Clima", "Economia"]
    assert targets_bob == ["Clima", "Economia"]


@pytest.mark.unit
def test_versao_atribuicao_e_deterministica_para_entradas_identicas(
    caminhos_estudo,
) -> None:
    videos = carregar_videos(caminhos_estudo.arquivo_videos)
    config = {"rotuladores": ["alice", "bob"], "percentual_sobreposicao": 50.0}

    primeira_versao = versao_atribuicao(config, videos)
    segunda_versao = versao_atribuicao(config, videos)

    assert primeira_versao == segunda_versao
    assert primeira_versao.startswith("v")
    assert len(primeira_versao) == 13


@pytest.mark.unit
def test_versao_atribuicao_muda_quando_sobreposicao_ou_rotuladores_mudam(
    caminhos_estudo,
) -> None:
    videos = carregar_videos(caminhos_estudo.arquivo_videos)
    config_base = {"rotuladores": ["alice", "bob"], "percentual_sobreposicao": 50.0}
    config_sobreposicao = {
        "rotuladores": ["alice", "bob"],
        "percentual_sobreposicao": 25.0,
    }
    config_rotuladores = {
        "rotuladores": ["alice", "carol"],
        "percentual_sobreposicao": 50.0,
    }

    versao_base = versao_atribuicao(config_base, videos)
    versao_sobreposicao = versao_atribuicao(config_sobreposicao, videos)
    versao_rotuladores = versao_atribuicao(config_rotuladores, videos)

    assert versao_base != versao_sobreposicao
    assert versao_base != versao_rotuladores


@pytest.mark.unit
def test_identificador_atribuicao_formata_versao_rotulador_e_id_video() -> None:
    identificador = identificador_atribuicao(
        "v123456789abc", "alice", "7100000000000000001"
    )

    assert identificador == "v123456789abc:alice:7100000000000000001"


@pytest.mark.unit
def test_vincular_ou_alocar_vaga_rotulador_substitui_vaga_disponivel(
    caminhos_estudo,
) -> None:
    videos = carregar_videos(caminhos_estudo.arquivo_videos)
    config = {"rotuladores": ["alice", "vaga_2"], "percentual_sobreposicao": 50.0}
    atribuicoes_iniciais = gerar_atribuicoes(config, videos, persistir=False)

    config_atualizada, atribuicoes_atualizadas, vaga_vinculada = (
        vincular_ou_alocar_vaga_rotulador(
            "bob",
            config,
            atribuicoes_iniciais,
            videos,
            usuarios_reivindicados={"alice"},
        )
    )

    assert vaga_vinculada == "vaga_2"
    assert config_atualizada["rotuladores"] == ["alice", "bob"]
    assert "vaga_2" not in set(atribuicoes_atualizadas["labeler"])
    assert (
        len(atribuicoes_atualizadas[atribuicoes_atualizadas["labeler"] == "bob"]) == 3
    )


@pytest.mark.unit
def test_vincular_ou_alocar_vaga_rotulador_aloca_fila_dinamica_quando_vagas_cheias(
    caminhos_estudo,
) -> None:
    videos = carregar_videos(caminhos_estudo.arquivo_videos)
    config = {
        "rotuladores": ["alice", "bob"],
        "percentual_sobreposicao": 50.0,
        "videos_por_rotulador": 3,
    }
    atribuicoes_iniciais = gerar_atribuicoes(config, videos, persistir=False)

    config_atualizada, atribuicoes_atualizadas, vaga_vinculada = (
        vincular_ou_alocar_vaga_rotulador(
            "professor_avaliacao",
            config,
            atribuicoes_iniciais,
            videos,
            usuarios_reivindicados={"alice", "bob"},
        )
    )

    assert vaga_vinculada == "professor_avaliacao"
    assert "professor_avaliacao" in config_atualizada["rotuladores"]
    assert (
        len(
            atribuicoes_atualizadas[
                atribuicoes_atualizadas["labeler"] == "professor_avaliacao"
            ]
        )
        == 3
    )
    assert (
        len(atribuicoes_atualizadas[atribuicoes_atualizadas["labeler"] == "alice"])
        == 3
    )
