"""Testes unitarios para limitador de tentativas, sessao simultanea, imunidade a SQL Injection e limites anti-DoS."""

from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from tokstance.backend.repositories.database import BancoDadosSQLite
from tokstance.backend.repositories.study_repo import RepositorioEstudo
from tokstance.backend.repositories.user_repo import RepositorioUsuarios
from tokstance.backend.security.password import gerar_hash_senha
from tokstance.backend.security.rate_limit import (
    GerenciadorSessoesAtivas,
    LimitadorTentativas,
    limpar_sessoes_ativas,
    listar_usuarios_ativos,
    liberar_sessao_ativa,
    reivindicar_sessao_ativa,
    usuario_esta_ativo,
)
from tokstance.backend.security.validators import validar_tamanho_texto


@pytest.mark.unit
def test_limitador_tentativas_bloqueia_apos_cinco_falhas_consecutivas(
    relogio_deterministico: Any,
) -> None:
    limitador = LimitadorTentativas(
        max_tentativas=5,
        segundos_bloqueio=60.0,
        relogio=relogio_deterministico.monotonico,
    )

    falha_1 = limitador.registrar_falha("ana")
    falha_2 = limitador.registrar_falha("ana")
    falha_3 = limitador.registrar_falha("ana")
    falha_4 = limitador.registrar_falha("ana")
    falha_5 = limitador.registrar_falha("ana")

    assert falha_1 is False
    assert falha_2 is False
    assert falha_3 is False
    assert falha_4 is False
    assert falha_5 is True
    assert limitador.esta_bloqueado("ana") is True
    assert limitador.segundos_restantes_bloqueio("ana") == 60.0


@pytest.mark.unit
def test_limitador_tentativas_libera_usuario_apos_expirar_janela_bloqueio(
    relogio_deterministico: Any,
) -> None:
    limitador = LimitadorTentativas(
        max_tentativas=3,
        segundos_bloqueio=45.0,
        relogio=relogio_deterministico.monotonico,
    )
    limitador.registrar_falha("bruno")
    limitador.registrar_falha("bruno")
    limitador.registrar_falha("bruno")

    relogio_deterministico.avancar(20.0)
    restante_no_meio = limitador.segundos_restantes_bloqueio("bruno")
    relogio_deterministico.avancar(26.0)
    bloqueado_apos_janela = limitador.esta_bloqueado("bruno")

    assert restante_no_meio == 25.0
    assert bloqueado_apos_janela is False
    assert limitador.segundos_restantes_bloqueio("bruno") == 0.0


@pytest.mark.unit
def test_limitador_tentativas_isola_contador_entre_usuarios_distintos(
    relogio_deterministico: Any,
) -> None:
    limitador = LimitadorTentativas(
        max_tentativas=2,
        segundos_bloqueio=30.0,
        relogio=relogio_deterministico.monotonico,
    )

    limitador.registrar_falha("carla")
    limitador.registrar_falha("carla")
    falha_diego = limitador.registrar_falha("diego")

    assert limitador.esta_bloqueado("carla") is True
    assert falha_diego is False
    assert limitador.esta_bloqueado("diego") is False


@pytest.mark.unit
def test_limitador_tentativas_limpa_historico_apos_sucesso_de_login(
    relogio_deterministico: Any,
) -> None:
    limitador = LimitadorTentativas(
        max_tentativas=3,
        segundos_bloqueio=60.0,
        relogio=relogio_deterministico.monotonico,
    )
    limitador.registrar_falha("elena")
    limitador.registrar_falha("elena")

    limitador.registrar_sucesso("elena")
    nova_falha = limitador.registrar_falha("elena")

    assert nova_falha is False
    assert limitador.esta_bloqueado("elena") is False


@pytest.mark.unit
def test_gerenciador_sessoes_ativas_impede_login_simultaneo_na_mesma_conta() -> None:
    gerenciador = GerenciadorSessoesAtivas()

    primeira_sessao = gerenciador.reivindicar_sessao("fabio")
    segunda_sessao_simultanea = gerenciador.reivindicar_sessao("fabio")
    sessao_outro_usuario = gerenciador.reivindicar_sessao("gabriela")

    assert primeira_sessao is True
    assert segunda_sessao_simultanea is False
    assert sessao_outro_usuario is True
    assert gerenciador.listar_ativos() == ["fabio", "gabriela"]


@pytest.mark.unit
def test_funcoes_globais_sessao_ativa_permitem_reivindicar_apos_liberacao() -> None:
    limpar_sessoes_ativas()

    reivindicou_antes = reivindicar_sessao_ativa("helena")
    ativo_durante = usuario_esta_ativo("helena")
    liberar_sessao_ativa("helena")
    ativo_apos_liberar = usuario_esta_ativo("helena")
    reivindicou_novamente = reivindicar_sessao_ativa("helena")
    usuarios_finais = listar_usuarios_ativos()
    limpar_sessoes_ativas()

    assert reivindicou_antes is True
    assert ativo_durante is True
    assert ativo_apos_liberar is False
    assert reivindicou_novamente is True
    assert usuarios_finais == ["helena"]


@pytest.mark.unit
def test_busca_usuario_e_cadastro_bloqueiam_injecao_sql_booleana(
    tmp_path: Path,
) -> None:
    banco = BancoDadosSQLite(tmp_path / "seguranca_sqli.db")
    repo_usuarios = RepositorioUsuarios(banco)
    repo_usuarios.criar_usuario("admin_real", gerar_hash_senha("Senha123", rodadas=4))

    resultado_busca = repo_usuarios.buscar_por_nome_usuario("admin_real' OR '1'='1")

    assert resultado_busca is None
    with pytest.raises(ValueError, match="apenas letras, números"):
        repo_usuarios.criar_usuario("hacker' OR '1'='1", gerar_hash_senha("Senha123", rodadas=4))


@pytest.mark.unit
def test_consulta_e_criacao_tarefa_neutralizam_payload_drop_table_usuarios(
    tmp_path: Path,
) -> None:
    banco = BancoDadosSQLite(tmp_path / "seguranca_drop.db")
    repo_usuarios = RepositorioUsuarios(banco)
    repo_estudo = RepositorioEstudo(banco, repo_usuarios)
    criador = repo_usuarios.criar_usuario("criador_seguro", gerar_hash_senha("Senha123", rodadas=4))
    pool = pd.DataFrame(
        [
            {
                "id": "71001",
                "url": "https://www.tiktok.com/@u/video/71001",
                "target": "Clima'; DROP TABLE usuarios; --",
            }
        ]
    )

    tarefa = repo_estudo.criar_tarefa(
        criado_por_usuario_id=criador["usuario_id"],
        pool_videos=pool,
        titulo="Estudo'; DROP TABLE usuarios; --",
        pergunta="Pergunta'; DROP TABLE tarefas; --",
    )
    usuarios_restantes = repo_usuarios.listar_usuarios()

    assert tarefa["titulo"] == "Estudo'; DROP TABLE usuarios; --"
    assert len(usuarios_restantes) == 1
    assert "usuarios" in banco.listar_tabelas()


@pytest.mark.unit
def test_busca_por_codigo_convite_neutraliza_injecao_union_select(
    tmp_path: Path,
) -> None:
    banco = BancoDadosSQLite(tmp_path / "seguranca_union.db")
    repo_usuarios = RepositorioUsuarios(banco)
    repo_estudo = RepositorioEstudo(banco, repo_usuarios)
    criador = repo_usuarios.criar_usuario("gestor_tarefa", gerar_hash_senha("Senha123", rodadas=4))
    pool = pd.DataFrame(
        [{"id": "71002", "url": "https://www.tiktok.com/@u/video/71002", "target": "Economia"}]
    )
    repo_estudo.criar_tarefa(
        criado_por_usuario_id=criador["usuario_id"],
        pool_videos=pool,
        codigo_convite="TOK-SEGURO1",
    )

    encontrada = repo_estudo.buscar_tarefa_por_codigo_convite(
        "TOK-SEGURO1' UNION SELECT * FROM tarefas --"
    )

    assert encontrada is None


@pytest.mark.unit
def test_registro_anotacao_parametrizado_preserva_integridade_contra_injecao_sql(
    tmp_path: Path,
) -> None:
    banco = BancoDadosSQLite(tmp_path / "seguranca_anotacao.db")
    repo_usuarios = RepositorioUsuarios(banco)
    repo_estudo = RepositorioEstudo(banco, repo_usuarios)
    usuario = repo_usuarios.criar_usuario("rotulador_01", gerar_hash_senha("Senha123", rodadas=4))
    pool = pd.DataFrame(
        [{"id": "71003", "url": "https://www.tiktok.com/@u/video/71003", "target": "Saúde"}]
    )
    tarefa = repo_estudo.criar_tarefa(
        criado_por_usuario_id=usuario["usuario_id"],
        pool_videos=pool,
    )

    anotacao = repo_estudo.registrar_anotacao(
        tarefa_id=tarefa["tarefa_id"],
        assignment_id="v1:rotulador_01:71003'; DELETE FROM anotacoes; --",
        rotulador="rotulador_01",
        video_id="71003",
        url="https://www.tiktok.com/@u/video/71003",
        target="Saúde'; DROP TABLE anotacoes; --",
        posicao="Contra",
        tempo_analise_segundos=12.5,
    )
    quadro = repo_estudo.carregar_anotacoes_tarefa_df(tarefa["tarefa_id"])

    assert anotacao["stance"] == "Contra"
    assert len(quadro) == 1


@pytest.mark.unit
def test_validar_tamanho_texto_rejeita_payload_gigantesco_anti_dos() -> None:
    payload_gigante = "A" * 10000

    with pytest.raises(ValueError, match="excede o limite"):
        validar_tamanho_texto(payload_gigante, nome_campo="comentario", tamanho_maximo=512)


@pytest.mark.unit
def test_validar_tamanho_texto_rejeita_caractere_nulo_embutido() -> None:
    payload_com_nulo = "texto_valido\x00injetado"

    with pytest.raises(ValueError, match="caracteres inválidos"):
        validar_tamanho_texto(payload_com_nulo, nome_campo="pergunta")
