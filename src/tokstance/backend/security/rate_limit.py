"""Limitador de tentativas por janela deslizante e controle de sessoes simultaneas."""

from collections.abc import Callable
import threading
import time

from tokstance.config import MAX_TENTATIVAS_LOGIN, SEGUNDOS_BLOQUEIO_LOGIN


class LimitadorTentativas:
    """Controla tentativas consecutivas falhas e bloqueio temporario por usuario."""

    def __init__(
        self,
        max_tentativas: int = MAX_TENTATIVAS_LOGIN,
        segundos_bloqueio: float = SEGUNDOS_BLOQUEIO_LOGIN,
        relogio: Callable[[], float] | None = None,
    ) -> None:
        self._max_tentativas = max(1, int(max_tentativas))
        self._segundos_bloqueio = max(1.0, float(segundos_bloqueio))
        self._relogio = relogio or time.monotonic
        self._trava = threading.Lock()
        self._falhas: dict[str, list[float]] = {}
        self._bloqueado_ate: dict[str, float] = {}

    def _chave_normalizada(self, chave: str) -> str:
        return str(chave or "").strip().lower()

    def _expirar_registros_antigos(self, chave_norm: str, agora: float) -> None:
        limite_bloqueio = self._bloqueado_ate.get(chave_norm)
        if limite_bloqueio is not None and agora >= limite_bloqueio:
            self._bloqueado_ate.pop(chave_norm, None)
            self._falhas.pop(chave_norm, None)
            return

        janela_inicio = agora - self._segundos_bloqueio
        historico = self._falhas.get(chave_norm, [])
        filtrado = [instante for instante in historico if instante > janela_inicio]
        if filtrado:
            self._falhas[chave_norm] = filtrado
        else:
            self._falhas.pop(chave_norm, None)

    def esta_bloqueado(self, chave: str) -> bool:
        """Retorna True se o usuario estiver temporariamente bloqueado."""
        return self.segundos_restantes_bloqueio(chave) > 0.0

    def segundos_restantes_bloqueio(self, chave: str) -> float:
        """Retorna quantos segundos restam de bloqueio para a chave informada."""
        chave_norm = self._chave_normalizada(chave)
        if not chave_norm:
            return 0.0
        agora = float(self._relogio())
        with self._trava:
            self._expirar_registros_antigos(chave_norm, agora)
            limite = self._bloqueado_ate.get(chave_norm)
            if limite is None or agora >= limite:
                return 0.0
            return round(limite - agora, 2)

    def registrar_falha(self, chave: str) -> bool:
        """Registra uma tentativa falha e retorna True caso atinja o bloqueio."""
        chave_norm = self._chave_normalizada(chave)
        if not chave_norm:
            return False
        agora = float(self._relogio())
        with self._trava:
            self._expirar_registros_antigos(chave_norm, agora)
            if chave_norm in self._bloqueado_ate and agora < self._bloqueado_ate[chave_norm]:
                return True
            historico = self._falhas.setdefault(chave_norm, [])
            historico.append(agora)
            if len(historico) >= self._max_tentativas:
                self._bloqueado_ate[chave_norm] = agora + self._segundos_bloqueio
                return True
            return False

    def registrar_sucesso(self, chave: str) -> None:
        """Limpa o historico de falhas e eventual bloqueio apos autenticacao valida."""
        chave_norm = self._chave_normalizada(chave)
        if not chave_norm:
            return
        with self._trava:
            self._falhas.pop(chave_norm, None)
            self._bloqueado_ate.pop(chave_norm, None)

    def limpar_tudo(self) -> None:
        """Remove todos os contadores e bloqueios ativos."""
        with self._trava:
            self._falhas.clear()
            self._bloqueado_ate.clear()


class GerenciadorSessoesAtivas:
    """Impede logins simultaneos na mesma conta mantendo registro thread-safe."""

    def __init__(self) -> None:
        self._trava = threading.Lock()
        self._usuarios_ativos: set[str] = set()

    def _normalizar_usuario(self, nome_usuario: str) -> str:
        return str(nome_usuario or "").strip()

    def reivindicar_sessao(self, nome_usuario: str) -> bool:
        """Reserva a sessao ativa para o usuario caso ainda nao esteja conectado."""
        limpo = self._normalizar_usuario(nome_usuario)
        if not limpo:
            return False
        with self._trava:
            if limpo in self._usuarios_ativos:
                return False
            self._usuarios_ativos.add(limpo)
            return True

    def liberar_sessao(self, nome_usuario: str) -> None:
        """Libera a sessao ativa de um usuario ao encerrar ou expirar a conexao."""
        limpo = self._normalizar_usuario(nome_usuario)
        if not limpo:
            return
        with self._trava:
            self._usuarios_ativos.discard(limpo)

    def esta_ativo(self, nome_usuario: str) -> bool:
        """Verifica se o usuario possui uma sessao ativa registrada."""
        limpo = self._normalizar_usuario(nome_usuario)
        if not limpo:
            return False
        with self._trava:
            return limpo in self._usuarios_ativos

    def listar_ativos(self) -> list[str]:
        """Retorna a lista ordenada de usuarios com sessao ativa no momento."""
        with self._trava:
            return sorted(self._usuarios_ativos)

    def limpar_tudo(self) -> None:
        """Remove todas as sessoes ativas registradas."""
        with self._trava:
            self._usuarios_ativos.clear()


_GERENCIADOR_SESSOES_PADRAO = GerenciadorSessoesAtivas()


def reivindicar_sessao_ativa(nome_usuario: str) -> bool:
    """Reserva sessao ativa global para o usuario caso nao haja outra aberta."""
    return _GERENCIADOR_SESSOES_PADRAO.reivindicar_sessao(nome_usuario)


def liberar_sessao_ativa(nome_usuario: str) -> None:
    """Libera a sessao ativa global associada ao usuario."""
    _GERENCIADOR_SESSOES_PADRAO.liberar_sessao(nome_usuario)


def usuario_esta_ativo(nome_usuario: str) -> bool:
    """Indica se o usuario ja possui sessao ativa global aberta."""
    return _GERENCIADOR_SESSOES_PADRAO.esta_ativo(nome_usuario)


def listar_usuarios_ativos() -> list[str]:
    """Lista os nomes de usuario com sessao ativa global no momento."""
    return _GERENCIADOR_SESSOES_PADRAO.listar_ativos()


def limpar_sessoes_ativas() -> None:
    """Limpa todas as sessoes ativas globais registradas."""
    _GERENCIADOR_SESSOES_PADRAO.limpar_tudo()
