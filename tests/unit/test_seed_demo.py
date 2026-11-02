"""Testes do script de povoamento com dados demonstrativos para avaliacao."""

from pathlib import Path

import pytest

from scripts.seed_demo import povoar_banco_demonstrativo
from tokstance.backend.repositories.database import BancoDadosSQLite
from tokstance.backend.repositories.study_repo import RepositorioEstudo


def test_seed_demo_popula_banco_e_cria_tarefa_demonstrativa(tmp_path: Path) -> None:
    #arrange
    caminho_db = tmp_path / "seed_teste.db"

    #act
    resultado = povoar_banco_demonstrativo(caminho_banco=caminho_db, reiniciar_tarefa_demo=True)

    #assert
    assert resultado["status"] == "sucesso"
    assert resultado["codigo_convite"] == "TOK-DEMO2026"
    assert "coordenador" in resultado["usuarios"]
    assert "professor" in resultado["usuarios"]

    banco = BancoDadosSQLite(caminho_db)
    repo = RepositorioEstudo(banco)
    tarefas = repo.listar_tarefas()
    assert len(tarefas) == 1
    assert tarefas[0]["titulo"] == "Detecção de Posição"

    #assert data populated
    total_anotacoes = banco.consultar_um("SELECT count(*) as total FROM anotacoes")
    assert total_anotacoes is not None and total_anotacoes["total"] > 0

    total_erros = banco.consultar_um("SELECT count(*) as total FROM erros_videos")
    assert total_erros is not None and total_erros["total"] > 0

    total_logs = banco.consultar_um("SELECT count(*) as total FROM logs_acesso")
    assert total_logs is not None and total_logs["total"] > 0
