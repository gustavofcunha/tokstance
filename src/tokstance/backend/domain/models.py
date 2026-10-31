"""Modelos de dominio, estruturas de dados e definicoes de esquemas tabulares."""

from dataclasses import dataclass, field
from itertools import combinations
import json
from pathlib import Path
from typing import Any

import pandas as pd

from tokstance.config import CODIGO_CONVITE_PADRAO, resolver_caminhos_dados

PAPEL_ADMINISTRADOR = "administrador"
PAPEL_ROTULADOR = "rotulador"
PAPEIS_VALIDOS = (PAPEL_ADMINISTRADOR, PAPEL_ROTULADOR)

POOL_PRINCIPAL = "principal"
POOL_RESERVA = "reserva"
TIPOS_POOL_VALIDOS = (POOL_PRINCIPAL, POOL_RESERVA)

COLUNAS_OBRIGATORIAS_VIDEO = ("id", "url", "target")
VIDEO_REQUIRED_COLUMNS = COLUNAS_OBRIGATORIAS_VIDEO

COLUNAS_OPCIONAIS_VIDEO = ("video_description", "voice_to_text", "video_duration")
VIDEO_OPTIONAL_COLUMNS = COLUNAS_OPCIONAIS_VIDEO

COLUNAS_VIDEO = COLUNAS_OBRIGATORIAS_VIDEO + COLUNAS_OPCIONAIS_VIDEO
VIDEO_COLUMNS = COLUNAS_VIDEO

COLUNAS_ATRIBUICAO = (
    "assignment_version",
    "assignment_id",
    "labeler",
    "video_id",
    "url",
    "target",
    "video_description",
    "voice_to_text",
    "video_duration",
)
ASSIGNMENT_COLUMNS = COLUNAS_ATRIBUICAO

COLUNAS_RESULTADO = (
    "timestamp",
    "labeler",
    "video_id",
    "url",
    "target",
    "stance",
    "tempo_analise_segundos",
    "video_duration",
    "assignment_id",
)
RESULT_COLUMNS = COLUNAS_RESULTADO

COLUNAS_ERRO = (
    "timestamp",
    "video_id",
    "url",
    "labeler",
    "assignment_id",
    "replacement_video_id",
    "replacement_url",
    "replacement_assignment_id",
    "replacement_status",
)
ERROR_COLUMNS = COLUNAS_ERRO

COLUNAS_LOG = (
    "timestamp",
    "usuario",
    "acao",
    "tempo_desde_login_segundos",
)
LOG_COLUMNS = COLUNAS_LOG

NOME_TAREFA_PADRAO = "Detecção de Posição"
DEFAULT_TASK_NAME = NOME_TAREFA_PADRAO

PERGUNTA_TAREFA_PADRAO = "Qual a posição expressa no vídeo em relação ao target?"
DEFAULT_TASK_QUESTION = PERGUNTA_TAREFA_PADRAO

OPCOES_TAREFA_PADRAO = (
    "Contra",
    "A Favor",
    "Neutro",
    "Vídeo não relacionado ao target",
)
DEFAULT_TASK_OPTIONS = OPCOES_TAREFA_PADRAO

DISTANCIAS_ROTULOS_PADRAO: dict[str, float] = {
    "Contra|A Favor": 3.0,
    "Contra|Neutro": 1.0,
    "Contra|Vídeo não relacionado ao target": 2.0,
    "A Favor|Neutro": 1.0,
    "A Favor|Vídeo não relacionado ao target": 2.0,
    "Neutro|Vídeo não relacionado ao target": 2.0,
}
DEFAULT_LABEL_DISTANCES = DISTANCIAS_ROTULOS_PADRAO


def chave_par_rotulos(esquerda: str, direita: str) -> str:
    """Formata a chave canonica para um par de rotulos da tarefa."""
    return f"{str(esquerda).strip()}|{str(direita).strip()}"


pair_key = chave_par_rotulos


def limpar_usuarios(valor: str | list[str] | tuple[str, ...] | None) -> list[str]:
    """Normaliza uma lista de itens ou usuarios separada por virgula ou quebra de linha."""
    if isinstance(valor, (list, tuple, set)):
        texto_bruto = "\n".join(str(item) for item in valor)
    else:
        texto_bruto = str(valor or "")
    candidatos = texto_bruto.replace(",", "\n").splitlines()
    return list(dict.fromkeys(usuario.strip() for usuario in candidatos if usuario.strip()))


clean_users = limpar_usuarios


def gerar_combinacoes_rotulos(
    opcoes: list[str] | tuple[str, ...],
    distancias_existentes: dict[str, Any] | None = None,
    penalidade_padrao: float = 1.0,
    *,
    existing_distances: dict[str, Any] | None = None,
    default_penalty: float | None = None,
) -> dict[str, float]:
    """Gera todas as combinacoes par-a-par de rotulos e seus pesos de penalidade."""
    opcoes_normalizadas = limpar_usuarios(list(opcoes))
    mapa_distancias = (
        existing_distances if existing_distances is not None else distancias_existentes
    )
    peso_padrao = (
        float(default_penalty) if default_penalty is not None else float(penalidade_padrao)
    )
    tabela_pesos: dict[frozenset[str], float] = {}
    if isinstance(mapa_distancias, dict):
        for par_bruto, peso_bruto in mapa_distancias.items():
            partes = [parte.strip() for parte in str(par_bruto).split("|", maxsplit=1)]
            if len(partes) == 2 and partes[0] and partes[1] and partes[0] != partes[1]:
                try:
                    tabela_pesos[frozenset(partes)] = float(peso_bruto)
                except (TypeError, ValueError):
                    continue

    geradas: dict[str, float] = {}
    for esquerda, direita in combinations(opcoes_normalizadas, 2):
        chave = chave_par_rotulos(esquerda, direita)
        peso = tabela_pesos.get(frozenset((esquerda, direita)), peso_padrao)
        geradas[chave] = float(peso)
    return geradas


generate_label_combinations = gerar_combinacoes_rotulos


@dataclass(frozen=True)
class RegistroVideo:
    """Representacao imutavel de um item de video principal ou reserva."""

    video_id: str
    url: str
    target: str
    video_description: str = ""
    voice_to_text: str = ""
    video_duration: str = ""
    tipo_pool: str = POOL_PRINCIPAL


VideoRecord = RegistroVideo


@dataclass
class ConfiguracaoEstudo:
    """Configuracao normalizada de uma tarefa de anotacao."""

    administradores: list[str] = field(default_factory=lambda: ["admin"])
    rotuladores: list[str] = field(default_factory=list)
    videos_por_rotulador: int = 10
    percentual_sobreposicao: float = 0.0
    tarefa: str = NOME_TAREFA_PADRAO
    pergunta: str = PERGUNTA_TAREFA_PADRAO
    opcoes_posicao: list[str] = field(
        default_factory=lambda: list(OPCOES_TAREFA_PADRAO)
    )
    distancias_rotulos: dict[str, float] = field(
        default_factory=lambda: dict(DISTANCIAS_ROTULOS_PADRAO)
    )
    codigo_convite: str = CODIGO_CONVITE_PADRAO

    @property
    def admins(self) -> list[str]:
        return self.administradores

    @property
    def labelers(self) -> list[str]:
        return self.rotuladores

    @property
    def videos_per_labeler(self) -> int:
        return self.videos_por_rotulador

    @property
    def overlap_percent(self) -> float:
        return self.percentual_sobreposicao

    @property
    def stance_options(self) -> list[str]:
        return self.opcoes_posicao

    @property
    def label_distances(self) -> dict[str, float]:
        return self.distancias_rotulos

    @property
    def invite_token(self) -> str:
        return self.codigo_convite

    def para_dicionario(self) -> dict[str, Any]:
        """Serializa a configuracao do estudo em dicionario compativel com JSON."""
        distancias = gerar_combinacoes_rotulos(
            self.opcoes_posicao, self.distancias_rotulos
        )
        return {
            "administradores": list(self.administradores),
            "rotuladores": list(self.rotuladores),
            "videos_por_rotulador": int(self.videos_por_rotulador),
            "percentual_sobreposicao": float(self.percentual_sobreposicao),
            "tarefa": str(self.tarefa),
            "pergunta": str(self.pergunta),
            "opcoes_posicao": list(self.opcoes_posicao),
            "distancias_rotulos": dict(distancias),
            "codigo_convite": str(self.codigo_convite),
        }

    def to_dict(self) -> dict[str, Any]:
        """Alias de compatibilidade para serializacao em dicionario."""
        return self.para_dicionario()


StudyConfig = ConfiguracaoEstudo


@dataclass(frozen=True)
class ContaUsuario:
    """Conta de usuario cadastrada com papel e vaga atribuida."""

    nome_usuario: str
    senha_hash: str
    papel: str = PAPEL_ROTULADOR
    vaga_atribuida: str = ""
    criado_em: str = ""

    @property
    def username(self) -> str:
        return self.nome_usuario

    @property
    def password_hash(self) -> str:
        return self.senha_hash

    @property
    def role(self) -> str:
        return self.papel

    @property
    def assigned_slot(self) -> str:
        return self.vaga_atribuida

    @property
    def created_at(self) -> str:
        return self.criado_em


UserAccount = ContaUsuario


@dataclass(frozen=True)
class RegistroAnotacao:
    """Anotacao de posicao concluida e submetida por um rotulador."""

    timestamp: str
    rotulador: str
    video_id: str
    url: str
    target: str
    posicao: str
    tempo_analise_segundos: float
    video_duration: str
    assignment_id: str

    @property
    def labeler(self) -> str:
        return self.rotulador

    @property
    def stance(self) -> str:
        return self.posicao


AnnotationRecord = RegistroAnotacao


@dataclass(frozen=True)
class RegistroErroVideo:
    """Registro de video indisponivel reportado e resultado da substituicao por reserva."""

    timestamp: str
    video_id: str
    url: str
    rotulador: str
    assignment_id: str
    replacement_video_id: str = ""
    replacement_url: str = ""
    replacement_assignment_id: str = ""
    replacement_status: str = ""

    @property
    def labeler(self) -> str:
        return self.rotulador


VideoErrorRecord = RegistroErroVideo


def carregar_videos(arquivo_videos: Path | None = None) -> pd.DataFrame:
    """Carrega e valida o conjunto de videos principais em videos.csv."""
    caminho_alvo = (
        Path(arquivo_videos)
        if arquivo_videos is not None
        else resolver_caminhos_dados().arquivo_videos
    )
    if not caminho_alvo.exists():
        raise FileNotFoundError(
            f"\n[ERRO CRÍTICO] Arquivo '{caminho_alvo.name}' ausente. A execução foi abortada."
        )
    if caminho_alvo.stat().st_size == 0:
        raise ValueError("videos.csv precisa conter ao menos um registro de vídeo.")
    try:
        videos = pd.read_csv(caminho_alvo, dtype=str).fillna("")
    except pd.errors.EmptyDataError as exc:
        raise ValueError("videos.csv precisa conter ao menos um registro de vídeo.") from exc

    if videos.empty:
        raise ValueError("videos.csv precisa conter ao menos um registro de vídeo.")
    ausentes = set(COLUNAS_OBRIGATORIAS_VIDEO).difference(videos.columns)
    if ausentes:
        raise ValueError(
            f"videos.csv não possui as colunas obrigatórias: {', '.join(sorted(ausentes))}"
        )
    for coluna in COLUNAS_OPCIONAIS_VIDEO:
        if coluna not in videos.columns:
            videos[coluna] = ""
    return videos.fillna("")


load_videos = carregar_videos


def carregar_videos_reserva(arquivo_videos_reserva: Path | None = None) -> pd.DataFrame:
    """Carrega e valida o conjunto de videos reserva em videos_reserva.csv."""
    caminho_alvo = (
        Path(arquivo_videos_reserva)
        if arquivo_videos_reserva is not None
        else resolver_caminhos_dados().arquivo_videos_reserva
    )
    if not caminho_alvo.exists():
        raise FileNotFoundError(
            f"\n[ERRO CRÍTICO] Arquivo '{caminho_alvo.name}' ausente. A execução foi abortada."
        )
    if caminho_alvo.stat().st_size == 0:
        raise ValueError("videos_reserva.csv precisa conter ao menos um registro de vídeo.")
    try:
        videos_reserva = pd.read_csv(caminho_alvo, dtype=str).fillna("")
    except pd.errors.EmptyDataError as exc:
        raise ValueError(
            "videos_reserva.csv precisa conter ao menos um registro de vídeo."
        ) from exc

    if videos_reserva.empty:
        raise ValueError("videos_reserva.csv precisa conter ao menos um registro de vídeo.")
    ausentes = set(COLUNAS_OBRIGATORIAS_VIDEO).difference(videos_reserva.columns)
    if ausentes:
        raise ValueError(
            f"videos_reserva.csv não possui as colunas obrigatórias: {', '.join(sorted(ausentes))}"
        )
    for coluna in COLUNAS_OPCIONAIS_VIDEO:
        if coluna not in videos_reserva.columns:
            videos_reserva[coluna] = ""
    return videos_reserva.fillna("")


load_reserve_videos = carregar_videos_reserva


def validar_arquivos_entrada_obrigatorios(
    arquivo_videos: Path | None = None,
    arquivo_videos_reserva: Path | None = None,
) -> None:
    """Garante que os arquivos de videos principais e reserva existem e possuem esquema valido."""
    carregar_videos(arquivo_videos)
    carregar_videos_reserva(arquivo_videos_reserva)


validate_required_input_files = validar_arquivos_entrada_obrigatorios


def dividir_videos_principal_e_reserva(
    pool_videos: pd.DataFrame,
    quantidade_principal: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Seleciona videos principais de forma balanceada por target e coloca o restante como reserva."""
    colunas = list(COLUNAS_VIDEO)
    if pool_videos.empty:
        vazio = pd.DataFrame(columns=colunas)
        return vazio.copy(), vazio.copy()

    normalizado = pool_videos.copy()
    for coluna in COLUNAS_OPCIONAIS_VIDEO:
        if coluna not in normalizado.columns:
            normalizado[coluna] = ""
    normalizado = normalizado[colunas].fillna("").drop_duplicates(subset=["id"], keep="first").reset_index(drop=True)

    #intercala videos entre targets normalizados para balancear a selecao principal
    baldes_target: dict[str, list[int]] = {}
    ordem_targets: list[str] = []
    for indice_video, target_bruto in enumerate(normalizado["target"].astype(str).tolist()):
        chave_target = target_bruto.strip()
        if chave_target not in baldes_target:
            baldes_target[chave_target] = []
            ordem_targets.append(chave_target)
        baldes_target[chave_target].append(indice_video)

    ordem_intercalada: list[int] = []
    while any(baldes_target[chave] for chave in ordem_targets):
        for chave in ordem_targets:
            if baldes_target[chave]:
                ordem_intercalada.append(baldes_target[chave].pop(0))

    limite = max(0, min(int(quantidade_principal), len(ordem_intercalada)))
    indices_principais = sorted(ordem_intercalada[:limite])
    conjunto_principais = set(indices_principais)
    indices_reserva = [idx for idx in range(len(normalizado)) if idx not in conjunto_principais]

    principais = normalizado.iloc[indices_principais].reset_index(drop=True)
    reservas = normalizado.iloc[indices_reserva].reset_index(drop=True)
    return principais, reservas


split_primary_and_reserve_videos = dividir_videos_principal_e_reserva


def salvar_configuracao(
    configuracao: dict[str, Any] | ConfiguracaoEstudo,
    arquivo_configuracao: Path | None = None,
) -> None:
    """Persiste a configuracao do estudo em JSON no disco."""
    caminho_alvo = (
        Path(arquivo_configuracao)
        if arquivo_configuracao is not None
        else resolver_caminhos_dados().arquivo_configuracao
    )
    caminho_alvo.parent.mkdir(parents=True, exist_ok=True)
    conteudo = (
        configuracao.para_dicionario()
        if isinstance(configuracao, ConfiguracaoEstudo)
        else dict(configuracao)
    )
    with caminho_alvo.open("w", encoding="utf-8") as handle:
        json.dump(conteudo, handle, ensure_ascii=False, indent=2)


save_config = salvar_configuracao


def carregar_configuracao(arquivo_configuracao: Path | None = None) -> dict[str, Any]:
    """Carrega e normaliza a configuracao do estudo a partir de configuracao.json."""
    caminho_alvo = (
        Path(arquivo_configuracao)
        if arquivo_configuracao is not None
        else resolver_caminhos_dados().arquivo_configuracao
    )
    if not caminho_alvo.exists():
        configuracao_padrao = ConfiguracaoEstudo().para_dicionario()
        salvar_configuracao(configuracao_padrao, caminho_alvo)
        return configuracao_padrao

    try:
        with caminho_alvo.open(encoding="utf-8") as handle:
            config_bruta = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("configuracao.json inválido ou corrompido.") from exc

    if not isinstance(config_bruta, dict):
        raise ValueError("configuracao.json inválido ou corrompido.")

    administradores = limpar_usuarios(
        config_bruta.get("administradores", config_bruta.get("admins", []))
    )
    rotuladores = limpar_usuarios(
        config_bruta.get("rotuladores", config_bruta.get("labelers", []))
    )
    videos_por_rotulador = int(
        config_bruta.get(
            "videos_por_rotulador", config_bruta.get("videos_per_labeler", 10)
        )
    )
    percentual_sobreposicao = float(
        config_bruta.get(
            "percentual_sobreposicao", config_bruta.get("overlap_percent", 0.0)
        )
    )
    tarefa = (
        str(config_bruta.get("tarefa") or NOME_TAREFA_PADRAO).strip()
        or NOME_TAREFA_PADRAO
    )
    pergunta = (
        str(config_bruta.get("pergunta") or PERGUNTA_TAREFA_PADRAO).strip()
        or PERGUNTA_TAREFA_PADRAO
    )
    opcoes_configuradas = limpar_usuarios(
        config_bruta.get("opcoes_posicao", config_bruta.get("stance_options", []))
    )
    opcoes_posicao = (
        opcoes_configuradas
        if len(opcoes_configuradas) >= 2
        else list(OPCOES_TAREFA_PADRAO)
    )
    distancias_fallback = (
        DISTANCIAS_ROTULOS_PADRAO
        if opcoes_posicao == list(OPCOES_TAREFA_PADRAO)
        else {}
    )
    distancias_brutas = config_bruta.get(
        "distancias_rotulos", config_bruta.get("label_distances")
    )
    distancias_efetivas = (
        distancias_brutas
        if isinstance(distancias_brutas, dict) and distancias_brutas
        else distancias_fallback
    )
    distancias_rotulos = gerar_combinacoes_rotulos(opcoes_posicao, distancias_efetivas)
    codigo_convite = str(
        config_bruta.get("codigo_convite")
        or config_bruta.get("invite_token")
        or CODIGO_CONVITE_PADRAO
    ).strip() or CODIGO_CONVITE_PADRAO

    return {
        "administradores": administradores,
        "rotuladores": rotuladores,
        "videos_por_rotulador": videos_por_rotulador,
        "percentual_sobreposicao": percentual_sobreposicao,
        "tarefa": tarefa,
        "pergunta": pergunta,
        "opcoes_posicao": opcoes_posicao,
        "distancias_rotulos": distancias_rotulos,
        "codigo_convite": codigo_convite,
    }


load_config = carregar_configuracao
