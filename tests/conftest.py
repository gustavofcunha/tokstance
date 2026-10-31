"""Fixtures compartilhadas de pytest para diretorios isolados, dados sinteticos e relogios."""

from datetime import datetime, timedelta
import json
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from tokstance.config import CaminhosDados, FUSO_BRT, resolver_caminhos_dados


class RelogioDeterministico:
    """Relogio controlavel ancorado no fuso de Brasilia para execucao deterministica de testes."""

    def __init__(self, momento_inicial: datetime | None = None) -> None:
        self._atual = momento_inicial or datetime(
            2026, 10, 31, 12, 0, 0, tzinfo=FUSO_BRT
        )
        self._monotonico = 1000.0

    def agora(self) -> datetime:
        """Retorna o datetime simulado atual em horario de Brasilia."""
        return self._atual

    def monotonico(self) -> float:
        """Retorna o timestamp monotonico simulado atual em segundos."""
        return self._monotonico

    def avancar(self, segundos: float) -> None:
        """Avanca o relogio de parede e o monotonico pelo numero de segundos informado."""
        self._atual = self._atual + timedelta(seconds=float(segundos))
        self._monotonico += float(segundos)


VIDEOS_SINTETICOS_PADRAO = [
    {
        "id": "7100000000000000001",
        "url": "https://www.tiktok.com/@creator1/video/7100000000000000001",
        "target": " Clima ",
        "video_description": "Debate sobre mudancas climaticas",
        "voice_to_text": "Precisamos reduzir emissoes agora",
        "video_duration": "25.0",
    },
    {
        "id": "7100000000000000002",
        "url": "https://www.tiktok.com/@creator2/video/7100000000000000002",
        "target": "Clima",
        "video_description": "Analise neutra de indicadores ambientais",
        "voice_to_text": "Os dados mostram variacoes regionais",
        "video_duration": "30.0",
    },
    {
        "id": "7100000000000000003",
        "url": "https://www.tiktok.com/@creator3/video/7100000000000000003",
        "target": "Economia",
        "video_description": "Opiniao sobre taxa de juros",
        "voice_to_text": "A taxa de juros precisa cair",
        "video_duration": "20.0",
    },
    {
        "id": "7100000000000000004",
        "url": "https://www.tiktok.com/@creator4/video/7100000000000000004",
        "target": "Economia",
        "video_description": "Resumo de inflacao mensal",
        "voice_to_text": "O indice ficou estavel neste mes",
        "video_duration": "22.0",
    },
]

RESERVAS_SINTETICAS_PADRAO = [
    {
        "id": "7900000000000000001",
        "url": "https://www.tiktok.com/@reserve1/video/7900000000000000001",
        "target": "Clima",
        "video_description": "Video reserva sobre clima",
        "voice_to_text": "Reserva tematica de clima",
        "video_duration": "24.0",
    },
    {
        "id": "7900000000000000002",
        "url": "https://www.tiktok.com/@reserve2/video/7900000000000000002",
        "target": "Economia",
        "video_description": "Video reserva sobre economia",
        "voice_to_text": "Reserva tematica de economia",
        "video_duration": "26.0",
    },
]


def gravar_arquivos_estudo_sinteticos(
    diretorio_base: Path,
    videos: list[dict[str, Any]] | None = None,
    reservas: list[dict[str, Any]] | None = None,
    configuracao: dict[str, Any] | None = None,
) -> CaminhosDados:
    """Popula um diretorio isolado com arquivos CSV e JSON sinteticos."""
    diretorio_base.mkdir(parents=True, exist_ok=True)
    caminhos = resolver_caminhos_dados(diretorio_base)

    linhas_video = videos if videos is not None else VIDEOS_SINTETICOS_PADRAO
    linhas_reserva = reservas if reservas is not None else RESERVAS_SINTETICAS_PADRAO
    pd.DataFrame(linhas_video).to_csv(caminhos.arquivo_videos, index=False)
    pd.DataFrame(linhas_reserva).to_csv(caminhos.arquivo_videos_reserva, index=False)

    configuracao_efetiva = configuracao or {
        "administradores": ["admin"],
        "rotuladores": ["alice", "bob"],
        "percentual_sobreposicao": 50,
        "codigo_convite": "TOKSTANCE-2026",
    }
    caminhos.arquivo_configuracao.write_text(
        json.dumps(configuracao_efetiva, ensure_ascii=False, indent=4),
        encoding="utf-8",
    )
    return caminhos


@pytest.fixture()
def relogio_deterministico() -> RelogioDeterministico:
    """Fornece um relogio controlavel ancorado no horario de Brasilia (UTC-03:00)."""
    return RelogioDeterministico()


@pytest.fixture()
def caminhos_estudo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> CaminhosDados:
    """Fornece um diretorio temporario isolado vinculado a TOKSTANCE_DATA_DIR."""
    diretorio_estudo = tmp_path / "dados_estudo"
    monkeypatch.setenv("TOKSTANCE_DATA_DIR", str(diretorio_estudo))
    return gravar_arquivos_estudo_sinteticos(diretorio_estudo)
