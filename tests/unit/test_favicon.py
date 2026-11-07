"""Testes unitarios para o favicon customizado ("t!") e rotas estaticas."""

from fastapi.testclient import TestClient

from tokstance.main import app, _FAVICON_ICO, _FAVICON_SVG


def test_arquivos_favicon_existem():
    """Garante que os arquivos de favicon foram gerados e existem."""
    assert _FAVICON_ICO.exists(), "favicon.ico deve existir no diretorio static"
    assert _FAVICON_SVG.exists(), "favicon.svg deve existir no diretorio static"


def test_rota_favicon_ico():
    """Testa se a rota /favicon.ico responde com 200 e tipo image/x-icon."""
    cliente = TestClient(app)
    resposta = cliente.get("/favicon.ico")
    assert resposta.status_code == 200
    assert "image/x-icon" in resposta.headers.get("content-type", "")
    assert len(resposta.content) > 0


def test_rota_favicon_svg():
    """Testa se a rota /favicon.svg responde com 200 e contem o texto de marca 't!'."""
    cliente = TestClient(app)
    resposta = cliente.get("/favicon.svg")
    assert resposta.status_code == 200
    assert "image/svg+xml" in resposta.headers.get("content-type", "")
    assert "t!" in resposta.text
    assert "#9c0014" in resposta.text
