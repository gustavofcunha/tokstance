"""Testes unitarios para a camada de seguranca avancada: headers OWASP, anti-DoS, rate limiting e blindagem SQLi."""

from pathlib import Path
from typing import Any
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from tokstance.backend.repositories.database import BancoDadosSQLite
from tokstance.backend.security.middleware import (
    LimitadorRequisicoesPorIP,
    MiddlewareAntiDosLimitePayload,
    MiddlewareCabecalhosSeguranca,
    MiddlewareRateLimitIP,
)
from tokstance.backend.security.password import HASH_DUMMY_BCRYPT, verificar_senha
from tokstance.backend.security.sqli_shield import (
    detectar_tentativa_sqli,
    sanitizar_texto_seguro,
    validar_campo_seguro,
)
from tokstance.backend.services.auth_service import ServicoAutenticacao


@pytest.fixture()
def app_com_seguranca() -> FastAPI:
    """Cria aplicacao de teste montada com todos os middlewares de seguranca."""
    app = FastAPI()
    app.add_middleware(MiddlewareCabecalhosSeguranca)
    app.add_middleware(MiddlewareAntiDosLimitePayload, max_bytes=1024)  # 1 KB para testes
    limitador_ip = LimitadorRequisicoesPorIP(limite_por_minuto=5, janela_segundos=10.0)
    app.add_middleware(MiddlewareRateLimitIP, limitador=limitador_ip)

    @app.get("/ping")
    def ping() -> dict[str, str]:
        return {"msg": "pong"}

    @app.post("/echo")
    def echo(dados: dict[str, Any]) -> dict[str, Any]:
        return dados

    return app


# ==============================================================================
# 1. TESTES DE CABECALHOS DE SEGURANCA (OWASP)
# ==============================================================================

@pytest.mark.unit
def test_middleware_injeta_cabecalhos_defensivos_owasp(app_com_seguranca: FastAPI) -> None:
    cliente = TestClient(app_com_seguranca)
    resposta = cliente.get("/ping")

    assert resposta.status_code == 200
    assert resposta.headers["X-Content-Type-Options"] == "nosniff"
    assert resposta.headers["X-Frame-Options"] == "SAMEORIGIN"
    assert resposta.headers["X-XSS-Protection"] == "1; mode=block"
    assert resposta.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "camera=()" in resposta.headers["Permissions-Policy"]


@pytest.mark.unit
def test_middleware_injeta_hsts_quando_requisicao_for_https(app_com_seguranca: FastAPI) -> None:
    cliente = TestClient(app_com_seguranca)
    resposta = cliente.get("/ping", headers={"X-Forwarded-Proto": "https"})

    assert resposta.status_code == 200
    assert "Strict-Transport-Security" in resposta.headers
    assert "max-age=31536000" in resposta.headers["Strict-Transport-Security"]


# ==============================================================================
# 2. TESTES ANTI-DOS: LIMITE DE PAYLOAD
# ==============================================================================

@pytest.mark.unit
def test_middleware_rejeita_payload_acima_do_limite_com_http_413(app_com_seguranca: FastAPI) -> None:
    cliente = TestClient(app_com_seguranca)
    payload_enorme = {"campo": "X" * 2048}  # Maior que o limite de 1024 bytes

    resposta = cliente.post("/echo", json=payload_enorme)

    assert resposta.status_code == 413
    assert "excede o limite" in resposta.json()["detail"]


@pytest.mark.unit
def test_middleware_aceita_payload_dentro_do_limite(app_com_seguranca: FastAPI) -> None:
    cliente = TestClient(app_com_seguranca)
    payload_valido = {"campo": "pequeno"}

    resposta = cliente.post("/echo", json=payload_valido)

    assert resposta.status_code == 200
    assert resposta.json()["campo"] == "pequeno"


# ==============================================================================
# 3. TESTES ANTI-DOS: RATE LIMITING POR IP
# ==============================================================================

@pytest.mark.unit
def test_limitador_ip_bloqueia_apos_exceder_taxa_com_http_429() -> None:
    app = FastAPI()
    limitador = LimitadorRequisicoesPorIP(limite_por_minuto=3, janela_segundos=5.0)
    app.add_middleware(MiddlewareRateLimitIP, limitador=limitador)

    @app.get("/teste")
    def rota_teste() -> dict[str, str]:
        return {"status": "ok"}

    cliente = TestClient(app)

    # 3 requisições permitidas
    r1 = cliente.get("/teste", headers={"X-Forwarded-For": "192.168.1.50"})
    r2 = cliente.get("/teste", headers={"X-Forwarded-For": "192.168.1.50"})
    r3 = cliente.get("/teste", headers={"X-Forwarded-For": "192.168.1.50"})
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r3.status_code == 200

    # 4ª requisição bloqueada
    r4 = cliente.get("/teste", headers={"X-Forwarded-For": "192.168.1.50"})
    assert r4.status_code == 429
    assert "Limite de taxa excedido" in r4.json()["detail"]
    assert "Retry-After" in r4.headers

    # Outro IP continua funcionando normalmente
    r_outro_ip = cliente.get("/teste", headers={"X-Forwarded-For": "10.0.0.1"})
    assert r_outro_ip.status_code == 200


@pytest.mark.unit
def test_limitador_ip_expurga_historico_antigo_sem_vazamento_de_memoria() -> None:
    tempo = [100.0]
    limitador = LimitadorRequisicoesPorIP(limite_por_minuto=10, janela_segundos=1.0, relogio=lambda: tempo[0])
    limitador.registrar_e_verificar("1.1.1.1")
    assert "1.1.1.1" in limitador._historico_ip

    # Simula passagem de tempo para expurgo
    tempo[0] = 300.0
    limitador._expurgar_ips_inativos(agora=300.0)
    assert "1.1.1.1" not in limitador._historico_ip


# ==============================================================================
# 4. TESTES DE BLINDAGEM CONTRA SQL INJECTION (SQLI SHIELD)
# ==============================================================================

@pytest.mark.unit
@pytest.mark.parametrize(
    "payload_sqli",
    [
        "admin' UNION SELECT * FROM usuarios --",
        "'; DROP TABLE tarefas; --",
        "' OR '1'='1",
        "' OR 1=1 --",
        "xp_cmdshell 'whoami'",
        "'; SLEEP(5); --",
        "target' /* comentario */",
        "1; TRUNCATE TABLE usuarios",
    ],
)
def test_detectar_tentativa_sqli_identifica_vetores_de_ataque(payload_sqli: str) -> None:
    assert detectar_tentativa_sqli(payload_sqli) is True


@pytest.mark.unit
@pytest.mark.parametrize(
    "texto_legitimo",
    [
        "Fim da Escala de Trabalho 6x1",
        "Reforma Tributária e Impactos",
        "Vacinação Infantil e Saúde Pública",
        "Opção 1: Concordo totalmente com o argumento",
        "usuario_valido-2026",
    ],
)
def test_detectar_tentativa_sqli_permite_textos_legitimos(texto_legitimo: str) -> None:
    assert detectar_tentativa_sqli(texto_legitimo) is False


@pytest.mark.unit
def test_sanitizar_texto_seguro_remove_bytes_nulos_e_caracteres_de_controle() -> None:
    with pytest.raises(ValueError, match="caracteres nulos inválidos"):
        sanitizar_texto_seguro("texto\x00injetado")

    # Caracteres de controle invisíveis são filtrados
    texto_com_controle = "texto\x01\x02\x03limpo"
    assert sanitizar_texto_seguro(texto_com_controle) == "textolimpo"


@pytest.mark.unit
def test_validar_campo_seguro_bloqueia_sqli_em_campos_estruturados() -> None:
    with pytest.raises(ValueError, match="padrões não permitidos por segurança"):
        validar_campo_seguro("admin' OR '1'='1", nome_campo="identificador", bloquear_sqli=True)


# ==============================================================================
# 5. TESTES DE DEFESA EM PROFUNDIDADE NO BANCO SQLITE
# ==============================================================================

@pytest.mark.unit
def test_banco_dados_sqlite_rejeita_inconsistencia_de_placeholders(tmp_path: Path) -> None:
    banco = BancoDadosSQLite(tmp_path / "sqli_defense.db")

    # Dois '?', mas apenas um parâmetro passado
    with pytest.raises(ValueError, match="Inconsistência de parâmetros SQL"):
        banco.consultar_um("SELECT * FROM usuarios WHERE usuario_id = ? AND nome_usuario = ?", (1,))

    # Um '?', mas nenhum parâmetro passado
    with pytest.raises(ValueError, match="Inconsistência de parâmetros SQL"):
        banco.executar("DELETE FROM tarefas WHERE tarefa_id = ?", ())


@pytest.mark.unit
def test_banco_dados_sqlite_rejeita_byte_nulo_na_query(tmp_path: Path) -> None:
    banco = BancoDadosSQLite(tmp_path / "sqli_null.db")
    with pytest.raises(ValueError, match="byte nulo"):
        banco.executar("SELECT 1\x00 FROM usuarios")


# ==============================================================================
# 6. TESTES DE MITIGACAO DE TIMING ATTACK E BRUTE-FORCE NA AUTENTICACAO
# ==============================================================================

@pytest.mark.unit
def test_autenticacao_executa_hash_dummy_em_usuario_inexistente(tmp_path: Path) -> None:
    banco = BancoDadosSQLite(tmp_path / "auth_timing.db")
    servico = ServicoAutenticacao(banco=banco)

    with patch("tokstance.backend.services.auth_service.verificar_senha") as mock_verificar:
        mock_verificar.return_value = False
        with pytest.raises(ValueError, match="usuário não encontrado"):
            servico.autenticar_usuario("usuario_que_nunca_existiu", "SenhaErrada123")

        # Garante que verificar_senha foi chamado com HASH_DUMMY_BCRYPT para tempo constante
        mock_verificar.assert_called_once_with("SenhaErrada123", HASH_DUMMY_BCRYPT)


@pytest.mark.unit
def test_verificar_codigo_recuperacao_bloqueia_forca_bruta_apos_cinco_erros(tmp_path: Path) -> None:
    banco = BancoDadosSQLite(tmp_path / "bruteforce_recup.db")
    servico = ServicoAutenticacao(banco=banco, rodadas_bcrypt=4)
    servico.cadastrar_usuario("usuario_alvo", "SenhaForte123", email="alvo@ufmg.br")
    servico.solicitar_recuperacao_senha("usuario_alvo")

    # 4 tentativas incorretas consecutivas
    for _ in range(4):
        with pytest.raises(ValueError, match="Código de recuperação inválido"):
            servico.verificar_codigo_recuperacao("usuario_alvo", "000000")

    # 5ª tentativa atinge o bloqueio
    with pytest.raises(PermissionError, match="Muitas tentativas incorretas"):
        servico.verificar_codigo_recuperacao("usuario_alvo", "000000")

    # 6ª tentativa continua bloqueada sem testar o código
    with pytest.raises(PermissionError, match="Muitas tentativas incorretas"):
        servico.verificar_codigo_recuperacao("usuario_alvo", "000000")
