"""Testes de ponta a ponta (E2E) no navegador para jornadas criticas de usuario."""

import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from typing import Any, Dict, Iterator, Tuple
import urllib.request
import pandas as pd
import pytest
from playwright.sync_api import Browser, Page, sync_playwright

from tokstance.backend.repositories.database import BancoDadosSQLite
from tokstance.backend.repositories.study_repo import RepositorioEstudo
from tokstance.backend.repositories.user_repo import RepositorioUsuarios
from tokstance.backend.services.admin_service import ServicoAdministracao
from tokstance.backend.services.auth_service import ServicoAutenticacao


def _obter_env_navegador() -> Dict[str, str]:
    #browser library path configuration for headless execution
    p1 = str(Path.home() / ".local/lib/playwright_deps/usr/lib/x86_64-linux-gnu")
    p2 = str(Path.home() / ".local/lib/playwright_deps/lib/x86_64-linux-gnu")
    cur_ld = os.environ.get("LD_LIBRARY_PATH", "")
    return dict(os.environ, LD_LIBRARY_PATH=f"{p1}:{p2}:{cur_ld}")


def _encontrar_porta_livre() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture(scope="module")
def servidor_e2e() -> Iterator[Tuple[str, str, str]]:
    #isolated test directory with standard dataset
    diretorio_base = Path(__file__).resolve().parent.parent.parent
    dados_temp = tempfile.mkdtemp(prefix="tokstance_e2e_srv_")
    caminho_dados = Path(dados_temp)

    shutil.copy(diretorio_base / "data/videos.csv", caminho_dados / "videos.csv")
    shutil.copy(diretorio_base / "data/videos_reserva.csv", caminho_dados / "videos_reserva.csv")

    banco = BancoDadosSQLite(caminho_dados / "tokstance.db")
    repo_usuarios = RepositorioUsuarios(banco)
    repo_estudo = RepositorioEstudo(banco, repo_usuarios=repo_usuarios)
    servico_auth = ServicoAutenticacao(banco, repo_usuarios=repo_usuarios, repo_estudo=repo_estudo)
    servico_admin = ServicoAdministracao(banco, repo_usuarios=repo_usuarios, repo_estudo=repo_estudo)

    #seed demo admin user and initial task
    admin_info = servico_auth.cadastrar_usuario("coordenador_e2e", "senhaForte123", email="coord@exemplo.org")
    pool_p = pd.read_csv(caminho_dados / "videos.csv", dtype=str).fillna("")
    pool_r = pd.read_csv(caminho_dados / "videos_reserva.csv", dtype=str).fillna("")

    codigo_convite = "TOK-E2E001"
    servico_admin.criar_nova_tarefa(
        usuario_administrador_id=int(admin_info["usuario_id"]),
        pool_videos=pool_p,
        videos_reserva_explicitos=pool_r,
        titulo="Detecção de Posição E2E",
        pergunta="Qual a posição expressa no vídeo em relação ao target?",
        opcoes_posicao=["Contra", "A Favor", "Neutro", "Vídeo não relacionado ao target"],
        numero_vagas=3,
        percentual_sobreposicao=50.0,
        codigo_convite=codigo_convite,
        permitir_admin_como_rotulador=True,
    )

    porta = _encontrar_porta_livre()
    url_base = f"http://127.0.0.1:{porta}"

    env_servidor = dict(
        os.environ,
        PORT=str(porta),
        HOST="127.0.0.1",
        TOKSTANCE_DATA_DIR=dados_temp,
        PYTHONPATH=str(diretorio_base / "src"),
    )
    env_servidor.pop("SMTP_HOST", None)

    processo = subprocess.Popen(
        [sys.executable, "-m", "tokstance.main"],
        env=env_servidor,
        cwd=str(diretorio_base),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    pronto = False
    for _ in range(40):
        time.sleep(0.5)
        try:
            with urllib.request.urlopen(f"{url_base}/api/health", timeout=1) as resposta:
                if resposta.status == 200:
                    pronto = True
                    break
        except Exception:
            pass

    if not pronto:
        processo.terminate()
        processo.wait()
        shutil.rmtree(dados_temp, ignore_errors=True)
        raise RuntimeError("Servidor E2E nao iniciou a tempo.")

    yield url_base, codigo_convite, dados_temp

    processo.terminate()
    try:
        processo.wait(timeout=5)
    except subprocess.TimeoutExpired:
        processo.kill()
    shutil.rmtree(dados_temp, ignore_errors=True)


@pytest.fixture
def pagina_navegador() -> Iterator[Page]:
    with sync_playwright() as playwright:
        navegador: Browser = playwright.chromium.launch(
            headless=True,
            env=_obter_env_navegador(),
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        contexto = navegador.new_context(viewport={"width": 1280, "height": 850})
        pagina = contexto.new_page()
        yield pagina
        contexto.close()
        navegador.close()


@pytest.mark.e2e
def test_e2e_cadastro_login_e_ingresso_via_convite(
    servidor_e2e: Tuple[str, str, str], pagina_navegador: Page
) -> None:
    #arrange
    url_base, codigo_convite, _ = servidor_e2e
    usuario_novo = f"rotulador_{int(time.time())}"

    #act
    pagina_navegador.goto(url_base)
    pagina_navegador.wait_for_selector(".auth-card")

    pagina_navegador.get_by_role("tab", name="Criar Conta").click()
    pagina_navegador.get_by_label("Nome de Usuário").nth(1).fill(usuario_novo)
    pagina_navegador.get_by_label("E-mail (usado na recuperação de senha)").fill(f"{usuario_novo}@ufmg.br")
    pagina_navegador.get_by_label("Senha de Acesso").nth(1).fill("senhaSecreta123")
    pagina_navegador.get_by_label("Confirmar Senha").fill("senhaSecreta123")
    pagina_navegador.get_by_role("button", name="Cadastrar e Acessar").click()

    pagina_navegador.wait_for_selector(".hub-header-bar", timeout=10000)

    #open invite modal and join task
    pagina_navegador.locator(".hub-plus-btn").click()
    pagina_navegador.wait_for_selector(".modal-overlay:not(.hide)", timeout=5000)

    pagina_navegador.locator("#input_codigo_convite input, #input_codigo_convite textarea").fill(codigo_convite)
    pagina_navegador.get_by_role("button", name="Entrar na Tarefa").click()

    #assert
    pagina_navegador.wait_for_selector(".hub-table", timeout=10000)
    conteudo_tabela = pagina_navegador.locator(".hub-table").inner_text()
    assert "Detecção de Posição E2E" in conteudo_tabela
    assert "Iniciar Rotulação" in conteudo_tabela


@pytest.mark.e2e
def test_e2e_rejeicao_credenciais_invalidas_e_convite_inexistente(
    servidor_e2e: Tuple[str, str, str], pagina_navegador: Page
) -> None:
    #arrange
    url_base, _, _ = servidor_e2e

    #act invalid login
    pagina_navegador.goto(url_base)
    pagina_navegador.wait_for_selector(".auth-card")

    pagina_navegador.get_by_label("Nome de Usuário").first.fill("usuario_inexistente")
    pagina_navegador.get_by_label("Senha de Acesso").first.fill("senhaErrada123")
    pagina_navegador.get_by_role("button", name="Entrar no Sistema").click()

    #assert invalid login toast
    pagina_navegador.wait_for_selector(".tokstance-toast.toast-erro", timeout=8000)
    texto_toast = pagina_navegador.locator(".tokstance-toast").inner_text()
    assert "inválid" in texto_toast.lower() or "não encontrado" in texto_toast.lower() or "incorret" in texto_toast.lower()

    #act valid login
    pagina_navegador.get_by_label("Nome de Usuário").first.fill("coordenador_e2e")
    pagina_navegador.get_by_label("Senha de Acesso").first.fill("senhaForte123")
    pagina_navegador.get_by_role("button", name="Entrar no Sistema").click()

    pagina_navegador.wait_for_selector(".hub-header-bar", timeout=10000)

    #act invalid invite code
    pagina_navegador.locator(".hub-plus-btn").click()
    pagina_navegador.wait_for_selector(".modal-overlay:not(.hide)", timeout=5000)

    pagina_navegador.locator("#input_codigo_convite input, #input_codigo_convite textarea").fill("TOK-CODIGOINEXISTENTE")
    pagina_navegador.get_by_role("button", name="Entrar na Tarefa").click()

    #assert invalid invite code toast
    pagina_navegador.wait_for_selector(".tokstance-toast.toast-erro", timeout=8000)
    texto_erro_convite = pagina_navegador.locator(".tokstance-toast").inner_text()
    assert "encontrada" in texto_erro_convite.lower() or "inválid" in texto_erro_convite.lower()

    #act logout
    pagina_navegador.get_by_role("button", name="Cancelar").click()
    pagina_navegador.get_by_role("button", name="Encerrar Sessão").click()
    pagina_navegador.wait_for_selector(".auth-card", timeout=8000)
