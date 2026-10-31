"""Configuracao de ambiente, fuso horario oficial de Brasilia, caminhos de arquivos e constantes."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path

DIRETORIO_PROJETO = Path(__file__).resolve().parent.parent.parent
PROJECT_DIR = DIRETORIO_PROJETO
#brasilia official timezone utc minus 3
BRT_TZ = timezone(timedelta(hours=-3))
FUSO_BRT = BRT_TZ

SEGUNDOS_MINIMOS_REPORTE_ERRO = 10.0
MIN_ERROR_REPORT_SECONDS = SEGUNDOS_MINIMOS_REPORTE_ERRO

TOLERANCIA_ANOTACAO_RAPIDA_SEGUNDOS = 5.0
FAST_ANNOTATION_TOLERANCE_SECONDS = TOLERANCIA_ANOTACAO_RAPIDA_SEGUNDOS

MAX_TENTATIVAS_LOGIN = 5
MAX_LOGIN_ATTEMPTS = MAX_TENTATIVAS_LOGIN

SEGUNDOS_BLOQUEIO_LOGIN = 60.0
LOGIN_LOCKOUT_SECONDS = SEGUNDOS_BLOQUEIO_LOGIN

TAMANHO_MINIMO_SENHA = 6
MIN_PASSWORD_LENGTH = TAMANHO_MINIMO_SENHA

TAMANHO_MAXIMO_SENHA = 128
MAX_PASSWORD_LENGTH = TAMANHO_MAXIMO_SENHA

TAMANHO_MAXIMO_USUARIO = 64
MAX_USERNAME_LENGTH = TAMANHO_MAXIMO_USUARIO

TAMANHO_MAXIMO_CAMPO_TEXTO = 512
MAX_TEXT_FIELD_LENGTH = TAMANHO_MAXIMO_CAMPO_TEXTO

CODIGO_CONVITE_PADRAO = os.getenv("TOKSTANCE_INVITE_TOKEN", "TOKSTANCE-2026")
DEFAULT_INVITE_TOKEN = CODIGO_CONVITE_PADRAO

USUARIO_ADMIN_PADRAO = os.getenv("TOKSTANCE_ADMIN_USER", "admin")
DEFAULT_ADMIN_USERNAME = USUARIO_ADMIN_PADRAO

SENHA_ADMIN_PADRAO = os.getenv("TOKSTANCE_ADMIN_PASSWORD", "TokStance@Admin2026")
DEFAULT_ADMIN_PASSWORD = SENHA_ADMIN_PADRAO


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

    @property
    def base_dir(self) -> Path:
        return self.diretorio_base

    @property
    def videos_file(self) -> Path:
        return self.arquivo_videos

    @property
    def reserve_videos_file(self) -> Path:
        return self.arquivo_videos_reserva

    @property
    def results_file(self) -> Path:
        return self.arquivo_resultados

    @property
    def assignments_file(self) -> Path:
        return self.arquivo_atribuicoes

    @property
    def config_file(self) -> Path:
        return self.arquivo_configuracao

    @property
    def log_file(self) -> Path:
        return self.arquivo_log

    @property
    def errors_file(self) -> Path:
        return self.arquivo_erros

    @property
    def agreement_file(self) -> Path:
        return self.arquivo_concordancia

    @property
    def database_file(self) -> Path:
        return self.arquivo_banco_dados


DataPaths = CaminhosDados


def resolver_diretorio_dados(diretorio_customizado: Path | str | None = None) -> Path:
    """Resolve o diretorio ativo de dados do estudo por argumento explicito ou variavel de ambiente."""
    if diretorio_customizado is not None:
        return Path(diretorio_customizado).resolve()
    env_dir = os.getenv("TOKSTANCE_DATA_DIR")
    if env_dir:
        return Path(env_dir).resolve()
    return (DIRETORIO_PROJETO / "data").resolve()


resolve_data_dir = resolver_diretorio_dados


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


resolve_data_paths = resolver_caminhos_dados


def agora_brt() -> datetime:
    """Retorna o datetime atual com fuso horario de Brasilia (UTC-03:00)."""
    return datetime.now(BRT_TZ)


now_brt = agora_brt


def formatar_data_hora_brt(momento: datetime | None = None) -> str:
    """Formata um datetime no fuso horario de Brasilia no padrao YYYY-MM-DD HH:MM:SS."""
    momento_alvo = momento.astimezone(BRT_TZ) if momento is not None else agora_brt()
    return momento_alvo.strftime("%Y-%m-%d %H:%M:%S")


format_brt_timestamp = formatar_data_hora_brt

CAMINHOS_PADRAO = resolver_caminhos_dados()
DEFAULT_PATHS = CAMINHOS_PADRAO
DIRETORIO_BASE = CAMINHOS_PADRAO.diretorio_base
BASE_DIR = DIRETORIO_BASE
ARQUIVO_VIDEOS = CAMINHOS_PADRAO.arquivo_videos
VIDEOS_FILE = ARQUIVO_VIDEOS
ARQUIVO_VIDEOS_RESERVA = CAMINHOS_PADRAO.arquivo_videos_reserva
RESERVE_VIDEOS_FILE = ARQUIVO_VIDEOS_RESERVA
ARQUIVO_RESULTADOS = CAMINHOS_PADRAO.arquivo_resultados
RESULTS_FILE = ARQUIVO_RESULTADOS
ARQUIVO_ATRIBUICOES = CAMINHOS_PADRAO.arquivo_atribuicoes
ASSIGNMENTS_FILE = ARQUIVO_ATRIBUICOES
ARQUIVO_CONFIGURACAO = CAMINHOS_PADRAO.arquivo_configuracao
CONFIG_FILE = ARQUIVO_CONFIGURACAO
ARQUIVO_LOG = CAMINHOS_PADRAO.arquivo_log
LOG_FILE = ARQUIVO_LOG
ARQUIVO_ERROS = CAMINHOS_PADRAO.arquivo_erros
ERRORS_FILE = ARQUIVO_ERROS
ARQUIVO_CONCORDANCIA = CAMINHOS_PADRAO.arquivo_concordancia
AGREEMENT_FILE = ARQUIVO_CONCORDANCIA
ARQUIVO_BANCO_DADOS = CAMINHOS_PADRAO.arquivo_banco_dados
DATABASE_FILE = ARQUIVO_BANCO_DADOS
