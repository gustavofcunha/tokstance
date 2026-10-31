"""Maquina de estados de substituicao por videos reserva e rebalanceamento de sobreposicao."""

import csv
from pathlib import Path

import pandas as pd

from tokstance.backend.domain.assignments import (
    gerar_atribuicoes,
    identificador_atribuicao,
    persistir_dataframe_se_alterado,
)
from tokstance.backend.domain.models import (
    COLUNAS_ERRO,
    COLUNAS_RESULTADO,
    carregar_videos,
    carregar_videos_reserva,
)
from tokstance.config import resolver_caminhos_dados


def ler_resultados(arquivo_resultados: Path | None = None) -> pd.DataFrame:
    """Carrega e normaliza as anotacoes concluidas a partir de resultados_anotacao.csv."""
    colunas = list(COLUNAS_RESULTADO)
    caminho_alvo = (
        Path(arquivo_resultados)
        if arquivo_resultados is not None
        else resolver_caminhos_dados().arquivo_resultados
    )
    if not caminho_alvo.exists() or caminho_alvo.stat().st_size == 0:
        return pd.DataFrame(columns=colunas)

    try:
        df = pd.read_csv(caminho_alvo, dtype=str)
        if df.empty:
            return pd.DataFrame(columns=colunas)
        if set(colunas).issubset(set(df.columns)):
            df = df[colunas].fillna("")
            ids_ausentes = df["assignment_id"].astype(str).str.strip().eq("")
            df.loc[ids_ausentes, "assignment_id"] = df.loc[ids_ausentes].apply(
                lambda linha: f"legacy:{linha['labeler']}:{linha['video_id']}",
                axis=1,
            )
            return df.drop_duplicates(subset=["assignment_id"], keep="last")
        if set(colunas[:-2]).issubset(set(df.columns)):
            df["video_duration"] = ""
            df["assignment_id"] = df.apply(
                lambda linha: f"legacy:{linha['labeler']}:{linha['video_id']}",
                axis=1,
            )
            return df[colunas].fillna("").drop_duplicates(
                subset=["assignment_id"], keep="last"
            )
    except (pd.errors.EmptyDataError, pd.errors.ParserError):
        pass

    try:
        df = pd.read_csv(caminho_alvo, header=None, dtype=str)
        if df.empty:
            return pd.DataFrame(columns=colunas)
        if df.shape[1] >= len(colunas) - 2:
            corrigido = df.iloc[:, : len(colunas) - 2].copy()
            corrigido["video_duration"] = ""
            corrigido["assignment_id"] = corrigido.apply(
                lambda linha: f"legacy:{linha['labeler']}:{linha['video_id']}",
                axis=1,
            )
            corrigido.columns = colunas
            return corrigido.fillna("").drop_duplicates(
                subset=["assignment_id"], keep="last"
            )
    except (pd.errors.EmptyDataError, pd.errors.ParserError):
        pass

    return pd.DataFrame(columns=colunas)


def ler_erros_atribuicoes(arquivo_erros: Path | None = None) -> pd.DataFrame:
    """Carrega e normaliza os registros de erro de video em erros_videos.csv."""
    colunas = list(COLUNAS_ERRO)
    caminho_alvo = (
        Path(arquivo_erros)
        if arquivo_erros is not None
        else resolver_caminhos_dados().arquivo_erros
    )
    if not caminho_alvo.exists() or caminho_alvo.stat().st_size == 0:
        return pd.DataFrame(columns=colunas)

    with caminho_alvo.open(encoding="utf-8", newline="") as handle:
        linhas = list(csv.reader(handle))
    if not linhas:
        return pd.DataFrame(columns=colunas)

    if linhas[0][:4] == colunas[:4]:
        colunas_no_arquivo = linhas.pop(0)
    else:
        colunas_no_arquivo = colunas[:5]

    normalizadas = []
    for linha in linhas:
        if len(linha) < 4:
            continue
        timestamp, video_id, url, rotulador = linha[:4]
        assignment_id = (
            linha[4].strip()
            if len(linha) >= 5 and linha[4].strip()
            else f"legacy:{rotulador}:{video_id}"
        )
        valores = dict(zip(colunas_no_arquivo, linha))
        valores["assignment_id"] = assignment_id
        normalizadas.append({coluna: valores.get(coluna, "") for coluna in colunas})
    return pd.DataFrame(normalizadas, columns=colunas)


def calcular_reservas_disponiveis(
    videos_reserva: pd.DataFrame,
    atribuicoes: pd.DataFrame,
    erros: pd.DataFrame,
) -> pd.DataFrame:
    """Filtra os videos reserva que ainda nao foram atribuidos nem consumidos por erros."""
    reservas_unicas = videos_reserva.drop_duplicates(subset=["id"], keep="first")
    ids_reserva = set(reservas_unicas["id"].astype(str))
    ids_usados = set(
        atribuicoes[atribuicoes["video_id"].astype(str).isin(ids_reserva)][
            "video_id"
        ].astype(str)
    )
    ids_usados.update(
        erros[erros["video_id"].astype(str).isin(ids_reserva)]["video_id"].astype(str)
    )
    return reservas_unicas[~reservas_unicas["id"].astype(str).isin(ids_usados)]


def aplicar_substituicoes_reserva(
    atribuicoes: pd.DataFrame,
    diretorio_dados: Path | None = None,
) -> pd.DataFrame:
    """Substitui videos reportados com erro por videos reserva compativeis."""
    caminhos = resolver_caminhos_dados(diretorio_dados)
    if atribuicoes.empty or not caminhos.arquivo_erros.exists():
        return atribuicoes

    erros = ler_erros_atribuicoes(caminhos.arquivo_erros)
    videos_reserva = carregar_videos_reserva(
        caminhos.arquivo_videos_reserva
    ).drop_duplicates(subset=["id"], keep="first")
    if erros.empty:
        return atribuicoes
    if videos_reserva.empty:
        erros_pendentes = (
            erros["replacement_assignment_id"].astype(str).str.strip().eq("")
        )
        erros.loc[erros_pendentes, "replacement_status"] = "SEM_RESERVA_DISPONIVEL"
        persistir_dataframe_se_alterado(
            erros, caminhos.arquivo_erros, list(erros.columns)
        )
        return atribuicoes

    reservas_disponiveis = calcular_reservas_disponiveis(
        videos_reserva, atribuicoes, erros
    )
    resultados = ler_resultados(caminhos.arquivo_resultados)
    ids_atribuicao_concluidos = set(
        resultados.get("assignment_id", pd.Series(dtype=str)).astype(str).str.strip()
    )
    atribuicoes_alteradas = False
    erros_alterados = False

    for indice_erro, erro in erros.iterrows():
        if str(erro.get("replacement_assignment_id", "")).strip():
            continue
        assignment_id = str(erro.get("assignment_id", "")).strip()
        id_video_original = str(erro.get("video_id", "")).strip()
        substituicao_anterior = erros[
            erros["video_id"].astype(str).eq(id_video_original)
            & erros["replacement_assignment_id"].astype(str).ne("")
        ]
        id_reserva_existente = ""
        status_anterior = ""
        if not substituicao_anterior.empty:
            id_video_original = str(substituicao_anterior.iloc[0]["video_id"]).strip()
            id_reserva_existente = str(
                substituicao_anterior.iloc[0]["replacement_video_id"]
            ).strip()
            status_anterior = str(
                substituicao_anterior.iloc[0]["replacement_status"]
            ).strip()

        linhas_correspondentes = atribuicoes.index[
            atribuicoes["assignment_id"].astype(str).eq(assignment_id)
        ]
        if linhas_correspondentes.empty:
            linhas_correspondentes = atribuicoes.index[
                atribuicoes["labeler"].astype(str).eq(str(erro.get("labeler", "")))
                & atribuicoes["video_id"].astype(str).eq(str(erro.get("video_id", "")))
            ]
        if linhas_correspondentes.empty and id_reserva_existente:
            linhas_correspondentes = atribuicoes.index[
                atribuicoes["labeler"].astype(str).eq(str(erro.get("labeler", "")))
                & atribuicoes["video_id"].astype(str).eq(id_reserva_existente)
            ]
        if linhas_correspondentes.empty:
            continue

        indice_origem = linhas_correspondentes[0]
        if status_anterior == "SUBSTITUIDO_OVERLAP_REBALANCEADO":
            erros.at[indice_erro, "replacement_video_id"] = id_reserva_existente
            erros.at[indice_erro, "replacement_url"] = str(
                atribuicoes.at[indice_origem, "url"]
            )
            erros.at[indice_erro, "replacement_assignment_id"] = str(
                atribuicoes.at[indice_origem, "assignment_id"]
            )
            erros.at[indice_erro, "replacement_status"] = status_anterior
            erros_alterados = True
            continue

        #resolve todas as linhas de atribuicao pertencentes ao mesmo grupo de sobreposicao
        linhas_grupo = atribuicoes.index[
            atribuicoes["video_id"].astype(str).eq(id_video_original)
        ]
        linhas_substituidas = (
            erros[
                erros["video_id"].astype(str).eq(id_video_original)
                & erros["replacement_assignment_id"].astype(str).ne("")
            ]["replacement_assignment_id"]
            .astype(str)
            .tolist()
        )
        if linhas_substituidas:
            linhas_grupo = linhas_grupo.union(
                atribuicoes.index[
                    atribuicoes["assignment_id"].astype(str).isin(linhas_substituidas)
                ]
            )
        if id_reserva_existente:
            linhas_grupo = linhas_grupo.union(
                atribuicoes.index[
                    atribuicoes["video_id"].astype(str).eq(id_reserva_existente)
                ]
            )
        linhas_grupo = linhas_grupo.sort_values()
        grupo_possui_concluido = any(
            str(atribuicoes.at[indice, "assignment_id"]).strip()
            in ids_atribuicao_concluidos
            for indice in linhas_grupo
        )
        target_origem = str(atribuicoes.at[indice_origem, "target"]).strip()
        if linhas_grupo.empty:
            linhas_grupo = linhas_correspondentes

        reservas_compativeis = videos_reserva[
            videos_reserva["target"].astype(str).str.strip().eq(target_origem)
        ]
        if id_reserva_existente:
            reservas_compativeis = reservas_compativeis[
                reservas_compativeis["id"].astype(str).eq(id_reserva_existente)
            ]
        else:
            reservas_compativeis = reservas_compativeis[
                reservas_compativeis["id"]
                .astype(str)
                .isin(reservas_disponiveis["id"].astype(str))
            ]

        #promove um video individual ja anotado quando o grupo de sobreposicao possui progresso parcial
        if grupo_possui_concluido and not id_reserva_existente:
            contagem_videos = atribuicoes.groupby(
                atribuicoes["video_id"].astype(str)
            )["assignment_id"].transform("size")
            ids_videos_concluidos = atribuicoes.loc[
                atribuicoes["assignment_id"].astype(str).isin(ids_atribuicao_concluidos),
                "video_id",
            ].astype(str)
            linhas_candidatas = atribuicoes.index[
                contagem_videos.eq(1)
                & atribuicoes["video_id"].astype(str).ne(id_video_original)
                & atribuicoes["video_id"].astype(str).isin(ids_videos_concluidos)
                & atribuicoes["target"].astype(str).str.strip().eq(target_origem)
                & atribuicoes["labeler"].astype(str).ne(str(erro.get("labeler", "")))
            ]
            if not linhas_candidatas.empty:
                indice_candidato = linhas_candidatas[0]
                id_video_candidato = str(
                    atribuicoes.at[indice_candidato, "video_id"]
                )
                candidato = atribuicoes.loc[indice_candidato].copy()
                rotulador_origem = str(atribuicoes.at[indice_origem, "labeler"])
                versao_origem = str(
                    atribuicoes.at[indice_origem, "assignment_version"]
                )
                id_substituicao_origem = identificador_atribuicao(
                    versao_origem, rotulador_origem, id_video_candidato
                )
                linhas_para_promover = [
                    indice
                    for indice in linhas_grupo
                    if str(atribuicoes.at[indice, "assignment_id"]).strip()
                    not in ids_atribuicao_concluidos
                ]
                if indice_origem not in linhas_para_promover:
                    linhas_para_promover.append(indice_origem)
                for indice_promocao in linhas_para_promover:
                    rotulador_promocao = str(
                        atribuicoes.at[indice_promocao, "labeler"]
                    )
                    versao_promocao = str(
                        atribuicoes.at[indice_promocao, "assignment_version"]
                    )
                    atribuicoes.at[indice_promocao, "video_id"] = id_video_candidato
                    for coluna in (
                        "url",
                        "target",
                        "video_description",
                        "voice_to_text",
                        "video_duration",
                    ):
                        atribuicoes.at[indice_promocao, coluna] = candidato[coluna]
                    atribuicoes.at[indice_promocao, "assignment_id"] = (
                        identificador_atribuicao(
                            versao_promocao, rotulador_promocao, id_video_candidato
                        )
                    )
                erros.at[indice_erro, "replacement_video_id"] = id_video_candidato
                erros.at[indice_erro, "replacement_url"] = str(candidato["url"])
                erros.at[indice_erro, "replacement_assignment_id"] = (
                    id_substituicao_origem
                )
                erros.at[indice_erro, "replacement_status"] = (
                    "SUBSTITUIDO_OVERLAP_REBALANCEADO"
                )
                atribuicoes_alteradas = True
                erros_alterados = True
                continue

        if reservas_compativeis.empty:
            if grupo_possui_concluido:
                erros.at[indice_erro, "replacement_status"] = (
                    "CRITICO_OVERLAP_INCONSISTENTE"
                )
            else:
                erros.at[indice_erro, "replacement_status"] = (
                    "SEM_RESERVA_DISPONIVEL"
                    if reservas_disponiveis.empty
                    else "SEM_RESERVA_COMPATIVEL"
                )
            erros_alterados = True
            continue

        reserva = reservas_compativeis.iloc[0]
        id_reserva = str(reserva["id"])
        linhas_para_substituir = (
            linhas_correspondentes if grupo_possui_concluido else linhas_grupo
        )
        for indice_substituicao in linhas_para_substituir:
            rotulador = str(atribuicoes.at[indice_substituicao, "labeler"])
            versao = str(atribuicoes.at[indice_substituicao, "assignment_version"])
            id_atribuicao_substituta = identificador_atribuicao(
                versao, rotulador, id_reserva
            )
            if (
                str(atribuicoes.at[indice_substituicao, "assignment_id"]).strip()
                in ids_atribuicao_concluidos
            ):
                continue
            atribuicoes.at[indice_substituicao, "video_id"] = id_reserva
            for coluna in (
                "url",
                "target",
                "video_description",
                "voice_to_text",
                "video_duration",
            ):
                atribuicoes.at[indice_substituicao, coluna] = reserva.get(coluna, "")
            atribuicoes.at[indice_substituicao, "assignment_id"] = (
                id_atribuicao_substituta
            )
            atribuicoes_alteradas = True

        rotulador = str(atribuicoes.at[indice_origem, "labeler"])
        versao = str(atribuicoes.at[indice_origem, "assignment_version"])
        id_atribuicao_substituta = identificador_atribuicao(
            versao, rotulador, id_reserva
        )
        erros.at[indice_erro, "replacement_video_id"] = id_reserva
        erros.at[indice_erro, "replacement_url"] = str(reserva["url"])
        erros.at[indice_erro, "replacement_assignment_id"] = id_atribuicao_substituta
        erros.at[indice_erro, "replacement_status"] = (
            "CRITICO_OVERLAP_INCONSISTENTE"
            if grupo_possui_concluido
            else "SUBSTITUIDO_OVERLAP"
        )
        if not grupo_possui_concluido and not id_reserva_existente:
            reservas_disponiveis = reservas_disponiveis[
                reservas_disponiveis["id"].astype(str).ne(id_reserva)
            ]
        erros_alterados = True

    if atribuicoes_alteradas:
        persistir_dataframe_se_alterado(
            atribuicoes, caminhos.arquivo_atribuicoes, list(atribuicoes.columns)
        )
    if erros_alterados:
        persistir_dataframe_se_alterado(
            erros, caminhos.arquivo_erros, list(erros.columns)
        )
    return atribuicoes


def carregar_atribuicoes(
    configuracao: dict,
    videos: pd.DataFrame,
    diretorio_dados: Path | None = None,
) -> pd.DataFrame:
    """Carrega as atribuicoes persistidas da versao ativa e aplica substituicoes por reserva."""
    caminhos = resolver_caminhos_dados(diretorio_dados)
    atribuicoes_base = gerar_atribuicoes(
        configuracao,
        videos,
        persistir=False,
        arquivo_atribuicoes=caminhos.arquivo_atribuicoes,
    )
    atribuicoes = atribuicoes_base
    if caminhos.arquivo_atribuicoes.exists() and not atribuicoes_base.empty:
        try:
            persistidas = pd.read_csv(caminhos.arquivo_atribuicoes, dtype=str).fillna("")
            possui_esquema = set(atribuicoes_base.columns).issubset(persistidas.columns)
            mesma_versao = set(persistidas.get("assignment_version", [])) == {
                atribuicoes_base.iloc[0]["assignment_version"]
            }
            if (
                possui_esquema
                and mesma_versao
                and len(persistidas) >= len(atribuicoes_base)
            ):
                atribuicoes = persistidas[atribuicoes_base.columns].copy()
        except (pd.errors.EmptyDataError, pd.errors.ParserError):
            pass

    if not atribuicoes.empty and not atribuicoes.equals(atribuicoes_base):
        persistir_dataframe_se_alterado(
            atribuicoes,
            caminhos.arquivo_atribuicoes,
            list(atribuicoes_base.columns),
        )
    elif not caminhos.arquivo_atribuicoes.exists():
        persistir_dataframe_se_alterado(
            atribuicoes_base,
            caminhos.arquivo_atribuicoes,
            list(atribuicoes_base.columns),
        )
    return aplicar_substituicoes_reserva(
        atribuicoes, diretorio_dados=caminhos.diretorio_base
    )


def garantir_esquema_erros(diretorio_dados: Path | None = None) -> None:
    """Normaliza erros_videos.csv em disco para o esquema canonico."""
    caminhos = resolver_caminhos_dados(diretorio_dados)
    if not caminhos.arquivo_erros.exists() or caminhos.arquivo_erros.stat().st_size == 0:
        return
    erros = ler_erros_atribuicoes(caminhos.arquivo_erros)
    persistir_dataframe_se_alterado(erros, caminhos.arquivo_erros, list(erros.columns))


def garantir_esquema_resultados(diretorio_dados: Path | None = None) -> None:
    """Normaliza resultados_anotacao.csv em disco e preenche duracoes ou IDs ausentes."""
    caminhos = resolver_caminhos_dados(diretorio_dados)
    colunas = list(COLUNAS_RESULTADO)
    if (
        not caminhos.arquivo_resultados.exists()
        or caminhos.arquivo_resultados.stat().st_size == 0
    ):
        return
    try:
        df = pd.read_csv(caminhos.arquivo_resultados, dtype=str).fillna("")
    except (pd.errors.EmptyDataError, pd.errors.ParserError):
        return
    videos = carregar_videos(caminhos.arquivo_videos).set_index("id")
    if "video_duration" not in df.columns:
        df["video_duration"] = ""
    if "assignment_id" not in df.columns:
        df["assignment_id"] = df.apply(
            lambda linha: f"legacy:{linha['labeler']}:{linha['video_id']}",
            axis=1,
        )
    for indice, linha in df.iterrows():
        if not str(linha.get("video_duration", "")).strip():
            chave_video = str(linha.get("video_id", ""))
            if chave_video in videos.index:
                df.at[indice, "video_duration"] = str(
                    videos.loc[chave_video, "video_duration"]
                )
    df = df.reindex(columns=[coluna for coluna in colunas if coluna in df.columns])
    df.to_csv(caminhos.arquivo_resultados, index=False)
