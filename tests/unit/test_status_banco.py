"""Testes unitarios para o script de status e monitoramento do banco TokStance."""

from pathlib import Path
import sqlite3

import pytest

from scripts.seed_demo import povoar_banco_demonstrativo
from scripts.status_banco import (
    atualizar_painel,
    coletar_dados_banco,
    gerar_markdown,
    imprimir_terminal,
    obter_caminho_db,
)


def test_obter_caminho_db_retorna_caminho_informado(tmp_path: Path) -> None:
    db_fake = tmp_path / "meu_banco.db"
    assert obter_caminho_db(db_fake) == db_fake.resolve()


def test_coletar_dados_banco_inexistente(tmp_path: Path) -> None:
    db_inexistente = tmp_path / "fantasma.db"
    dados = coletar_dados_banco(db_inexistente)
    assert dados["status"] == "erro"
    assert "nao encontrado" in dados["mensagem"]


def test_coletar_dados_e_gerar_markdown_com_banco_povoado(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    db_teste = tmp_path / "seed_status.db"
    arquivo_md = tmp_path / "STATUS.md"

    # Arrange: popular banco demonstrativo
    povoar_banco_demonstrativo(caminho_banco=db_teste, reiniciar_tarefa_demo=True)

    # Act 1: coletar metricas
    dados = coletar_dados_banco(db_teste)
    assert dados["status"] == "sucesso"
    assert len(dados["usuarios"]) >= 5
    assert len(dados["tarefas"]) == 1

    tarefa = dados["tarefas"][0]
    assert tarefa["titulo"] == "Detecção de Posição"
    assert tarefa["codigo_convite"] == "TOK-DEMO2026"
    assert tarefa["sobreposicao_percentual"] == 50
    assert tarefa["vagas_ocupadas"] == 3
    assert tarefa["vagas_restantes"] == 1

    dist = tarefa["distribuicao"]
    assert dist["total_atribuicoes"] == 75
    assert dist["videos_distintos"] == 30
    assert dist["videos_overlap"] == 15
    assert dist["videos_exclusivos"] == 15

    # Act 2: gerar markdown
    conteudo_md = gerar_markdown(dados)
    assert "# TokStance - Painel de Monitoramento" in conteudo_md
    assert "TOK-DEMO2026" in conteudo_md
    assert "coordenador" in conteudo_md
    assert "professor" in conteudo_md

    # Act 3: atualizar arquivo
    atualizar_painel(db_teste, arquivo_md)
    assert arquivo_md.exists()
    assert len(arquivo_md.read_text(encoding="utf-8")) > 200

    # Act 4: imprimir no terminal
    imprimir_terminal(dados)
    saida = capsys.readouterr().out
    assert "TOKSTANCE - MONITORAMENTO DO BANCO DE DADOS" in saida
    assert "Detecção de Posição" in saida

