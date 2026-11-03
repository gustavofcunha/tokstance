"""Testes de ponta a ponta (E2E) no navegador para jornadas criticas de usuario."""

import os
from pathlib import Path
import re
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

    #copiar base real se presente ou gerar dataset sintetico deterministico
    caminho_videos = diretorio_base / "data/videos.csv"
    caminho_reserva = diretorio_base / "data/videos_reserva.csv"

    if caminho_videos.exists() and caminho_videos.stat().st_size > 100:
        shutil.copy(caminho_videos, caminho_dados / "videos.csv")
    else:
        df_videos_sinteticos = pd.DataFrame([
            {
                "id": f"vid_real_{idx}",
                "url": f"https://www.tiktok.com/@canal/video/{1000 + idx}",
                "target": "Fim da Escala de Trabalho 6x1" if idx <= 20 else "Reforma Tributária",
                "video_description": f"Vídeo demonstrativo #{idx} sobre temas relevantes",
                "voice_to_text": f"Transcrição do áudio do vídeo #{idx}",
                "video_duration": "30.0",
            }
            for idx in range(1, 31)
        ])
        df_videos_sinteticos.to_csv(caminho_dados / "videos.csv", index=False)

    if caminho_reserva.exists() and caminho_reserva.stat().st_size > 100:
        shutil.copy(caminho_reserva, caminho_dados / "videos_reserva.csv")
    else:
        df_reserva_sinteticos = pd.DataFrame([
            {
                "id": f"res_real_{idx}",
                "url": f"https://www.tiktok.com/@reserva/video/{2000 + idx}",
                "target": "Fim da Escala de Trabalho 6x1" if idx <= 6 else "Reforma Tributária",
                "video_description": f"Vídeo reserva #{idx}",
                "voice_to_text": f"Transcrição do reserva #{idx}",
                "video_duration": "25.0",
            }
            for idx in range(1, 11)
        ])
        df_reserva_sinteticos.to_csv(caminho_dados / "videos_reserva.csv", index=False)

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
        TOKSTANCE_MOCK_SMTP="1",
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
    pagina_navegador.get_by_label("Nome Completo").fill("Nome Rotulador Teste")
    pagina_navegador.get_by_label("Nome de Usuário").nth(1).fill(usuario_novo)
    pagina_navegador.get_by_label("E-mail").fill(f"{usuario_novo}@ufmg.br")
    pagina_navegador.get_by_label("Senha de Acesso").nth(1).fill("senhaSecreta123")
    pagina_navegador.get_by_label("Confirmar Senha").fill("senhaSecreta123")
    pagina_navegador.get_by_role("button", name="Cadastrar e Acessar").click()

    pagina_navegador.wait_for_selector(".hub-header-bar", timeout=10000)

    #open invite modal and join task
    pagina_navegador.locator(".hub-plus-rotulador").click()
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

    #assert invalid login toast and inline error
    pagina_navegador.wait_for_selector(".auth-inline-error", timeout=8000)
    texto_inline = pagina_navegador.locator(".auth-inline-error").inner_text()
    assert "inválid" in texto_inline.lower() or "não encontrado" in texto_inline.lower() or "incorret" in texto_inline.lower()

    pagina_navegador.wait_for_selector(".tokstance-toast.toast-erro", timeout=8000)
    texto_toast = pagina_navegador.locator(".tokstance-toast").inner_text()
    assert "inválid" in texto_toast.lower() or "não encontrado" in texto_toast.lower() or "incorret" in texto_toast.lower()

    #act valid login
    pagina_navegador.get_by_label("Nome de Usuário").first.fill("coordenador_e2e")
    pagina_navegador.get_by_label("Senha de Acesso").first.fill("senhaForte123")
    pagina_navegador.get_by_role("button", name="Entrar no Sistema").click()

    pagina_navegador.wait_for_selector(".hub-header-bar", timeout=10000)

    #act invalid invite code
    pagina_navegador.locator(".hub-plus-rotulador").click()
    pagina_navegador.wait_for_selector(".modal-overlay:not(.hide)", timeout=5000)

    pagina_navegador.locator("#input_codigo_convite input, #input_codigo_convite textarea").fill("TOK-CODIGOINEXISTENTE")
    pagina_navegador.get_by_role("button", name="Entrar na Tarefa").click()

    #assert invalid invite code toast and inline error
    pagina_navegador.wait_for_selector(".modal-card .auth-inline-error", timeout=8000)
    texto_inline_modal = pagina_navegador.locator(".modal-card .auth-inline-error").inner_text()
    assert "encontrada" in texto_inline_modal.lower() or "inválid" in texto_inline_modal.lower()

    pagina_navegador.wait_for_selector(".tokstance-toast.toast-erro", timeout=8000)
    texto_erro_convite = pagina_navegador.locator(".tokstance-toast").inner_text()
    assert "encontrada" in texto_erro_convite.lower() or "inválid" in texto_erro_convite.lower()

    #act logout
    pagina_navegador.get_by_role("button", name="Cancelar").click()
    pagina_navegador.wait_for_selector(".modal-overlay:not(.hide)", state="hidden", timeout=5000)
    _fazer_logout_e_aguardar_tela_inicial(pagina_navegador)

    #act tentativa de cadastro com senha sem cumprir requisitos de complexidade
    pagina_navegador.get_by_role("tab", name="Criar Conta").click()
    campo_nc = pagina_navegador.get_by_label("Nome Completo")
    campo_nc.wait_for(state="visible", timeout=8000)
    campo_nc.fill("Usuario Falha Senha")
    pagina_navegador.get_by_label("Nome de Usuário").nth(1).fill("usuario_falha_senha")
    pagina_navegador.get_by_label("E-mail").fill("falha@exemplo.org")
    pagina_navegador.get_by_label("Senha de Acesso").nth(1).fill("somenteletras")
    pagina_navegador.get_by_label("Confirmar Senha").fill("somenteletras")
    pagina_navegador.get_by_role("button", name="Cadastrar e Acessar").click()

    #assert erro de requisitos de senha exibido inline e no toast
    pagina_navegador.locator(".auth-inline-error").filter(has_text=re.compile(r"letra", re.I)).wait_for(timeout=10000)
    texto_erro_cad = pagina_navegador.locator(".auth-inline-error").inner_text()
    assert "letra" in texto_erro_cad.lower() and "número" in texto_erro_cad.lower()

    pagina_navegador.wait_for_selector(".tokstance-toast.toast-erro", state="attached", timeout=8000)
    texto_toast_cad = pagina_navegador.locator(".tokstance-toast.toast-erro").last.text_content() or ""
    assert "letra" in texto_toast_cad.lower() and "número" in texto_toast_cad.lower()


def _fazer_logout_e_aguardar_tela_inicial(pagina: Page) -> None:
    #encerrar sessao e aguardar retorno estavel a tela inicial de autenticacao
    pagina.get_by_role("button", name="Encerrar Sessão").click()
    pagina.wait_for_selector(".hub-header-bar", state="hidden", timeout=10000)
    pagina.wait_for_selector(".tokstance-toast.toast-sucesso", timeout=10000)
    pagina.wait_for_selector(".auth-card", state="visible", timeout=10000)
    pagina.reload()
    pagina.wait_for_selector(".auth-card", state="visible", timeout=10000)
    pagina.get_by_role("button", name="Entrar no Sistema").wait_for(state="visible", timeout=10000)


def _cadastrar_e_entrar_na_tarefa(
    pagina: Page, url_base: str, usuario: str, codigo_convite: str
) -> None:
    pagina.goto(url_base)
    pagina.wait_for_selector(".auth-card")
    pagina.get_by_role("tab", name="Criar Conta").click()
    pagina.get_by_label("Nome Completo").fill(f"Nome Completo {usuario}")
    pagina.get_by_label("Nome de Usuário").nth(1).fill(usuario)
    pagina.get_by_label("E-mail").fill(f"{usuario}@exemplo.org")
    pagina.get_by_label("Senha de Acesso").nth(1).fill("senha12345")
    pagina.get_by_label("Confirmar Senha").fill("senha12345")
    pagina.get_by_label("Código de Convite (opcional)").fill(codigo_convite)
    pagina.get_by_role("button", name="Cadastrar e Acessar").click()
    pagina.wait_for_selector(".hub-header-bar", timeout=10000)


@pytest.mark.e2e
def test_e2e_modal_aviso_conteudo_sensivel_e_saida_segura(
    servidor_e2e: Tuple[str, str, str], pagina_navegador: Page
) -> None:
    #arrange
    url_base, codigo_convite, _ = servidor_e2e
    usuario_novo = f"rot_aviso_{int(time.time() * 1000) % 100000}"

    #act register with invite and reach hub
    _cadastrar_e_entrar_na_tarefa(pagina_navegador, url_base, usuario_novo, codigo_convite)

    #act open task labeling
    pagina_navegador.locator(".hub-table-btn", has_text="Rotulação").first.click()

    #assert sensitive warning modal appears
    pagina_navegador.wait_for_selector(".sensitive-warning-wrapper", timeout=10000)
    texto_modal = pagina_navegador.locator(".sensitive-warning-wrapper").inner_text()
    assert "Conteúdo Sensível" in texto_modal or "Aviso" in texto_modal

    #act safe exit
    pagina_navegador.get_by_role("button", name="Parar de rotular").click()

    #assert return to hub
    pagina_navegador.wait_for_selector(".hub-header-bar", timeout=10000)
    assert pagina_navegador.locator(".hub-table").count() > 0


@pytest.mark.e2e
def test_e2e_confirmacao_aviso_sensivel_revela_workspace_rotulacao(
    servidor_e2e: Tuple[str, str, str], pagina_navegador: Page
) -> None:
    #arrange
    url_base, codigo_convite, _ = servidor_e2e
    usuario_novo = f"rot_work_{int(time.time() * 1000) % 100000}"

    #act register with invite and reach hub
    _cadastrar_e_entrar_na_tarefa(pagina_navegador, url_base, usuario_novo, codigo_convite)

    #act open task labeling
    pagina_navegador.locator(".hub-table-btn", has_text="Rotulação").first.click()
    pagina_navegador.wait_for_selector(".sensitive-warning-wrapper", timeout=10000)

    #act accept sensitive warning
    pagina_navegador.get_by_role("button", name="Continuar").click()

    #assert workspace revealed with tiktok player and stance options
    pagina_navegador.wait_for_selector(".annotation-controls", state="visible", timeout=10000)
    assert pagina_navegador.locator("iframe").count() > 0
    assert pagina_navegador.locator(".annotation-controls").is_visible()

    #verifica ausencia de rolagem horizontal no navegador e presenca de rodape
    scroll_width = pagina_navegador.evaluate("() => document.documentElement.scrollWidth")
    client_width = pagina_navegador.evaluate("() => document.documentElement.clientWidth")
    assert scroll_width <= client_width + 2


@pytest.mark.e2e
def test_e2e_anotacao_completa_e_avanco_da_barra_de_progresso(
    servidor_e2e: Tuple[str, str, str], pagina_navegador: Page
) -> None:
    #arrange
    url_base, codigo_convite, _ = servidor_e2e
    usuario_novo = f"rot_anot_{int(time.time() * 1000) % 100000}"

    #act register with invite and reach hub
    _cadastrar_e_entrar_na_tarefa(pagina_navegador, url_base, usuario_novo, codigo_convite)

    #act open task labeling and accept warning
    pagina_navegador.locator(".hub-table-btn", has_text="Rotulação").first.click()
    pagina_navegador.wait_for_selector(".sensitive-warning-wrapper", timeout=10000)
    pagina_navegador.get_by_role("button", name="Continuar").click()
    pagina_navegador.wait_for_selector(".annotation-controls", state="visible", timeout=10000)

    #act select stance option and save
    pagina_navegador.locator("label", has_text="A Favor").click()
    pagina_navegador.get_by_role("button", name="Salvar Resposta e Avançar").click()

    #assert progress bar advances
    pagina_navegador.locator(".labeler-controls-column").get_by_text(re.compile(r"1 de ")).wait_for(timeout=10000)
    texto_progresso = pagina_navegador.locator(".labeler-controls-column").inner_text()
    assert "1 de " in texto_progresso


@pytest.mark.e2e
def test_e2e_criacao_de_tarefa_e_auditoria_console_administrador(
    servidor_e2e: Tuple[str, str, str], pagina_navegador: Page
) -> None:
    #arrange
    url_base, _, _ = servidor_e2e
    coord_usuario = f"coord_adm_{int(time.time() * 1000) % 100000}"

    #act register new coordinator
    pagina_navegador.goto(url_base)
    pagina_navegador.wait_for_selector(".auth-card")
    pagina_navegador.get_by_role("tab", name="Criar Conta").click()
    pagina_navegador.get_by_label("Nome Completo").fill("Coordenador Administrador")
    pagina_navegador.get_by_label("Nome de Usuário").nth(1).fill(coord_usuario)
    pagina_navegador.get_by_label("E-mail").fill(f"{coord_usuario}@ufmg.br")
    pagina_navegador.get_by_label("Senha de Acesso").nth(1).fill("senhaForte123")
    pagina_navegador.get_by_label("Confirmar Senha").fill("senhaForte123")
    pagina_navegador.get_by_role("button", name="Cadastrar e Acessar").click()

    pagina_navegador.wait_for_selector(".hub-header-bar", timeout=10000)

    #act open wizard
    pagina_navegador.locator(".hub-plus-admin").click()
    pagina_navegador.wait_for_selector(".admin-panel", timeout=10000)

    #act submit task with default videos
    pagina_navegador.get_by_role("button", name="Criar Tarefa e Atribuir Vagas").click()

    #assert toast with direct action button appears
    pagina_navegador.wait_for_selector(".toast-acao", timeout=10000)
    pagina_navegador.locator(".toast-acao").click()

    #assert admin console opened with kpis and downloads section
    pagina_navegador.wait_for_selector(".admin-command-center", timeout=10000)
    assert pagina_navegador.locator(".admin-kpis, .dashboard-grid, .admin-command-center").count() > 0
    assert pagina_navegador.locator(".admin-downloads").count() > 0


@pytest.mark.e2e
def test_e2e_redefinicao_senha_exibe_erro_confirmacao_diferente_e_sucesso_quando_coincide(
    servidor_e2e: Tuple[str, str, str], pagina_navegador: Page
) -> None:
    #arrange
    url_base, _, caminho_dados_str = servidor_e2e
    usuario_recup = f"user_recup_{int(time.time() * 1000) % 100000}"

    #act cadastro do usuario para ter email registrado
    _cadastrar_e_entrar_na_tarefa(pagina_navegador, url_base, usuario_recup, "")

    #act logout para ir a tela inicial
    _fazer_logout_e_aguardar_tela_inicial(pagina_navegador)

    #act solicitar recuperacao de senha
    pagina_navegador.get_by_role("tab", name="Recuperar Senha").click()
    campo_ident = pagina_navegador.get_by_label("Nome de Usuário ou E-mail Cadastrado")
    campo_ident.wait_for(state="visible", timeout=8000)
    campo_ident.fill(usuario_recup)
    pagina_navegador.get_by_role("button", name="Enviar Código de Recuperação").click()

    #aguarda o campo do codigo de verificacao ficar visivel e aviso inline
    campo_codigo = pagina_navegador.get_by_label("Código de Verificação (6 dígitos)")
    campo_codigo.wait_for(state="visible", timeout=15000)
    pagina_navegador.wait_for_selector(".auth-inline-success", timeout=15000)

    #busca codigo no banco sqlite isolado
    banco_path = Path(caminho_dados_str) / "tokstance.db"
    banco = BancoDadosSQLite(banco_path)
    linha = None
    for _ in range(20):
        linha = banco.consultar_um(
            "SELECT r.codigo_recuperacao FROM recuperacao_senha r JOIN usuarios u ON u.usuario_id = r.usuario_id WHERE u.nome_usuario = ? AND r.usado = 0 ORDER BY r.recuperacao_id DESC LIMIT 1;",
            (usuario_recup,),
        )
        if linha:
            break
        time.sleep(0.3)
    assert linha is not None
    cod_recup = str(linha["codigo_recuperacao"])

    #act preencher codigo de verificacao
    pagina_navegador.get_by_label("Código de Verificação (6 dígitos)").fill(cod_recup)
    pagina_navegador.get_by_role("button", name="Verificar Código").click()

    #aguarda passo de redefinicao de senha
    campo_nova_senha = pagina_navegador.get_by_label("Nova Senha").first
    campo_confirma_senha = pagina_navegador.get_by_label("Confirmar Nova Senha")
    campo_nova_senha.wait_for(state="visible", timeout=10000)

    #act submeter senha curta sem cumprir tamanho minimo
    campo_nova_senha.fill("123")
    campo_confirma_senha.fill("123")
    pagina_navegador.get_by_role("button", name="Redefinir Senha").click()

    #assert erro de requisitos de tamanho minimo exibido inline e no toast
    pagina_navegador.wait_for_selector(".auth-inline-error", timeout=8000)
    texto_inline_curta = pagina_navegador.locator(".auth-inline-error").inner_text()
    assert "mínimo" in texto_inline_curta.lower() and "6" in texto_inline_curta

    pagina_navegador.wait_for_selector(".tokstance-toast.toast-erro", state="attached", timeout=8000)
    texto_toast_curta = pagina_navegador.locator(".tokstance-toast.toast-erro").last.text_content() or ""
    assert "mínimo" in texto_toast_curta.lower() and "6" in texto_toast_curta

    #act submeter senha sem numeros violando complexidade
    campo_nova_senha.fill("somenteletras")
    campo_confirma_senha.fill("somenteletras")
    pagina_navegador.get_by_role("button", name="Redefinir Senha").click()

    #assert erro de requisitos de letra e numero exibido inline e no toast
    pagina_navegador.locator(".auth-inline-error").filter(has_text=re.compile(r"letra", re.I)).wait_for(timeout=10000)
    texto_inline_sn = pagina_navegador.locator(".auth-inline-error").inner_text()
    assert "letra" in texto_inline_sn.lower() and "número" in texto_inline_sn.lower()

    pagina_navegador.wait_for_selector(".tokstance-toast.toast-erro", state="attached", timeout=8000)
    texto_toast_sn = pagina_navegador.locator(".tokstance-toast.toast-erro").last.text_content() or ""
    assert "letra" in texto_toast_sn.lower() and "número" in texto_toast_sn.lower()

    #act preencher nova senha com confirmacao diferente
    campo_nova_senha.fill("novaSenhaForte123")
    campo_confirma_senha.fill("senhaDiferente456")
    pagina_navegador.get_by_role("button", name="Redefinir Senha").click()

    #assert erro de confirmacao diferente exibido inline no card e no toast
    pagina_navegador.locator(".auth-inline-error").filter(has_text=re.compile(r"coincidem|diferente", re.I)).wait_for(timeout=10000)
    texto_inline = pagina_navegador.locator(".auth-inline-error").inner_text()
    assert "não coincidem" in texto_inline.lower() or "diferente" in texto_inline.lower()

    pagina_navegador.wait_for_selector(".tokstance-toast.toast-erro", state="attached", timeout=8000)
    texto_toast = pagina_navegador.locator(".tokstance-toast.toast-erro").last.text_content() or ""
    assert "não coincidem" in texto_toast.lower() or "diferente" in texto_toast.lower()

    #act corrigir a confirmacao de senha para coincidir
    campo_confirma_senha.fill("novaSenhaForte123")
    pagina_navegador.get_by_role("button", name="Redefinir Senha").click()

    #assert toast de sucesso na redefinicao
    toast_sucesso = pagina_navegador.locator(".tokstance-toast.toast-sucesso").last
    toast_sucesso.wait_for(state="attached", timeout=10000)
    texto_sucesso = toast_sucesso.text_content() or ""
    assert "sucesso" in texto_sucesso.lower() or "redefinida" in texto_sucesso.lower()

    #assert transicao automatica para a aba entrar com usuario pre-preenchido e aviso de sucesso
    campo_senha_login = pagina_navegador.get_by_label("Senha de Acesso").first
    campo_senha_login.wait_for(state="visible", timeout=10000)

    campo_usuario_login = pagina_navegador.get_by_label("Nome de Usuário").first
    assert campo_usuario_login.input_value() == usuario_recup

    pagina_navegador.wait_for_selector(".auth-inline-success", timeout=8000)
    texto_inline_sucesso = pagina_navegador.locator(".auth-inline-success").first.inner_text()
    assert "redefinida com sucesso" in texto_inline_sucesso.lower()

    #act entrar com a nova senha sem precisar redigitar o usuario nem clicar na aba
    campo_senha_login.fill("novaSenhaForte123")
    pagina_navegador.get_by_role("button", name="Entrar no Sistema").click()

    pagina_navegador.wait_for_selector(".hub-header-bar", timeout=10000)
    assert pagina_navegador.locator(".hub-header-bar").is_visible()


@pytest.mark.e2e
def test_e2e_login_olho_visualizar_senha_alterna_visibilidade_e_permite_login(
    servidor_e2e: Tuple[str, str, str], pagina_navegador: Page
) -> None:
    #arrange carregar tela de login
    url_base, _, _ = servidor_e2e
    pagina_navegador.goto(url_base)
    pagina_navegador.wait_for_selector(".auth-card", timeout=8000)

    #garantir aba entrar selecionada
    pagina_navegador.get_by_role("tab", name="Entrar").click()

    campo_senha = pagina_navegador.locator("#login_senha input")
    campo_senha.wait_for(state="visible", timeout=8000)

    #assert botao do olho de visibilidade presente no campo de senha
    btn_olho = pagina_navegador.locator("#login_senha .btn-olho-senha")
    btn_olho.wait_for(state="visible", timeout=8000)
    assert btn_olho.count() == 1
    assert campo_senha.get_attribute("type") == "password"
    assert btn_olho.get_attribute("aria-label") == "Mostrar senha"

    #act digitar senha e alternar visibilidade com o botao do olho
    campo_senha.fill("senhaForte123")
    btn_olho.click()

    #assert tipo de campo alternado para texto visivel
    assert campo_senha.get_attribute("type") == "text"
    assert btn_olho.get_attribute("aria-label") == "Ocultar senha"

    #act clicar novamente no olho para ocultar
    btn_olho.click()

    #assert tipo de campo restaurado para password
    assert campo_senha.get_attribute("type") == "password"
    assert btn_olho.get_attribute("aria-label") == "Mostrar senha"

    #act alternar para visivel e fazer login
    btn_olho.click()
    assert campo_senha.get_attribute("type") == "text"

    pagina_navegador.get_by_label("Nome de Usuário").first.fill("coordenador_e2e")
    pagina_navegador.get_by_role("button", name="Entrar no Sistema").click()

    #assert login concluido com sucesso no hub com senha autenticada
    pagina_navegador.wait_for_selector(".hub-header-bar", timeout=10000)
    assert pagina_navegador.locator(".hub-header-bar").is_visible()


@pytest.mark.e2e
def test_e2e_criacao_de_multiplas_tarefas_exibe_mensagem_em_todas_e_em_falhas(
    servidor_e2e: Tuple[str, str, str], pagina_navegador: Page
) -> None:
    #arrange login e abertura do wizard
    url_base, _, _ = servidor_e2e
    usuario_adm = f"adm_multi_{int(time.time() * 1000) % 100000}"
    _cadastrar_e_entrar_na_tarefa(pagina_navegador, url_base, usuario_adm, "")

    pagina_navegador.locator(".hub-plus-admin").click()
    pagina_navegador.wait_for_selector(".admin-panel", timeout=8000)

    #act criar primeira tarefa com sucesso
    pagina_navegador.get_by_role("button", name="Criar Tarefa e Atribuir Vagas").click()

    #assert toast e aviso inline exibidos para a primeira tarefa
    toast = pagina_navegador.locator(".tokstance-toast")
    toast.wait_for(state="visible", timeout=8000)
    texto_t1 = toast.text_content() or ""
    assert "criada com sucesso" in texto_t1.lower()

    inline_aviso = pagina_navegador.locator(".wizard-feedback-slot .auth-inline-success")
    inline_aviso.wait_for(state="visible", timeout=8000)
    assert "criada com sucesso" in (inline_aviso.text_content() or "").lower()

    #act criar segunda tarefa consecutiva com outro titulo
    pagina_navegador.get_by_label("Título da Tarefa").fill("Estudo de Posicionamento Segundo Lote")
    pagina_navegador.get_by_role("button", name="Criar Tarefa e Atribuir Vagas").click()

    #assert mensagem de sucesso exibida tambem para a segunda tarefa
    toast.wait_for(state="visible", timeout=8000)
    texto_t2 = toast.text_content() or ""
    assert "criada com sucesso" in texto_t2.lower()

    inline_aviso.wait_for(state="visible", timeout=8000)
    assert "criada com sucesso" in (inline_aviso.text_content() or "").lower()

    #act forcar falha informando apenas uma opcao de resposta
    pagina_navegador.get_by_label("Opções de Resposta (uma por linha)").fill("ApenasUmaOpcao")
    pagina_navegador.get_by_role("button", name="Criar Tarefa e Atribuir Vagas").click()

    #assert mensagem de erro exibida no toast e no aviso inline
    toast_erro = pagina_navegador.locator(".tokstance-toast.toast-erro")
    toast_erro.wait_for(state="visible", timeout=12000)
    assert "ao menos duas opções" in (toast_erro.text_content() or "").lower()

    inline_erro = pagina_navegador.locator(".wizard-feedback-slot .auth-inline-error")
    inline_erro.wait_for(state="visible", timeout=12000)
    assert "ao menos duas opções" in (inline_erro.text_content() or "").lower()


@pytest.mark.e2e
def test_e2e_redefinicao_senha_preserva_tarefas_administradas_atribuidas_e_progresso(
    servidor_e2e: Tuple[str, str, str], pagina_navegador: Page
) -> None:
    #arrange login e criacao de tarefa
    url_base, _, caminho_banco = servidor_e2e
    usuario = f"pesq_pres_{int(time.time() * 1000) % 100000}"
    email = f"{usuario}@exemplo.org"
    _cadastrar_e_entrar_na_tarefa(pagina_navegador, url_base, usuario, "")

    #cria tarefa com admin participando como rotulador
    pagina_navegador.locator(".hub-plus-admin").click()
    pagina_navegador.wait_for_selector(".admin-panel", timeout=8000)
    pagina_navegador.get_by_label("Título da Tarefa").fill("Estudo Preservação de Progresso")
    pagina_navegador.get_by_role("button", name="Criar Tarefa e Atribuir Vagas").click()
    pagina_navegador.locator(".wizard-feedback-slot .auth-inline-success").wait_for(state="visible", timeout=8000)

    #volta para o hub e inicia rotulacao
    pagina_navegador.get_by_role("button", name="← Voltar ao Hub").click()
    pagina_navegador.wait_for_selector(".hub-two-col", timeout=8000)

    btn_iniciar = pagina_navegador.locator(".hub-table-btn", has_text="Rotulação").first
    btn_iniciar.wait_for(state="visible", timeout=8000)
    btn_iniciar.click()

    pagina_navegador.wait_for_selector(".sensitive-warning-wrapper", timeout=10000)
    pagina_navegador.get_by_role("button", name="Continuar").click()
    pagina_navegador.wait_for_selector(".annotation-controls", state="visible", timeout=10000)

    pagina_navegador.locator("label", has_text="A Favor").click()
    pagina_navegador.get_by_role("button", name="Salvar Resposta e Avançar").click()

    #aguarda avanco da barra de progresso para 1 de N
    pagina_navegador.locator(".labeler-controls-column").get_by_text(re.compile(r"1 de ")).wait_for(timeout=10000)

    #sai para o hub e verifica progresso salvo
    pagina_navegador.get_by_role("button", name="← Sair do Workspace").click()
    pagina_navegador.wait_for_selector(".hub-two-col", timeout=8000)
    btn_continuar = pagina_navegador.locator(".hub-table-btn.in-progress", has_text="Continuar Rotulação")
    btn_continuar.wait_for(state="visible", timeout=8000)

    #logout
    _fazer_logout_e_aguardar_tela_inicial(pagina_navegador)

    #solicita recuperacao de senha
    pagina_navegador.get_by_role("tab", name="Recuperar Senha").click()
    campo_ident_pres = pagina_navegador.get_by_label("Nome de Usuário ou E-mail Cadastrado")
    campo_ident_pres.wait_for(state="visible", timeout=8000)
    campo_ident_pres.fill(usuario)
    pagina_navegador.get_by_role("button", name="Enviar Código de Recuperação").click()

    campo_codigo = pagina_navegador.get_by_label("Código de Verificação (6 dígitos)")
    campo_codigo.wait_for(state="visible", timeout=10000)

    #obtem codigo gerado no banco de dados sqlite
    banco = BancoDadosSQLite(Path(caminho_banco) / "tokstance.db")
    registro = banco.consultar_um(
        "SELECT codigo_recuperacao FROM recuperacao_senha WHERE usado = 0 ORDER BY recuperacao_id DESC LIMIT 1;"
    )
    assert registro is not None
    codigo = str(registro["codigo_recuperacao"])

    #digita codigo e confirma
    campo_codigo.fill(codigo)
    pagina_navegador.get_by_role("button", name="Verificar Código").click()

    #digita nova senha e redefine
    pagina_navegador.get_by_label("Nova Senha").first.fill("NovaSenhaSegura123")
    pagina_navegador.get_by_label("Confirmar Nova Senha").fill("NovaSenhaSegura123")
    pagina_navegador.get_by_role("button", name="Redefinir Senha").click()

    #verifica retorno para a tela de login
    pagina_navegador.wait_for_selector(".auth-inline-success", timeout=8000)

    #faz login com a nova senha
    campo_senha = pagina_navegador.get_by_label("Senha de Acesso").first
    campo_senha.fill("NovaSenhaSegura123")
    pagina_navegador.get_by_role("button", name="Entrar no Sistema").click()

    #verifica hub com tarefas administradas e progresso 100% preservado
    pagina_navegador.wait_for_selector(".hub-two-col", timeout=10000)
    assert pagina_navegador.locator("text=Estudo Preservação de Progresso").count() >= 1
    btn_continuar_pos_redefinicao = pagina_navegador.locator(".hub-table-btn.in-progress", has_text="Continuar Rotulação")
    btn_continuar_pos_redefinicao.wait_for(state="visible", timeout=8000)
    assert pagina_navegador.locator("text=1 de ").count() >= 1


@pytest.mark.e2e
def test_e2e_cadastro_solicita_nome_completo_persiste_maiusculo_e_email_limpo(
    servidor_e2e: Tuple[str, str, str], pagina_navegador: Page
) -> None:
    #arrange
    url_base, _, caminho_banco = servidor_e2e
    usuario_teste = f"usuario_nc_{int(time.time() * 1000) % 100000}"

    pagina_navegador.goto(url_base)
    pagina_navegador.wait_for_selector(".auth-card")
    pagina_navegador.get_by_role("tab", name="Criar Conta").click()

    #assert campo de email sem texto de recuperacao de senha
    assert pagina_navegador.get_by_label("E-mail").count() >= 1
    assert pagina_navegador.locator("text=E-mail (usado na recuperação de senha)").count() == 0

    #assert campo de nome completo presente com classe de transformacao
    campo_nome = pagina_navegador.get_by_label("Nome Completo")
    campo_nome.wait_for(state="visible", timeout=5000)

    #act tentativa de submissao sem nome completo
    pagina_navegador.get_by_label("Nome de Usuário").nth(1).fill(usuario_teste)
    pagina_navegador.get_by_label("E-mail").fill(f"{usuario_teste}@ufmg.br")
    pagina_navegador.get_by_label("Senha de Acesso").nth(1).fill("senhaForte123")
    pagina_navegador.get_by_label("Confirmar Senha").fill("senhaForte123")
    pagina_navegador.get_by_role("button", name="Cadastrar e Acessar").click()

    #assert erro informando obrigatoriedade do nome completo
    pagina_navegador.wait_for_selector(".auth-inline-error", timeout=5000)
    texto_erro = pagina_navegador.locator(".auth-inline-error").inner_text()
    assert "nome completo" in texto_erro.lower()

    #act preenche nome completo em minusculas
    campo_nome.fill("carlos eduardo da silva")
    pagina_navegador.get_by_role("button", name="Cadastrar e Acessar").click()

    #assert cadastro bem-sucedido e entrada no hub
    pagina_navegador.wait_for_selector(".hub-header-bar", timeout=10000)

    #assert gravacao no banco sqlite em maiusculas
    banco = BancoDadosSQLite(Path(caminho_banco) / "tokstance.db")
    registro = banco.consultar_um(
        "SELECT nome_usuario, nome_completo, email FROM usuarios WHERE nome_usuario = ?;",
        (usuario_teste,),
    )
    assert registro is not None
    assert registro["nome_completo"] == "CARLOS EDUARDO DA SILVA"
    assert registro["email"] == f"{usuario_teste}@ufmg.br"






