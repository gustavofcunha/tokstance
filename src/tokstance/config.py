"""Configuracao de ambiente, fuso horario oficial de Brasilia, caminhos de arquivos e constantes."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path

DIRETORIO_PROJETO = Path(__file__).resolve().parent.parent.parent
#fuso horario oficial de brasilia utc menos 3
FUSO_BRT = timezone(timedelta(hours=-3))

SEGUNDOS_MINIMOS_REPORTE_ERRO = 10.0
TOLERANCIA_ANOTACAO_RAPIDA_SEGUNDOS = 5.0

MAX_TENTATIVAS_LOGIN = 5
SEGUNDOS_BLOQUEIO_LOGIN = 60.0
TAMANHO_MINIMO_SENHA = 6
TAMANHO_MAXIMO_SENHA = 128
TAMANHO_MAXIMO_USUARIO = 64
TAMANHO_MAXIMO_CAMPO_TEXTO = 512

CODIGO_CONVITE_PADRAO = os.getenv("TOKSTANCE_INVITE_TOKEN", "TOKSTANCE-2026")
USUARIO_ADMIN_PADRAO = os.getenv("TOKSTANCE_ADMIN_USER", "admin")
SENHA_ADMIN_PADRAO = os.getenv("TOKSTANCE_ADMIN_PASSWORD", "TokStance@Admin2026")


@dataclass(frozen=True)
class CaminhosDados:
    """Caminhos de arquivos resolvidos para o diretorio de dados de um estudo TokStance."""

    diretorio_base: Path
    arquivo_videos: Path
    arquivo_videos_reserva: Path
    arquivo_resultados: Path
    arquivo_atribuicoes: Path
    arquivo_configuracao: Path
    arquivo_log: Path
    arquivo_erros: Path
    arquivo_concordancia: Path
    arquivo_banco_dados: Path


def resolver_diretorio_dados(diretorio_customizado: Path | str | None = None) -> Path:
    """Resolve o diretorio ativo de dados do estudo por argumento explicito ou variavel de ambiente."""
    if diretorio_customizado is not None:
        return Path(diretorio_customizado).resolve()
    diretorio_env = os.getenv("TOKSTANCE_DATA_DIR")
    if diretorio_env:
        return Path(diretorio_env).resolve()
    return (DIRETORIO_PROJETO / "data").resolve()


def resolver_caminhos_dados(diretorio_customizado: Path | str | None = None) -> CaminhosDados:
    """Constroi todos os caminhos canonicos de arquivos para o diretorio de dados informado."""
    base = resolver_diretorio_dados(diretorio_customizado)
    return CaminhosDados(
        diretorio_base=base,
        arquivo_videos=base / "videos.csv",
        arquivo_videos_reserva=base / "videos_reserva.csv",
        arquivo_resultados=base / "resultados_anotacao.csv",
        arquivo_atribuicoes=base / "atribuicoes.csv",
        arquivo_configuracao=base / "configuracao.json",
        arquivo_log=base / "acessos_log.csv",
        arquivo_erros=base / "erros_videos.csv",
        arquivo_concordancia=base / "concordancia.json",
        arquivo_banco_dados=base / "tokstance.db",
    )


def agora_brt() -> datetime:
    """Retorna o datetime atual com fuso horario de Brasilia (UTC-03:00)."""
    return datetime.now(FUSO_BRT)


def formatar_data_hora_brt(momento: datetime | None = None) -> str:
    """Formata um datetime no fuso horario de Brasilia no padrao YYYY-MM-DD HH:MM:SS."""
    momento_alvo = momento.astimezone(FUSO_BRT) if momento is not None else agora_brt()
    return momento_alvo.strftime("%Y-%m-%d %H:%M:%S")


CAMINHOS_PADRAO = resolver_caminhos_dados()
DIRETORIO_BASE = CAMINHOS_PADRAO.diretorio_base
ARQUIVO_VIDEOS = CAMINHOS_PADRAO.arquivo_videos
ARQUIVO_VIDEOS_RESERVA = CAMINHOS_PADRAO.arquivo_videos_reserva
ARQUIVO_RESULTADOS = CAMINHOS_PADRAO.arquivo_resultados
ARQUIVO_ATRIBUICOES = CAMINHOS_PADRAO.arquivo_atribuicoes
ARQUIVO_CONFIGURACAO = CAMINHOS_PADRAO.arquivo_configuracao
ARQUIVO_LOG = CAMINHOS_PADRAO.arquivo_log
ARQUIVO_ERROS = CAMINHOS_PADRAO.arquivo_erros
ARQUIVO_CONCORDANCIA = CAMINHOS_PADRAO.arquivo_concordancia
ARQUIVO_BANCO_DADOS = CAMINHOS_PADRAO.arquivo_banco_dados
