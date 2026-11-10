"""Calculo configuravel de distancia par-a-par entre rotulos e alfa de Krippendorff ordinal."""

from typing import Any

import pandas as pd

from tokstance.backend.domain.models import carregar_configuracao
from tokstance.config import (
    TOLERANCIA_ANOTACAO_RAPIDA_SEGUNDOS,
    formatar_data_hora_brt,
)


def interpretar_mapa_distancias(
    mapa_distancias: dict[str, Any] | dict[frozenset[str], float] | None = None,
) -> dict[frozenset[str], float]:
    """Normaliza um dicionario de distancias par-a-par em chaves simetricas frozenset."""
    origem = mapa_distancias
    if origem is None:
        origem = carregar_configuracao().get("distancias_rotulos", {})
    tabela: dict[frozenset[str], float] = {}
    if not isinstance(origem, dict):
        return tabela

    for chave_bruta, peso_bruto in origem.items():
        try:
            peso = float(peso_bruto)
        except (TypeError, ValueError):
            continue
        if isinstance(chave_bruta, frozenset):
            if len(chave_bruta) == 2:
                tabela[frozenset(str(item).strip() for item in chave_bruta)] = peso
            continue
        partes = [parte.strip() for parte in str(chave_bruta).split("|", maxsplit=1)]
        if len(partes) == 2 and partes[0] and partes[1] and partes[0] != partes[1]:
            tabela[frozenset(partes)] = peso
    return tabela


def distancia_rotulos(
    esquerda: str,
    direita: str,
    mapa_distancias: dict[str, Any] | dict[frozenset[str], float] | None = None,
) -> float:
    """Retorna a distancia de penalidade configurada entre dois rotulos da tarefa."""
    esquerda_norm = str(esquerda).strip()
    direita_norm = str(direita).strip()
    if esquerda_norm == direita_norm:
        return 0.0
    tabela = interpretar_mapa_distancias(mapa_distancias)
    return tabela.get(frozenset((esquerda_norm, direita_norm)), 1.0)


def calcular_concordancia(
    resultados: pd.DataFrame,
    configuracao: dict[str, Any] | None = None,
    opcoes_permitidas: list[str] | tuple[str, ...] | None = None,
    mapa_distancias: dict[str, Any] | dict[frozenset[str], float] | None = None,
) -> dict[str, Any]:
    """Calcula a concordancia ponderada por distancia e as penalidades acumuladas por rotulador."""
    momento_atual = formatar_data_hora_brt()
    if resultados.empty or "stance" not in resultados.columns:
        return {
            "metrica": "Alfa de Krippendorff (ordinal)",
            "alfa": None,
            "videos_com_multiplas_anotacoes": 0,
            "anotacoes_consideradas": 0,
            "videos_com_discordancia": [],
            "rotuladores_com_maior_discordancia": [],
            "atualizado_em": momento_atual,
        }

    config_ativa = (
        configuracao
        if isinstance(configuracao, dict)
        else carregar_configuracao()
    )
    opcoes_efetivas = (
        list(opcoes_permitidas)
        if opcoes_permitidas is not None
        else list(config_ativa.get("opcoes_posicao", []))
    )
    distancias_efetivas = interpretar_mapa_distancias(
        mapa_distancias
        if mapa_distancias is not None
        else config_ativa.get("distancias_rotulos", {})
    )

    mascara_valida = resultados["stance"].astype(str).str.strip().ne("")
    if opcoes_efetivas:
        mascara_valida = mascara_valida & resultados["stance"].isin(opcoes_efetivas)
    rotulos_por_video = (
        resultados[mascara_valida].groupby("video_id")["stance"].apply(list)
    )
    utilizaveis = rotulos_por_video[rotulos_por_video.map(len) >= 2]

    if utilizaveis.empty:
        return {
            "metrica": "Alfa de Krippendorff (ordinal)",
            "alfa": None,
            "videos_com_multiplas_anotacoes": 0,
            "anotacoes_consideradas": 0,
            "videos_com_discordancia": [],
            "rotuladores_com_maior_discordancia": [],
            "atualizado_em": momento_atual,
        }

    #correcao estatistica para discordancia observada e esperada entre pares
    discordancia_observada = 0.0
    total_pares = 0
    videos_com_discordancia: list[dict[str, Any]] = []
    resultados_filtrados = resultados[mascara_valida]
    for id_video, rotulos in utilizaveis.items():
        distancias = [
            distancia_rotulos(
                rotulos[idx_esq], rotulos[idx_dir], distancias_efetivas
            )
            for idx_esq in range(len(rotulos))
            for idx_dir in range(idx_esq + 1, len(rotulos))
        ]
        discordancia_observada += sum(distancias)
        total_pares += len(distancias)
        if any(distancia > 0 for distancia in distancias):
            grupo_video = resultados_filtrados[
                resultados_filtrados["video_id"].astype(str) == str(id_video)
            ]
            anotacoes_por_rotulador: list[dict[str, str]] = []
            url_video = ""
            target_video = ""
            for linha in grupo_video.itertuples():
                rot_nome = str(getattr(linha, "labeler", "") or "").strip()
                pos_nome = str(getattr(linha, "stance", "") or "").strip()
                if not url_video:
                    url_video = str(getattr(linha, "url", "") or "").strip()
                if not target_video:
                    target_video = str(getattr(linha, "target", "") or "").strip()
                anotacoes_por_rotulador.append(
                    {"rotulador": rot_nome, "stance": pos_nome}
                )
            videos_com_discordancia.append(
                {
                    "video_id": str(id_video),
                    "url": url_video,
                    "target": target_video,
                    "anotacoes": rotulos,
                    "anotacoes_por_rotulador": anotacoes_por_rotulador,
                    "discordancia_ordinal": round(
                        sum(distancias) / len(distancias), 4
                    ),
                }
            )

    todos_rotulos = [rotulo for rotulos in utilizaveis for rotulo in rotulos]
    discordancia_esperada = sum(
        distancia_rotulos(
            todos_rotulos[idx_esq], todos_rotulos[idx_dir], distancias_efetivas
        )
        for idx_esq in range(len(todos_rotulos))
        for idx_dir in range(idx_esq + 1, len(todos_rotulos))
    )
    pares_esperados = len(todos_rotulos) * (len(todos_rotulos) - 1) / 2
    if total_pares == 0:
        alfa = None
    elif discordancia_esperada == 0:
        alfa = 1.0 if discordancia_observada == 0 else None
    else:
        alfa = 1.0 - (discordancia_observada / total_pares) / (
            discordancia_esperada / pares_esperados
        )

    videos_com_discordancia.sort(
        key=lambda item: item["discordancia_ordinal"], reverse=True
    )

    contagem_total_por_rotulador: dict[str, int] = {}
    if "labeler" in resultados_filtrados.columns:
        contagem_total_por_rotulador = (
            resultados_filtrados.groupby("labeler")["video_id"]
            .nunique()
            .astype(int)
            .to_dict()
        )

    discordancias_por_rotulador: dict[str, float] = {}
    videos_comparados_por_rotulador: dict[str, int] = {}
    videos_divergentes_por_rotulador: dict[str, int] = {}
    resultados_validos = resultados[resultados["video_id"].isin(utilizaveis.index)]
    for _, resultados_video in resultados_validos.groupby("video_id"):
        rotulos = resultados_video["stance"].tolist()
        for linha in resultados_video.itertuples():
            videos_comparados_por_rotulador[linha.labeler] = (
                videos_comparados_por_rotulador.get(linha.labeler, 0) + 1
            )
            outros_rotulos = [
                rotulo for rotulo in rotulos if rotulo != linha.stance
            ]
            if outros_rotulos:
                pontuacao = sum(
                    distancia_rotulos(linha.stance, rotulo, distancias_efetivas)
                    for rotulo in outros_rotulos
                ) / len(outros_rotulos)
                discordancias_por_rotulador[linha.labeler] = (
                    discordancias_por_rotulador.get(linha.labeler, 0.0) + pontuacao
                )
                videos_divergentes_por_rotulador[linha.labeler] = (
                    videos_divergentes_por_rotulador.get(linha.labeler, 0) + 1
                )

    ranking_rotuladores = [
        {
            "rotulador": rotulador,
            "labeler": rotulador,
            "quantidade_videos": int(
                contagem_total_por_rotulador.get(
                    rotulador, videos_comparados_por_rotulador.get(rotulador, 0)
                )
            ),
            "videos_comparados": int(
                videos_comparados_por_rotulador.get(rotulador, 0)
            ),
            "videos_divergentes": int(
                videos_divergentes_por_rotulador.get(rotulador, 0)
            ),
            "penalidade_media": round(
                pontuacao
                / max(1, videos_comparados_por_rotulador.get(rotulador, 1)),
                2,
            ),
            "penalidade": round(pontuacao, 2),
        }
        for rotulador, pontuacao in discordancias_por_rotulador.items()
    ]
    ranking_rotuladores.sort(key=lambda item: item["penalidade"], reverse=True)
    return {
        "metrica": "Concordância ponderada por distância",
        "alfa": round(alfa, 6) if alfa is not None else None,
        "videos_com_multiplas_anotacoes": int(len(utilizaveis)),
        "anotacoes_consideradas": int(len(todos_rotulos)),
        "videos_com_discordancia": videos_com_discordancia,
        "rotuladores_com_maior_discordancia": ranking_rotuladores,
        "atualizado_em": momento_atual,
    }


def encontrar_anotacoes_rapidas(
    resultados: pd.DataFrame,
    videos: pd.DataFrame,
    tolerancia_segundos: float = TOLERANCIA_ANOTACAO_RAPIDA_SEGUNDOS,
) -> list[dict[str, Any]]:
    """Detecta anotacoes concluidas mais rapido do que a duracao do video menos a tolerancia."""
    if resultados.empty or videos.empty:
        return []
    tolerancia = float(tolerancia_segundos)
    duracoes = videos.set_index(videos["id"].astype(str))["video_duration"].to_dict()
    alertas: list[dict[str, Any]] = []
    for linha in resultados.itertuples():
        duracao_bruta = getattr(linha, "video_duration", "") or duracoes.get(
            str(linha.video_id), ""
        )
        try:
            duracao = float(duracao_bruta)
            tempo_analise = float(linha.tempo_analise_segundos)
        except (TypeError, ValueError):
            continue
        if tempo_analise < duracao - tolerancia:
            alertas.append(
                {
                    "video_id": str(linha.video_id),
                    "rotulador": str(linha.labeler),
                    "video_duration": round(duracao, 2),
                    "tempo_analise_segundos": round(tempo_analise, 2),
                    "diferenca_segundos": round(duracao - tempo_analise, 2),
                }
            )
    return sorted(alertas, key=lambda item: item["diferenca_segundos"], reverse=True)


def versoes_atribuicao(
    atribuicoes: pd.DataFrame,
    resultados: pd.DataFrame,
    erros: pd.DataFrame,
) -> list[str]:
    """Lista a versao ativa de atribuicao seguida pelas versoes historicas em ordem reversa."""
    versoes: list[str] = []
    versao_atual: str | None = None
    if not atribuicoes.empty and "assignment_version" in atribuicoes.columns:
        versoes.extend(
            atribuicoes["assignment_version"].dropna().astype(str).tolist()
        )
        versao_atual = versoes[0] if versoes else None
    for quadro in (resultados, erros):
        if not quadro.empty and "assignment_id" in quadro.columns:
            versoes.extend(
                quadro["assignment_id"]
                .astype(str)
                .str.split(":", n=1)
                .str[0]
                .tolist()
            )
    disponiveis = {
        versao for versao in versoes if versao and versao != "legacy"
    }
    if versao_atual:
        disponiveis.discard(versao_atual)
    return ([versao_atual] if versao_atual else []) + sorted(
        disponiveis, reverse=True
    )


def filtrar_por_versao_atribuicao(
    quadro: pd.DataFrame,
    versao: str | None,
) -> pd.DataFrame:
    """Filtra linhas de resultados ou erros pertencentes ao prefixo de uma versao de atribuicao."""
    if quadro.empty or not versao or "assignment_id" not in quadro.columns:
        return quadro.copy()
    return quadro[
        quadro["assignment_id"].astype(str).str.startswith(f"{versao}:")
    ].copy()


def tabela_atribuicoes_por_versao(
    atribuicoes: pd.DataFrame,
    resultados: pd.DataFrame,
    erros: pd.DataFrame,
    versao: str | None,
) -> pd.DataFrame:
    """Retorna as atribuicoes ativas ou reconstroi as linhas historicas de uma versao anterior."""
    if (
        versao
        and not atribuicoes.empty
        and versao in set(atribuicoes["assignment_version"].astype(str))
    ):
        return atribuicoes[
            atribuicoes["assignment_version"].astype(str).eq(versao)
        ].copy()
    return pd.concat(
        [
            filtrar_por_versao_atribuicao(resultados, versao),
            filtrar_por_versao_atribuicao(erros, versao),
        ],
        ignore_index=True,
    )
