"""Ponto de entrada principal da aplicacao TokStance (versao inicial do frontend)."""

import os
from pathlib import Path
import sys

#adiciona o diretorio src ao sys.path para execucao direta
_SRC_DIR = str(Path(__file__).resolve().parent.parent)
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from fastapi import FastAPI, Response
from fastapi.responses import FileResponse
import gradio as gr
import uvicorn

_STATIC_DIR = Path(__file__).resolve().parent / "frontend" / "static"
_FAVICON_ICO = _STATIC_DIR / "favicon.ico"
_FAVICON_SVG = _STATIC_DIR / "favicon.svg"

from tokstance.backend.api.routes import roteador_api
from tokstance.backend.security.middleware import (
    MiddlewareAntiDosLimitePayload,
    MiddlewareCabecalhosSeguranca,
    MiddlewareRateLimitIP,
)
from tokstance.frontend.gradio_ui import construir_interface
from tokstance.frontend.theme import (
    APP_CSS,
    JS_FORCAR_MODO_CLARO,
    obter_tema_branco,
)


def criar_aplicacao() -> FastAPI:
    """Cria a aplicacao FastAPI e acopla a interface visual Gradio na raiz."""
    app_fastapi = FastAPI(
        title="TokStance",
        description="Plataforma Colaborativa de Anotação e Concordância de Vídeos Curtos",
        version="1.0.0",
    )

    # Middlewares de seguranca OWASP, Anti-DoS e Rate Limiting
    app_fastapi.add_middleware(MiddlewareCabecalhosSeguranca)
    app_fastapi.add_middleware(MiddlewareAntiDosLimitePayload)
    app_fastapi.add_middleware(MiddlewareRateLimitIP)

    # Rotas estaticas para favicon customizado ("t!")
    @app_fastapi.get("/favicon.ico", include_in_schema=False)
    async def obter_favicon_ico() -> Response:
        if _FAVICON_ICO.exists():
            return FileResponse(str(_FAVICON_ICO), media_type="image/x-icon")
        return Response(status_code=404)

    @app_fastapi.get("/favicon.svg", include_in_schema=False)
    async def obter_favicon_svg() -> Response:
        if _FAVICON_SVG.exists():
            return FileResponse(str(_FAVICON_SVG), media_type="image/svg+xml")
        return Response(status_code=404)

    app_fastapi.include_router(roteador_api)

    tags_head = (
        '<link rel="icon" type="image/svg+xml" href="/favicon.svg?v=1">'
        '<link rel="alternate icon" type="image/x-icon" href="/favicon.ico?v=1">'
    )

    demo = construir_interface()
    app_montada = gr.mount_gradio_app(
        app_fastapi,
        demo,
        path="/",
        theme=obter_tema_branco(),
        css=APP_CSS,
        js=JS_FORCAR_MODO_CLARO,
        head=tags_head,
        favicon_path=str(_FAVICON_ICO) if _FAVICON_ICO.exists() else None,
        footer_links=[],
    )
    return app_montada


app = criar_aplicacao()


def iniciar_servidor(
    host: str = "0.0.0.0",
    porta: int = 7860,
    recarregar: bool = False,
) -> None:
    """Executa o servidor web uvicorn com a aplicacao montada."""
    uvicorn.run(
        "tokstance.main:app",
        host=host,
        port=porta,
        reload=recarregar,
    )


if __name__ == "__main__":
    porta = int(os.getenv("PORT", "7860"))
    host = os.getenv("HOST", "0.0.0.0")
    iniciar_servidor(host=host, porta=porta)
