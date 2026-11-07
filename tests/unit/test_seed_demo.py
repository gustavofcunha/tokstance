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
    assert "professor" in resultado["usuarios"]
    assert "rotulador_1" in resultado["usuarios"]

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


def test_seed_demo_remove_usuarios_extras_e_preserva_apenas_demo_e_gustavo(tmp_path: Path) -> None:
    caminho_db = tmp_path / "seed_limpeza.db"
    banco = BancoDadosSQLite(caminho_db)
    banco.inicializar_esquema()

    # Cria usuario extra qualquer (ex: intruso ou avaliador que se cadastrou)
    banco.executar(
        "INSERT INTO usuarios (nome_usuario, senha_hash, email, nome_completo, criado_em) VALUES (?, ?, ?, ?, ?)",
        ("usuario_intruso", "hash_fake", "intruso@teste.com", "Usuario Intruso", "2026-01-01 00:00:00"),
    )
    banco.executar(
        "INSERT INTO usuarios (nome_usuario, senha_hash, email, nome_completo, criado_em) VALUES (?, ?, ?, ?, ?)",
        ("outro_avaliador", "hash_fake", "outro@teste.com", "Outro Avaliador", "2026-01-01 00:00:00"),
    )

    # Executa o povoamento demonstrativo
    resultado = povoar_banco_demonstrativo(caminho_banco=caminho_db, reiniciar_tarefa_demo=True)
    assert resultado["status"] == "sucesso"

    # Verifica que apenas os 4 usuarios permitidos existem
    usuarios = banco.consultar_todos("SELECT nome_usuario FROM usuarios ORDER BY nome_usuario")
    nomes = [u["nome_usuario"] for u in usuarios]
    assert nomes == ["gustavo", "professor", "rotulador_1", "rotulador_2"]
    assert "usuario_intruso" not in nomes
    assert "outro_avaliador" not in nomes

    # Verifica que a lista de usuarios limpos foi registrada no resultado
    limpos = [u["nome_usuario"] for u in resultado["usuarios_limpos"]]
    assert "usuario_intruso" in limpos
    assert "outro_avaliador" in limpos


def test_seed_demo_remove_tarefas_extras_e_imprime_no_terminal(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    from scripts.seed_demo import main
    import sys

    caminho_db = tmp_path / "seed_cli.db"
    banco = BancoDadosSQLite(caminho_db)
    banco.inicializar_esquema()

    # Cria usuario extra e tarefa extra
    banco.executar(
        "INSERT INTO usuarios (nome_usuario, senha_hash, email, nome_completo, criado_em) VALUES (?, ?, ?, ?, ?)",
        ("usuario_antigo", "hash", "antigo@exemplo.com", "Usuario Antigo", "2026-01-01 00:00:00"),
    )
    u_extra = banco.consultar_um("SELECT usuario_id FROM usuarios WHERE nome_usuario = 'usuario_antigo'")
    assert u_extra is not None
    uid = u_extra["usuario_id"]

    banco.executar(
        "INSERT INTO tarefas (slug_tarefa, titulo, pergunta, opcoes_json, distancias_rotulos_json, codigo_convite, criado_por_usuario_id, criado_em) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ("tarefa-legada", "Tarefa Legada do Usuário", "Pergunta?", "[]", "{}", "TOK-OLD1", uid, "2026-01-01 00:00:00"),
    )

    # Executa a funcao main via CLI simulado
    monkeypatch.setattr(sys, "argv", ["seed_demo.py", "--db-path", str(caminho_db)])
    main()

    saida = capsys.readouterr().out
    assert "Usuários limpos/removidos (1):" in saida
    assert "usuario_antigo" in saida
    assert "Tarefas limpas/removidas" in saida
    assert "Tarefa Legada do Usuário" in saida
