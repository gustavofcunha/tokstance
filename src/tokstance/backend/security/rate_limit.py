"""Limitador de tentativas por janela deslizante para login e cadastro."""

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
