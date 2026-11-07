"""Middlewares ASGI de seguranca para FastAPI e Gradio: cabecalhos, protecao anti-DoS e rate limiting."""

from __future__ import annotations

import os
import threading
import time
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from tokstance.config import (
    MAX_PAYLOAD_SIZE_BYTES,
    MAX_REQUISICOES_POR_MINUTO_IP,
)


class MiddlewareCabecalhosSeguranca(BaseHTTPMiddleware):
    """Injeta cabecalhos HTTP defensivos recomendados pela OWASP e Mozilla Web Security."""

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        response: Response = await call_next(request)

        # 1. Impede deteccao MIME incorreta no navegador (MIME-Sniffing)
        response.headers["X-Content-Type-Options"] = "nosniff"

        # 2. Protecao contra Clickjacking preservando iframes da propria aplicacao (Gradio)
        if "X-Frame-Options" not in response.headers:
            response.headers["X-Frame-Options"] = "SAMEORIGIN"

        # 3. Protecao contra ataques XSS refletidos legado
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # 4. Politica estrita de envio do cabecalho Referer
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # 5. Restringe acesso a recursos sensiveis de hardware do navegador
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
            "magnetometer=(), microphone=(), payment=(), usb=()"
        )

        # 6. HSTS ativado automaticamente se a conexao for HTTPS (producao)
        proto = request.headers.get("x-forwarded-proto", request.url.scheme).lower()
        if proto == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response


class MiddlewareAntiDosLimitePayload(BaseHTTPMiddleware):
    """Rejeita corpos de requisicao excessivamente grandes antes de esgotarem a memoria do servidor."""

    def __init__(self, app: Any, max_bytes: int = MAX_PAYLOAD_SIZE_BYTES) -> None:
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                tamanho = int(content_length)
                if tamanho > self.max_bytes:
                    return JSONResponse(
                        status_code=413,
                        content={
                            "detail": (
                                f"Corpo da requisição excede o limite máximo permitido de "
                                f"{self.max_bytes // (1024 * 1024)}MB."
                            )
                        },
                    )
            except ValueError:
                pass

        return await call_next(request)


class LimitadorRequisicoesPorIP:
    """Implementa janela deslizante thread-safe para controle de taxa por endereco IP com expurgo de memoria."""

    def __init__(
        self,
        limite_por_minuto: int = MAX_REQUISICOES_POR_MINUTO_IP,
        janela_segundos: float = 60.0,
        relogio: Any | None = None,
    ) -> None:
        self.limite = max(1, int(limite_por_minuto))
        self.janela_segundos = max(0.1, float(janela_segundos))
        self._relogio = relogio or time.monotonic
        self._trava = threading.Lock()
        self._historico_ip: dict[str, list[float]] = {}
        self._ultimo_expurgo = float(self._relogio())

    def _expurgar_ips_inativos(self, agora: float) -> None:
        """Limpa registros antigos a cada 2 minutos para evitar vazamento de memoria por flood de IPs."""
        if agora - self._ultimo_expurgo < 120.0 and self._ultimo_expurgo != 0.0:
            return
        self._ultimo_expurgo = agora
        corte = agora - self.janela_segundos
        chaves_remover = [
            ip for ip, timestamps in self._historico_ip.items()
            if not timestamps or timestamps[-1] <= corte
        ]
        for ip in chaves_remover:
            self._historico_ip.pop(ip, None)

    def registrar_e_verificar(self, ip: str) -> tuple[bool, int]:
        """Retorna (permitido: bool, segundos_espera: int)."""
        agora = float(self._relogio())
        corte = agora - self.janela_segundos

        with self._trava:
            self._expurgar_ips_inativos(agora)

            historico = self._historico_ip.get(ip, [])
            validos = [t for t in historico if t > corte]

            if len(validos) >= self.limite:
                self._historico_ip[ip] = validos
                tempo_espera = max(1, int(validos[0] + self.janela_segundos - agora))
                return False, tempo_espera

            validos.append(agora)
            self._historico_ip[ip] = validos
            return True, 0

    def limpar_tudo(self) -> None:
        with self._trava:
            self._historico_ip.clear()


class MiddlewareRateLimitIP(BaseHTTPMiddleware):
    """Intercepta requisicoes e bloqueia abusos ou ataques de inundacao (DDoS) por IP."""

    def __init__(
        self,
        app: Any,
        limitador: LimitadorRequisicoesPorIP | None = None,
    ) -> None:
        super().__init__(app)
        self.limitador = limitador or LimitadorRequisicoesPorIP()

    def _obter_ip_cliente(self, request: Request) -> str:
        """Obtem o endereco IP real considerando proxies reversos confiaveis."""
        # 1. Cabecalho padrao de proxies como Cloudflare, Render, Fly.io
        cf_ip = request.headers.get("cf-connecting-ip")
        if cf_ip:
            return cf_ip.strip()

        # 2. X-Forwarded-For (pega o primeiro endereco)
        x_forwarded = request.headers.get("x-forwarded-for")
        if x_forwarded:
            primeiro_ip = x_forwarded.split(",")[0].strip()
            if primeiro_ip:
                return primeiro_ip

        # 3. Fallback para host do socket
        if request.client and request.client.host:
            return str(request.client.host).strip()

        return "127.0.0.1"

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        # Ignorar limitacao se desativada explicitamente em testes
        if os.getenv("TOKSTANCE_DISABLE_RATE_LIMIT") == "1":
            return await call_next(request)

        ip = self._obter_ip_cliente(request)
        permitido, espera = self.limitador.registrar_e_verificar(ip)

        if not permitido:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": (
                        f"Muitas requisições originadas do endereço {ip}. "
                        f"Limite de taxa excedido. Tente novamente em {espera} segundos."
                    )
                },
                headers={"Retry-After": str(espera)},
            )

        return await call_next(request)
