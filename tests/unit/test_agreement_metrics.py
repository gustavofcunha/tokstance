"""Testes unitarios para distancias configuraveis entre rotulos, alfa de Krippendorff e alertas."""

import pandas as pd
import pytest

from tokstance.backend.domain.agreement import (
    calcular_concordancia,
    distancia_rotulos,
    encontrar_anotacoes_rapidas,
    filtrar_por_versao_atribuicao,
    tabela_atribuicoes_por_versao,
    versoes_atribuicao,
)
from tokstance.backend.domain.models import (
    DISTANCIAS_ROTULOS_PADRAO,
    gerar_combinacoes_rotulos,
)


@pytest.mark.unit
def test_distancia_rotulos_retorna_zero_para_rotulos_identicos() -> None:
    distancias_customizadas = {"Baixo|Médio": 1.5, "Baixo|Alto": 4.0, "Médio|Alto": 2.0}

    assert distancia_rotulos("Baixo", "Baixo", distancias_customizadas) == 0.0
    assert distancia_rotulos("Contra", "Contra", DISTANCIAS_ROTULOS_PADRAO) == 0.0


@pytest.mark.unit
def test_distancia_rotulos_e_simetrica_e_le_penalidades_configuradas() -> None:
    assert distancia_rotulos("Contra", "A Favor", DISTANCIAS_ROTULOS_PADRAO) == 3.0
    assert distancia_rotulos("A Favor", "Contra", DISTANCIAS_ROTULOS_PADRAO) == 3.0
    assert distancia_rotulos("Contra", "Neutro", DISTANCIAS_ROTULOS_PADRAO) == 1.0
    assert distancia_rotulos("Neutro", "A Favor", DISTANCIAS_ROTULOS_PADRAO) == 1.0
    assert (
        distancia_rotulos(
            "Vídeo não relacionado ao target", "Contra", DISTANCIAS_ROTULOS_PADRAO
        )
        == 2.0
    )
    assert (
        distancia_rotulos(
            "A Favor", "Vídeo não relacionado ao target", DISTANCIAS_ROTULOS_PADRAO
        )
        == 2.0
    )


@pytest.mark.unit
def test_gerar_combinacoes_rotulos_cria_todos_os_pares_para_opcoes_customizadas() -> None:
    opcoes_customizadas = ["Leve", "Moderado", "Grave"]
    penalidades_configuradas = {"Leve|Grave": 5.0, "Leve|Moderado": 1.5}

    pares = gerar_combinacoes_rotulos(
        opcoes_customizadas,
        distancias_existentes=penalidades_configuradas,
        penalidade_padrao=2.0,
    )

    pares_esperados = {
        "Leve|Moderado": 1.5,
        "Leve|Grave": 5.0,
        "Moderado|Grave": 2.0,
    }
    assert pares == pares_esperados


@pytest.mark.unit
def test_calcular_concordancia_retorna_alfa_nulo_sem_multiplas_anotacoes(
    caminhos_estudo,
) -> None:
    anotacoes_unicas = pd.DataFrame(
        [
            {"video_id": "101", "labeler": "alice", "stance": "Contra"},
            {"video_id": "102", "labeler": "bob", "stance": "A Favor"},
        ]
    )

    resumo = calcular_concordancia(anotacoes_unicas)

    assert resumo["alfa"] is None
    assert resumo["videos_com_multiplas_anotacoes"] == 0
    assert resumo["videos_com_discordancia"] == []


@pytest.mark.unit
def test_calcular_concordancia_retorna_alfa_unitario_em_consenso_perfeito_customizado() -> None:
    config_customizada = {
        "opcoes_posicao": ["Tóxico", "Não Tóxico", "Incerto"],
        "distancias_rotulos": {
            "Tóxico|Não Tóxico": 4.0,
            "Tóxico|Incerto": 1.5,
            "Não Tóxico|Incerto": 1.5,
        },
    }
    anotacoes_consenso = pd.DataFrame(
        [
            {"video_id": "101", "labeler": "alice", "stance": "Tóxico"},
            {"video_id": "101", "labeler": "bob", "stance": "Tóxico"},
            {"video_id": "102", "labeler": "alice", "stance": "Não Tóxico"},
            {"video_id": "102", "labeler": "bob", "stance": "Não Tóxico"},
        ]
    )

    resumo = calcular_concordancia(
        anotacoes_consenso, configuracao=config_customizada
    )

    assert resumo["alfa"] == 1.0
    assert resumo["videos_com_multiplas_anotacoes"] == 2
    assert resumo["anotacoes_consideradas"] == 4
    assert resumo["videos_com_discordancia"] == []


@pytest.mark.unit
def test_calcular_concordancia_usa_penalidades_configuradas_para_severidade_discordancia(
    caminhos_estudo,
) -> None:
    desvio_neutro = pd.DataFrame(
        [
            {"video_id": "101", "labeler": "alice", "stance": "Contra"},
            {"video_id": "101", "labeler": "bob", "stance": "Neutro"},
            {"video_id": "102", "labeler": "alice", "stance": "A Favor"},
            {"video_id": "102", "labeler": "bob", "stance": "A Favor"},
        ]
    )
    divergencia_polar = pd.DataFrame(
        [
            {"video_id": "101", "labeler": "alice", "stance": "Contra"},
            {"video_id": "101", "labeler": "bob", "stance": "A Favor"},
            {"video_id": "102", "labeler": "alice", "stance": "A Favor"},
            {"video_id": "102", "labeler": "bob", "stance": "A Favor"},
        ]
    )

    resumo_neutro = calcular_concordancia(desvio_neutro)
    resumo_polar = calcular_concordancia(divergencia_polar)

    assert resumo_neutro["videos_com_discordancia"][0]["discordancia_ordinal"] == 1.0
    assert resumo_polar["videos_com_discordancia"][0]["discordancia_ordinal"] == 3.0
    assert resumo_polar["alfa"] < resumo_neutro["alfa"]


@pytest.mark.unit
def test_calcular_concordancia_classifica_rotulador_divergente_no_topo_das_penalidades(
    caminhos_estudo,
) -> None:
    resultados = pd.DataFrame(
        [
            {"video_id": "101", "labeler": "alice", "stance": "Contra"},
            {"video_id": "101", "labeler": "bob", "stance": "Neutro"},
            {"video_id": "101", "labeler": "carol", "stance": "A Favor"},
            {"video_id": "102", "labeler": "bob", "stance": "Neutro"},
            {"video_id": "102", "labeler": "carol", "stance": "A Favor"},
        ]
    )

    resumo = calcular_concordancia(resultados)
    penalidades = resumo["rotuladores_com_maior_discordancia"]

    assert penalidades[0]["rotulador"] == "carol"
    assert penalidades[0]["penalidade"] == 3.0
    assert penalidades[-1]["rotulador"] == "bob"
    assert penalidades[-1]["penalidade"] == 2.0


@pytest.mark.unit
def test_encontrar_anotacoes_rapidas_sinaliza_envios_abaixo_da_duracao_menos_tolerancia() -> None:
    videos = pd.DataFrame(
        [
            {"id": "101", "video_duration": "25.0"},
            {"id": "102", "video_duration": "30.0"},
        ]
    )
    resultados = pd.DataFrame(
        [
            {
                "video_id": "101",
                "labeler": "alice",
                "tempo_analise_segundos": "12.0",
                "video_duration": "25.0",
            },
            {
                "video_id": "102",
                "labeler": "bob",
                "tempo_analise_segundos": "8.0",
                "video_duration": "30.0",
            },
        ]
    )

    alertas = encontrar_anotacoes_rapidas(
        resultados, videos, tolerancia_segundos=5.0
    )

    assert len(alertas) == 2
    assert alertas[0]["rotulador"] == "bob"
    assert alertas[0]["diferenca_segundos"] == 22.0
    assert alertas[1]["rotulador"] == "alice"
    assert alertas[1]["diferenca_segundos"] == 13.0


@pytest.mark.unit
def test_encontrar_anotacoes_rapidas_ignora_envios_dentro_da_tolerancia() -> None:
    videos = pd.DataFrame([{"id": "101", "video_duration": "25.0"}])
    resultados = pd.DataFrame(
        [
            {
                "video_id": "101",
                "labeler": "alice",
                "tempo_analise_segundos": "21.5",
                "video_duration": "25.0",
            }
        ]
    )

    alertas = encontrar_anotacoes_rapidas(
        resultados, videos, tolerancia_segundos=5.0
    )

    assert alertas == []


@pytest.mark.unit
def test_versoes_atribuicao_lista_versao_ativa_primeiro_e_exclui_prefixo_legado() -> None:
    atribuicoes = pd.DataFrame([{"assignment_version": "v_ativa_003"}])
    resultados = pd.DataFrame(
        [
            {"assignment_id": "v_antiga_001:alice:101"},
            {"assignment_id": "legacy:bob:102"},
        ]
    )
    erros = pd.DataFrame([{"assignment_id": "v_antiga_002:carol:103"}])

    versoes = versoes_atribuicao(atribuicoes, resultados, erros)

    assert versoes == ["v_ativa_003", "v_antiga_002", "v_antiga_001"]


@pytest.mark.unit
def test_filtrar_por_versao_atribuicao_e_tabela_reconstroem_rodada_historica() -> None:
    atribuicoes = pd.DataFrame(
        [
            {
                "assignment_version": "v_ativa_002",
                "assignment_id": "v_ativa_002:alice:101",
                "labeler": "alice",
                "video_id": "101",
            }
        ]
    )
    resultados = pd.DataFrame(
        [
            {"assignment_id": "v_antiga_001:alice:101", "labeler": "alice", "video_id": "101"},
            {"assignment_id": "v_ativa_002:alice:101", "labeler": "alice", "video_id": "101"},
        ]
    )
    erros = pd.DataFrame(
        [{"assignment_id": "v_antiga_001:bob:102", "labeler": "bob", "video_id": "102"}]
    )

    resultados_filtrados = filtrar_por_versao_atribuicao(resultados, "v_antiga_001")
    reconstruida = tabela_atribuicoes_por_versao(
        atribuicoes, resultados, erros, "v_antiga_001"
    )

    assert len(resultados_filtrados) == 1
    assert len(reconstruida) == 2
