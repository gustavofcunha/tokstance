"""Testes unitários para diretrizes rigorosas de persistência, diário de emergência (zero-perda) e recuperação de falhas."""

import concurrent.futures
import json
import os
from pathlib import Path
import sqlite3
import time

import pandas as pd
import pytest

from tokstance.backend.repositories.database import BancoDadosSQLite
from tokstance.backend.repositories.persistence_vault import DiarioAnotacoesPersistencia
from tokstance.backend.repositories.study_repo import RepositorioEstudo
from tokstance.backend.repositories.user_repo import RepositorioUsuarios
from tokstance.backend.services.auth_service import ServicoAutenticacao
from tokstance.backend.services.queue_service import ServicoFilaAnotacao


@pytest.mark.unit
def test_diario_anotacoes_grava_pendente_com_fsync_e_checksum(tmp_path: Path) -> None:
    caminho_j = tmp_path / "teste_journal.jsonl"
    diario = DiarioAnotacoesPersistencia(caminho_j)

    dados = {
        "tarefa_id": 1,
        "assignment_id": "ASG-001",
        "labeler": "rotulador_1",
        "video_id": "VID-101",
        "url": "https://www.tiktok.com/@u/video/101",
        "target": "Saúde",
        "stance": "A Favor",
        "tempo_analise_segundos": 14.5,
        "video_duration": "20.0",
        "usuario_id": 42,
        "timestamp": "2026-11-07 10:00:00",
    }

    reg = diario.registrar_pendente(dados)

    assert caminho_j.exists()
    assert reg["status"] == "pendente"
    assert len(reg["checksum"]) == 64

    consol = diario.ler_registros_consolidados()
    assert "1:ASG-001" in consol
    assert consol["1:ASG-001"]["status"] == "pendente"

    pendentes = diario.obter_pendentes()
    assert len(pendentes) == 1
    assert pendentes[0]["assignment_id"] == "ASG-001"


@pytest.mark.unit
def test_diario_anotacoes_ack_e_sincronizacao(tmp_path: Path) -> None:
    caminho_j = tmp_path / "ack_journal.jsonl"
    diario = DiarioAnotacoesPersistencia(caminho_j)

    dados = {
        "tarefa_id": 2,
        "assignment_id": "ASG-002",
        "labeler": "rotulador_2",
        "video_id": "VID-102",
        "url": "https://www.tiktok.com/@u/video/102",
        "target": "Economia",
        "stance": "Contra",
        "tempo_analise_segundos": 8.0,
        "timestamp": "2026-11-07 10:05:00",
    }

    diario.registrar_pendente(dados)
    assert len(diario.obter_pendentes()) == 1

    diario.marcar_sincronizado(2, "ASG-002")

    consol = diario.ler_registros_consolidados()
    assert consol["2:ASG-002"]["status"] == "sincronizado"
    assert len(diario.obter_pendentes()) == 0


@pytest.mark.unit
def test_zero_loss_recuperacao_apos_falha_sqlite(tmp_path: Path) -> None:
    caminho_db = tmp_path / "falha_recuperacao.db"
    banco = BancoDadosSQLite(caminho_db)
    diario = banco.diario_anotacoes

    # Prepara cenario minimo de tarefa
    repo_u = RepositorioUsuarios(banco)
    repo_e = RepositorioEstudo(banco, repo_u)
    u = repo_u.criar_usuario("user_teste", "hash123")
    pool = pd.DataFrame([
        {
            "id": "V-10",
            "url": "https://www.tiktok.com/@u/video/10",
            "target": "Tema",
            "video_description": "",
            "voice_to_text": "",
            "video_duration": "10.0",
        }
    ])
    t = repo_e.criar_tarefa(
        criado_por_usuario_id=u["usuario_id"],
        pool_videos=pool,
        quantidade_videos_principal=1,
        numero_vagas=1,
    )

    # Simula anotação salva apenas no diário como pendente (falha simulada no SQLite)
    diario.registrar_pendente({
        "tarefa_id": t["tarefa_id"],
        "assignment_id": "ASG-SIMULADO",
        "usuario_id": u["usuario_id"],
        "labeler": "user_teste",
        "video_id": "V-10",
        "url": "https://www.tiktok.com/@u/video/10",
        "target": "Tema",
        "stance": "A Favor",
        "tempo_analise_segundos": 12.0,
        "video_duration": "10.0",
        "timestamp": "2026-11-07 10:10:00",
    })

    # O SQLite ainda não tem a anotação
    antes = banco.consultar_um("SELECT * FROM anotacoes WHERE assignment_id = ?", ("ASG-SIMULADO",))
    assert antes is None
    assert len(diario.obter_pendentes()) == 1

    # Executa a recuperação/sincronização
    sincronizados = diario.sincronizar_com_banco(banco)
    assert sincronizados == 1

    # Anotação agora está persistida com integridade no SQLite
    depois = banco.consultar_um("SELECT * FROM anotacoes WHERE assignment_id = ?", ("ASG-SIMULADO",))
    assert depois is not None
    assert depois["stance"] == "A Favor"
    assert len(diario.obter_pendentes()) == 0


@pytest.mark.unit
def test_reconstrucao_total_banco_a_partir_do_diario(tmp_path: Path) -> None:
    caminho_db_1 = tmp_path / "origem.db"
    banco_1 = BancoDadosSQLite(caminho_db_1)
    diario = banco_1.diario_anotacoes

    for i in range(1, 6):
        diario.registrar_pendente({
            "tarefa_id": 10,
            "assignment_id": f"ASG-{i}",
            "usuario_id": 1,
            "labeler": "rotulador_reconstroi",
            "video_id": f"VID-{i}",
            "url": f"https://www.tiktok.com/@u/video/{i}",
            "target": "Meta",
            "stance": "A Favor" if i % 2 == 0 else "Contra",
            "tempo_analise_segundos": 10.0 + i,
            "timestamp": "2026-11-07 10:15:00",
        })

    # Banco novo limpo
    caminho_db_novo = tmp_path / "novo_limpo.db"
    banco_novo = BancoDadosSQLite(caminho_db_novo)

    assert len(banco_novo.consultar_todos("SELECT * FROM anotacoes;")) == 0

    reconstruidos = diario.reconstruir_banco(banco_novo, tarefa_id=10)
    assert reconstruidos == 5

    linhas = banco_novo.consultar_todos("SELECT * FROM anotacoes WHERE tarefa_id = 10;")
    assert len(linhas) == 5


@pytest.mark.unit
def test_verificar_integridade_sqlite_detecta_wal_e_chaves_estrangeiras(tmp_path: Path) -> None:
    caminho_db = tmp_path / "integridade.db"
    banco = BancoDadosSQLite(caminho_db)

    relatorio = banco.verificar_integridade()
    assert relatorio["status"] == "ok"
    assert relatorio["quick_check"] == "ok"
    assert relatorio["integrity_check"] == "ok"
    assert relatorio["journal_mode"].upper() == "WAL"
    assert relatorio["foreign_keys_erros"] == []


@pytest.mark.unit
def test_backup_e_restauracao_online_sqlite_com_rotatividade(tmp_path: Path) -> None:
    caminho_db = tmp_path / "backup_origem.db"
    banco = BancoDadosSQLite(caminho_db)
    banco.executar(
        "INSERT INTO usuarios (nome_usuario, senha_hash, criado_em) VALUES (?, ?, ?);",
        ("usuario_bkp", "hash123", "2026-11-07"),
    )

    # Cria backups sucessivos com rotatividade máxima de 2
    b1 = banco.fazer_backup(manter_ultimos=2)
    time.sleep(0.02)
    b2 = banco.fazer_backup(manter_ultimos=2)
    time.sleep(0.02)
    b3 = banco.fazer_backup(manter_ultimos=2)

    pasta_bkp = tmp_path / "backups"
    backups_restantes = list(pasta_bkp.glob("tokstance_backup_*.db"))
    assert len(backups_restantes) <= 2
    assert b3.exists()

    # Modifica o banco ativo
    banco.executar("DELETE FROM usuarios WHERE nome_usuario = ?;", ("usuario_bkp",))
    assert banco.consultar_um("SELECT * FROM usuarios WHERE nome_usuario = 'usuario_bkp'") is None

    # Restaura a partir de b3
    banco.restaurar_backup(b3)
    restaurado = banco.consultar_um("SELECT * FROM usuarios WHERE nome_usuario = 'usuario_bkp'")
    assert restaurado is not None
    assert restaurado["nome_usuario"] == "usuario_bkp"


@pytest.mark.unit
def test_concorrencia_wal_e_retry_em_lock_simultaneo(tmp_path: Path) -> None:
    caminho_db = tmp_path / "concorrencia.db"
    banco = BancoDadosSQLite(caminho_db)

    def gravar_usuario(i: int) -> int:
        return banco.executar(
            "INSERT INTO usuarios (nome_usuario, senha_hash, criado_em) VALUES (?, ?, ?);",
            (f"conc_user_{i}", "hash", "2026-11-07"),
        )

    # Executa 20 gravações concorrentes via ThreadPool
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        resultados = list(executor.map(gravar_usuario, range(20)))

    assert len(resultados) == 20
    total = banco.consultar_um("SELECT count(*) AS total FROM usuarios;")
    assert total["total"] == 20


@pytest.mark.unit
def test_fluxo_completo_rotulacao_com_resiliencia_zero_perda(tmp_path: Path) -> None:
    caminho_db = tmp_path / "workflow_resiliente.db"
    banco = BancoDadosSQLite(caminho_db)
    servico_auth = ServicoAutenticacao(banco=banco, rodadas_bcrypt=4)
    servico_fila = ServicoFilaAnotacao(banco=banco)

    user = servico_auth.cadastrar_usuario("rotulador_resiliente", "SenhaForte123")
    pool = pd.DataFrame([
        {
            "id": "VID-R1",
            "url": "https://www.tiktok.com/@u/video/r1",
            "target": "Meio Ambiente",
            "video_description": "Desmatamento zero",
            "voice_to_text": "Audio R1",
            "video_duration": "20.0",
        },
        {
            "id": "VID-R2",
            "url": "https://www.tiktok.com/@u/video/r2",
            "target": "Meio Ambiente",
            "video_description": "Energia solar",
            "voice_to_text": "Audio R2",
            "video_duration": "25.0",
        },
    ])
    tarefa = servico_auth.repo_estudo.criar_tarefa(
        criado_por_usuario_id=user["usuario_id"],
        pool_videos=pool,
        quantidade_videos_principal=2,
        numero_vagas=1,
        codigo_convite="TOK-RESILIENT",
    )
    servico_auth.entrar_na_tarefa_por_convite(user["usuario_id"], "TOK-RESILIENT")

    estado1 = servico_fila.obter_estado_fila(tarefa["tarefa_id"], "rotulador_resiliente")
    vid1 = estado1["video_atual"]

    # Salva anotação 1
    res1 = servico_fila.salvar_anotacao_e_avancar(
        tarefa_id=tarefa["tarefa_id"],
        nome_usuario="rotulador_resiliente",
        assignment_id=vid1["assignment_id"],
        posicao="A Favor",
        tempo_analise_segundos=15.0,
    )
    assert res1["anotacao_salva"]["stance"] == "A Favor"

    # Verifica que o diário físico foi escrito e ack registrado
    diario = banco.diario_anotacoes
    consol = diario.ler_registros_consolidados()
    chave = f"{tarefa['tarefa_id']}:{vid1['assignment_id']}"
    assert chave in consol
    assert consol[chave]["status"] == "sincronizado"


@pytest.mark.unit
def test_resiliencia_diario_a_linhas_parciais_ou_corrompidas(tmp_path: Path) -> None:
    caminho_j = tmp_path / "corrompido_journal.jsonl"
    diario = DiarioAnotacoesPersistencia(caminho_j)

    # Grava uma linha válida
    diario.registrar_pendente({
        "tarefa_id": 1,
        "assignment_id": "ASG-OK",
        "stance": "Neutro",
        "timestamp": "2026-11-07 10:30:00",
    })

    # Simula interrupção brusca (queda de energia) que deixou JSON incompleto no final
    with open(caminho_j, "a", encoding="utf-8") as f:
        f.write('{"tarefa_id": 1, "assignment_id": "ASG-INCOMPLETO", "sta')

    # A leitura não pode lançar exceção, deve recuperar com segurança a linha íntegra
    consol = diario.ler_registros_consolidados()
    assert "1:ASG-OK" in consol
    assert "1:ASG-INCOMPLETO" not in consol

    # Compactação atômica limpa o arquivo corrompido
    diario.compactar()
    consol_pos = diario.ler_registros_consolidados()
    assert "1:ASG-OK" in consol_pos
