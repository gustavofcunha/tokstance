"""Testes unitarios para as rotas REST do backend FastAPI e metodos de servico de autenticacao."""

from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from fastapi import FastAPI
import pandas as pd
import pytest

from tokstance.backend.api.routes import roteador_api
from tokstance.backend.repositories.database import BancoDadosSQLite
from tokstance.backend.services.admin_service import ServicoAdministracao
from tokstance.backend.services.auth_service import ServicoAutenticacao


@pytest.fixture()
def cliente_api(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    app = FastAPI()
    app.include_router(roteador_api)
    caminho_db = tmp_path / "api_test.db"
    monkeypatch.setenv("TOKSTANCE_DATA_DIR", str(tmp_path))
    return TestClient(app)


@pytest.mark.unit
def test_rota_health_retorna_status_ok_e_tabelas_conectadas(cliente_api: TestClient) -> None:
    resposta = cliente_api.get("/api/health")

    assert resposta.status_code == 200
    dados = resposta.json()
    assert dados["status"] == "ok"
    assert dados["banco"] == "conectado"
    assert dados["tabelas_disponiveis"] >= 8


@pytest.mark.unit
def test_rota_summary_retorna_lista_de_tarefas_cadastradas(
    cliente_api: TestClient, tmp_path: Path
) -> None:
    banco = BancoDadosSQLite(tmp_path / "tokstance.db")
    servico_auth = ServicoAutenticacao(banco=banco, rodadas_bcrypt=4)
    admin = servico_auth.cadastrar_usuario("admin_api", "SenhaForte123")
    servico_admin = ServicoAdministracao(banco=banco)
    pool = pd.DataFrame([{"id": "1", "url": "http://v/1", "target": "Alvo"}])
    tarefa = servico_admin.criar_nova_tarefa(
        usuario_administrador_id=admin["usuario_id"],
        pool_videos=pool,
        titulo="Tarefa API Teste",
    )

    resposta_todas = cliente_api.get("/api/summary")
    resposta_unica = cliente_api.get(f"/api/summary?tarefa_id={tarefa['tarefa_id']}")
    resposta_inexistente = cliente_api.get("/api/summary?tarefa_id=99999")

    assert resposta_todas.status_code == 200
    assert resposta_todas.json()["total_tarefas"] >= 1

    assert resposta_unica.status_code == 200
    assert resposta_unica.json()["titulo"] == "Tarefa API Teste"

    assert resposta_inexistente.status_code == 404


@pytest.mark.unit
def test_garantir_conta_admin_padrao_cria_e_reaproveita_usuario(tmp_path: Path) -> None:
    banco = BancoDadosSQLite(tmp_path / "admin_padrao.db")
    servico_auth = ServicoAutenticacao(banco=banco, rodadas_bcrypt=4)

    admin_1 = servico_auth.garantir_conta_admin_padrao()
    admin_2 = servico_auth.garantir_conta_admin_padrao()

    assert admin_1["usuario_id"] == admin_2["usuario_id"]
    assert admin_1["nome_usuario"] == "admin"


@pytest.mark.unit
def test_autenticar_usuario_sucesso_falha_e_sessao_simultanea(tmp_path: Path) -> None:
    banco = BancoDadosSQLite(tmp_path / "auth_flows.db")
    servico_auth = ServicoAutenticacao(banco=banco, rodadas_bcrypt=4)
    servico_auth.cadastrar_usuario("user_auth", "SenhaValida123")

    with pytest.raises(ValueError, match="Informe o nome de usuário"):
        servico_auth.autenticar_usuario("", "SenhaValida123")

    with pytest.raises(ValueError, match="Credenciais inválidas"):
        servico_auth.autenticar_usuario("user_auth", "SenhaIncorreta")

    sessao = servico_auth.autenticar_usuario("user_auth", "SenhaValida123")
    assert sessao["nome_usuario"] == "user_auth"

    with pytest.raises(RuntimeError, match="já possui uma sessão ativa"):
        servico_auth.autenticar_usuario("user_auth", "SenhaValida123")

    servico_auth.encerrar_sessao("user_auth")
    sessao_nova = servico_auth.autenticar_usuario("user_auth", "SenhaValida123")
    assert sessao_nova["nome_usuario"] == "user_auth"


@pytest.mark.unit
def test_criar_aplicacao_monta_gradio_e_fastapi() -> None:
    """Valida a criacao da aplicacao acoplando FastAPI e Gradio na raiz."""
    from tokstance.main import criar_aplicacao
    app_montada = criar_aplicacao()
    cliente = TestClient(app_montada)

    res_saude = cliente.get("/api/health")
    assert res_saude.status_code == 200
    assert res_saude.json()["status"] == "ok"

    res_raiz = cliente.get("/")
    assert res_raiz.status_code == 200
