"""Motor deterministico de versionamento de atribuicoes e alocacao de filas."""

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from tokstance.backend.domain.models import COLUNAS_ATRIBUICAO
from tokstance.config import resolver_caminhos_dados


def _extrair_rotuladores(configuracao: dict[str, Any]) -> list[str]:
    brutos = configuracao.get("rotuladores", [])
    return [str(item).strip() for item in brutos if str(item).strip()]


def _extrair_percentual_sobreposicao(configuracao: dict[str, Any]) -> float:
    valor = configuracao.get("percentual_sobreposicao", 0.0)
    return max(0.0, min(100.0, float(valor or 0.0)))


def versao_atribuicao(configuracao: dict[str, Any], videos: pd.DataFrame) -> str:
    """Calcula um identificador deterministico SHA-256 de 12 caracteres para os videos e configuracao."""
    assinatura_videos = videos[["id", "url", "target"]].to_csv(
        index=False,
        lineterminator="\n",
    )
    assinatura_config = json.dumps(
        {
            "rotuladores": _extrair_rotuladores(configuracao),
            "percentual_sobreposicao": _extrair_percentual_sobreposicao(configuracao),
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    resumo = hashlib.sha256(
        f"{assinatura_videos}\n{assinatura_config}".encode("utf-8")
    ).hexdigest()
    return f"v{resumo[:12]}"


def identificador_atribuicao(versao: str, rotulador: str, id_video: str) -> str:
    """Constroi o identificador unico canonico de uma atribuicao entre rotulador e video."""
    return f"{versao}:{rotulador}:{id_video}"


def persistir_dataframe_se_alterado(
    quadro: pd.DataFrame,
    caminho_arquivo: Path,
    colunas: list[str] | tuple[str, ...],
) -> None:
    """Grava um DataFrame em CSV somente quando o conteudo serializado difere do disco."""
    caminho_alvo = Path(caminho_arquivo)
    caminho_alvo.parent.mkdir(parents=True, exist_ok=True)
    conteudo = quadro.reindex(columns=list(colunas)).to_csv(index=False)
    if caminho_alvo.exists() and caminho_alvo.read_text(encoding="utf-8") == conteudo:
        return
    caminho_alvo.write_text(conteudo, encoding="utf-8")


def gerar_atribuicoes(
    configuracao: dict[str, Any],
    videos: pd.DataFrame,
    persistir: bool = True,
    arquivo_atribuicoes: Path | None = None,
) -> pd.DataFrame:
    """Gera filas de anotacao balanceadas por target e agrupadas em blocos contiguos."""
    rotuladores = _extrair_rotuladores(configuracao)
    percentual_sobreposicao = _extrair_percentual_sobreposicao(configuracao)
    versao = versao_atribuicao(configuracao, videos)
    colunas = list(COLUNAS_ATRIBUICAO)

    if not rotuladores or len(videos) == 0:
        return pd.DataFrame(columns=colunas)

    #intercala videos entre targets normalizados antes de separar a sobreposicao
    baldes_target: dict[str, list[int]] = {}
    ordem_targets: list[str] = []
    for indice_video, target_bruto in enumerate(videos["target"].astype(str).tolist()):
        chave_target = target_bruto.strip()
        if chave_target not in baldes_target:
            baldes_target[chave_target] = []
            ordem_targets.append(chave_target)
        baldes_target[chave_target].append(indice_video)

    ordem_balanceada: list[int] = []
    while any(baldes_target[chave_target] for chave_target in ordem_targets):
        for chave_target in ordem_targets:
            if baldes_target[chave_target]:
                ordem_balanceada.append(baldes_target[chave_target].pop(0))

    quantidade_sobreposicao = int((percentual_sobreposicao / 100.0) * len(videos))
    indices_sobreposicao = ordem_balanceada[:quantidade_sobreposicao]
    indices_individuais = ordem_balanceada[quantidade_sobreposicao:]

    contagem_por_target = {
        rotulador: {chave_target: 0 for chave_target in ordem_targets}
        for rotulador in rotuladores
    }
    totais_rotulador = {rotulador: 0 for rotulador in rotuladores}
    atribuicoes_individuais: dict[int, str] = {}

    for indice_video in indices_individuais:
        chave_target = str(videos.iloc[indice_video]["target"]).strip()
        rotulador_escolhido = min(
            rotuladores,
            key=lambda candidato: (
                contagem_por_target[candidato][chave_target],
                totais_rotulador[candidato],
                rotuladores.index(candidato),
            ),
        )
        atribuicoes_individuais[indice_video] = rotulador_escolhido
        contagem_por_target[rotulador_escolhido][chave_target] += 1
        totais_rotulador[rotulador_escolhido] += 1

    pares_brutos: list[tuple[str, int]] = []
    for indice_video in indices_sobreposicao:
        for rotulador in rotuladores:
            pares_brutos.append((rotulador, indice_video))
    pares_brutos.extend(
        (rotulador, indice_video)
        for indice_video, rotulador in atribuicoes_individuais.items()
    )

    #agrupa a fila de cada rotulador em blocos contiguos de target
    classificacao_target = {
        chave_target: posicao for posicao, chave_target in enumerate(ordem_targets)
    }
    pares_brutos.sort(
        key=lambda item: (
            rotuladores.index(item[0]),
            classificacao_target[str(videos.iloc[item[1]]["target"]).strip()],
            item[1],
        )
    )

    linhas = [
        {
            "assignment_version": versao,
            "assignment_id": identificador_atribuicao(
                versao, rotulador, str(videos.iloc[indice_video]["id"])
            ),
            "labeler": rotulador,
            "video_id": str(videos.iloc[indice_video]["id"]),
            "url": videos.iloc[indice_video]["url"],
            "target": videos.iloc[indice_video]["target"],
            "video_description": videos.iloc[indice_video].get("video_description", ""),
            "voice_to_text": videos.iloc[indice_video].get("voice_to_text", ""),
            "video_duration": videos.iloc[indice_video].get("video_duration", ""),
        }
        for rotulador, indice_video in pares_brutos
    ]
    resultado = pd.DataFrame(linhas, columns=colunas)
    resultado = resultado.drop_duplicates(
        subset=["labeler", "video_id"], keep="last"
    ).reset_index(drop=True)
    if persistir:
        arquivo_alvo = (
            Path(arquivo_atribuicoes)
            if arquivo_atribuicoes is not None
            else resolver_caminhos_dados().arquivo_atribuicoes
        )
        persistir_dataframe_se_alterado(resultado, arquivo_alvo, colunas)
    return resultado


def construir_fila_avaliacao_rotulador(
    nome_usuario: str,
    versao: str,
    videos: pd.DataFrame,
    maximo_videos: int | None = None,
) -> pd.DataFrame:
    """Cria uma fila balanceada por target e agrupada em blocos para um novo rotulador."""
    colunas = list(COLUNAS_ATRIBUICAO)
    if videos.empty or not str(nome_usuario).strip():
        return pd.DataFrame(columns=colunas)

    baldes_target: dict[str, list[int]] = {}
    ordem_targets: list[str] = []
    for indice_video, target_bruto in enumerate(videos["target"].astype(str).tolist()):
        chave_target = target_bruto.strip()
        if chave_target not in baldes_target:
            baldes_target[chave_target] = []
            ordem_targets.append(chave_target)
        baldes_target[chave_target].append(indice_video)

    indices_intercalados: list[int] = []
    while any(baldes_target[chave_target] for chave_target in ordem_targets):
        for chave_target in ordem_targets:
            if baldes_target[chave_target]:
                indices_intercalados.append(baldes_target[chave_target].pop(0))

    limite = len(indices_intercalados)
    if maximo_videos is not None and int(maximo_videos) > 0:
        limite = min(limite, int(maximo_videos))
    indices_selecionados = indices_intercalados[:limite]

    classificacao_target = {
        chave_target: posicao for posicao, chave_target in enumerate(ordem_targets)
    }
    indices_selecionados.sort(
        key=lambda idx: (
            classificacao_target[str(videos.iloc[idx]["target"]).strip()],
            idx,
        )
    )

    linhas = [
        {
            "assignment_version": versao,
            "assignment_id": identificador_atribuicao(
                versao, nome_usuario, str(videos.iloc[idx]["id"])
            ),
            "labeler": nome_usuario,
            "video_id": str(videos.iloc[idx]["id"]),
            "url": videos.iloc[idx]["url"],
            "target": videos.iloc[idx]["target"],
            "video_description": videos.iloc[idx].get("video_description", ""),
            "voice_to_text": videos.iloc[idx].get("voice_to_text", ""),
            "video_duration": videos.iloc[idx].get("video_duration", ""),
        }
        for idx in indices_selecionados
    ]
    return pd.DataFrame(linhas, columns=colunas)


def vincular_ou_alocar_vaga_rotulador(
    nome_usuario: str,
    configuracao: dict[str, Any],
    atribuicoes: pd.DataFrame,
    videos: pd.DataFrame,
    usuarios_reivindicados: set[str] | None = None,
    rotuladores_concluidos: set[str] | None = None,
) -> tuple[dict[str, Any], pd.DataFrame, str]:
    """Vincula um novo rotulador a uma vaga disponivel ou aloca uma fila dinamica na rodada ativa."""
    usuario_normalizado = str(nome_usuario).strip()
    config_atualizada = dict(configuracao)
    rotuladores = _extrair_rotuladores(config_atualizada)
    reivindicados = set(usuarios_reivindicados or set())
    anotados = set(rotuladores_concluidos or set())
    colunas = list(COLUNAS_ATRIBUICAO)

    if atribuicoes.empty:
        if usuario_normalizado not in rotuladores:
            rotuladores.append(usuario_normalizado)
            config_atualizada["rotuladores"] = rotuladores
        geradas = gerar_atribuicoes(config_atualizada, videos, persistir=False)
        return config_atualizada, geradas, usuario_normalizado

    versao_ativa = str(atribuicoes["assignment_version"].iloc[-1])

    #reaproveita a fila existente caso o rotulador ja esteja presente nas atribuicoes
    if usuario_normalizado in set(atribuicoes["labeler"].astype(str)):
        if usuario_normalizado not in rotuladores:
            rotuladores.append(usuario_normalizado)
            config_atualizada["rotuladores"] = rotuladores
        return config_atualizada, atribuicoes.reindex(columns=colunas), usuario_normalizado

    #vincula a primeira vaga configurada ainda nao reivindicada e sem anotacoes
    vaga_disponivel = None
    for candidato in rotuladores:
        if candidato not in reivindicados and candidato not in anotados:
            if candidato.startswith(("vaga_", "rotulador_")):
                vaga_disponivel = candidato
                break

    if vaga_disponivel is not None:
        novos_rotuladores = [
            usuario_normalizado if item == vaga_disponivel else item
            for item in rotuladores
        ]
        config_atualizada["rotuladores"] = novos_rotuladores
        atribuicoes_atualizadas = atribuicoes.copy()
        mascara_vaga = atribuicoes_atualizadas["labeler"].astype(str).eq(vaga_disponivel)
        atribuicoes_atualizadas.loc[mascara_vaga, "labeler"] = usuario_normalizado
        atribuicoes_atualizadas.loc[mascara_vaga, "assignment_id"] = (
            atribuicoes_atualizadas.loc[mascara_vaga].apply(
                lambda linha: identificador_atribuicao(
                    str(linha["assignment_version"]),
                    usuario_normalizado,
                    str(linha["video_id"]),
                ),
                axis=1,
            )
        )
        return (
            config_atualizada,
            atribuicoes_atualizadas.reindex(columns=colunas),
            vaga_disponivel,
        )

    #aloca uma fila de avaliacao extra quando todas as vagas iniciais ja estao ocupadas
    if usuario_normalizado not in rotuladores:
        rotuladores.append(usuario_normalizado)
        config_atualizada["rotuladores"] = rotuladores

    maximo_videos = int(
        config_atualizada.get("videos_por_rotulador", len(videos)) or len(videos)
    )
    fila_extra = construir_fila_avaliacao_rotulador(
        usuario_normalizado,
        versao_ativa,
        videos,
        maximo_videos=maximo_videos,
    )
    combinadas = pd.concat([atribuicoes, fila_extra], ignore_index=True)
    combinadas = combinadas.drop_duplicates(
        subset=["assignment_version", "labeler", "video_id"], keep="last"
    ).reset_index(drop=True)
    return config_atualizada, combinadas.reindex(columns=colunas), usuario_normalizado
