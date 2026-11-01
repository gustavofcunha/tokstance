"""Ponto de entrada principal da aplicacao TokStance (versao inicial do frontend)."""

import os
from pathlib import Path
import sys

#adiciona o diretorio src ao sys.path para execucao direta
_SRC_DIR = str(Path(__file__).resolve().parent.parent)
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from fastapi import FastAPI
import gradio as gr
import uvicorn

from tokstance.backend.api.routes import roteador_api
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
    app_fastapi.include_router(roteador_api)

    demo = construir_interface()
    app_montada = gr.mount_gradio_app(
        app_fastapi,
        demo,
        path="/",
        theme=obter_tema_branco(),
        css=APP_CSS,
        js=JS_FORCAR_MODO_CLARO,
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
