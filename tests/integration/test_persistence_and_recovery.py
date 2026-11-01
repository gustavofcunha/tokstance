"""Testes de integracao para armazenamento relacional SQLite por tarefa, vagas e exportacao sob demanda."""

import json
from pathlib import Path
import sqlite3

import pandas as pd
import pytest

from tokstance.backend.repositories.database import BancoDadosSQLite
from tokstance.backend.repositories.study_repo import RepositorioEstudo
from tokstance.backend.repositories.user_repo import RepositorioUsuarios
from tokstance.backend.security.password import gerar_hash_senha


def _pool_videos_exemplo() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "id": "71001",
                "url": "https://www.tiktok.com/@u/video/71001",
                "target": "Clima",
                "video_description": "Video clima 1",
                "voice_to_text": "Audio clima 1",
                "video_duration": "22.0",
            },
            {
                "id": "71002",
                "url": "https://www.tiktok.com/@u/video/71002",
                "target": "Clima",
                "video_description": "Video clima 2",
                "voice_to_text": "Audio clima 2",
                "video_duration": "25.0",
            },
            {
                "id": "71003",
                "url": "https://www.tiktok.com/@u/video/71003",
                "target": "Clima",
                "video_description": "Video clima 3",
                "voice_to_text": "Audio clima 3",
                "video_duration": "28.0",
            },
            {
                "id": "72001",
                "url": "https://www.tiktok.com/@u/video/72001",
                "target": "Economia",
                "video_description": "Video economia 1",
                "voice_to_text": "Audio economia 1",
                "video_duration": "19.0",
            },
            {
                "id": "72002",
                "url": "https://www.tiktok.com/@u/video/72002",
                "target": "Economia",
                "video_description": "Video economia 2",
                "voice_to_text": "Audio economia 2",
                "video_duration": "21.0",
            },
            {
                "id": "72003",
                "url": "https://www.tiktok.com/@u/video/72003",
                "target": "Economia",
                "video_description": "Video economia 3",
                "voice_to_text": "Audio economia 3",
                "video_duration": "24.0",
            },
        ]
    )


@pytest.mark.integration
def test_esquema_sqlite_cria_nove_tabelas_relacionais_e_ativa_chaves_estrangeiras(
    tmp_path: Path,
) -> None:
    banco = BancoDadosSQLite(tmp_path / "esquema.db")

    tabelas = banco.listar_tabelas()
    estado_fk = banco.consultar_um("PRAGMA foreign_keys;")

    assert tabelas == [
        "anotacoes",
        "atribuicoes",
        "erros_videos",
        "logs_acesso",
        "membros_tarefa",
        "recuperacao_senha",
        "tarefas",
        "usuarios",
        "videos_tarefa",
    ]
    assert estado_fk == {"foreign_keys": 1}


@pytest.mark.integration
def test_criar_tarefa_divide_pool_balanceado_entre_principal_e_reserva_no_sqlite(
    tmp_path: Path,
) -> None:
    banco = BancoDadosSQLite(tmp_path / "divisao_pool.db")
    repo_usuarios = RepositorioUsuarios(banco)
    repo_estudo = RepositorioEstudo(banco, repo_usuarios)
    admin = repo_usuarios.criar_usuario("admin_estudo", gerar_hash_senha("Senha123", rodadas=4))

    tarefa = repo_estudo.criar_tarefa(
        criado_por_usuario_id=admin["usuario_id"],
        pool_videos=_pool_videos_exemplo(),
        quantidade_videos_principal=4,
        numero_vagas=2,
        percentual_sobreposicao=50,
    )
    principais = repo_estudo.carregar_videos_tarefa_df(tarefa["tarefa_id"], "principal")
    reservas = repo_estudo.carregar_videos_tarefa_df(tarefa["tarefa_id"], "reserva")

    assert len(principais) == 4
    assert len(reservas) == 2
    assert principais["target"].value_counts().to_dict() == {"Clima": 2, "Economia": 2}
    assert reservas["target"].value_counts().to_dict() == {"Clima": 1, "Economia": 1}


@pytest.mark.integration
def test_vincular_rotulador_assume_vaga_1_e_vaga_2_e_aloca_fila_extra_no_terceiro(
    tmp_path: Path,
) -> None:
    banco = BancoDadosSQLite(tmp_path / "vagas.db")
    repo_usuarios = RepositorioUsuarios(banco)
    repo_estudo = RepositorioEstudo(banco, repo_usuarios)
    admin = repo_usuarios.criar_usuario("admin_vagas", gerar_hash_senha("Senha123", rodadas=4))
    u1 = repo_usuarios.criar_usuario("rot_alice", gerar_hash_senha("Senha123", rodadas=4))
    u2 = repo_usuarios.criar_usuario("rot_bruno", gerar_hash_senha("Senha123", rodadas=4))
    u3 = repo_usuarios.criar_usuario("rot_carla", gerar_hash_senha("Senha123", rodadas=4))
    tarefa = repo_estudo.criar_tarefa(
        criado_por_usuario_id=admin["usuario_id"],
        pool_videos=_pool_videos_exemplo(),
        quantidade_videos_principal=4,
        numero_vagas=2,
        percentual_sobreposicao=50,
    )

    membro_1 = repo_estudo.vincular_rotulador_na_tarefa(
        tarefa["tarefa_id"], u1["usuario_id"], "rot_alice"
    )
    membro_2 = repo_estudo.vincular_rotulador_na_tarefa(
        tarefa["tarefa_id"], u2["usuario_id"], "rot_bruno"
    )
    membro_3 = repo_estudo.vincular_rotulador_na_tarefa(
        tarefa["tarefa_id"], u3["usuario_id"], "rot_carla"
    )
    atribuicoes_carla = repo_estudo.carregar_atribuicoes_tarefa_df(
        tarefa["tarefa_id"], "rot_carla"
    )

    assert membro_1["vaga_atribuida"] == "vaga_1"
    assert membro_2["vaga_atribuida"] == "vaga_2"
    assert membro_3["vaga_atribuida"] == "rot_carla"
    assert len(atribuicoes_carla) == 3


@pytest.mark.integration
def test_criador_da_tarefa_acumula_papeis_de_administrador_e_rotulador_ao_entrar(
    tmp_path: Path,
) -> None:
    banco = BancoDadosSQLite(tmp_path / "multipapel.db")
    repo_usuarios = RepositorioUsuarios(banco)
    repo_estudo = RepositorioEstudo(banco, repo_usuarios)
    pesquisador = repo_usuarios.criar_usuario(
        "gustavo_ufmg", gerar_hash_senha("Senha123", rodadas=4)
    )
    tarefa = repo_estudo.criar_tarefa(
        criado_por_usuario_id=pesquisador["usuario_id"],
        pool_videos=_pool_videos_exemplo(),
        quantidade_videos_principal=4,
        numero_vagas=2,
    )

    repo_estudo.vincular_rotulador_na_tarefa(
        tarefa["tarefa_id"], pesquisador["usuario_id"], "gustavo_ufmg"
    )
    papeis = repo_usuarios.listar_papeis_usuario_na_tarefa(
        tarefa["tarefa_id"], pesquisador["usuario_id"]
    )
    tarefas_admin = repo_usuarios.listar_tarefas_do_usuario(
        pesquisador["usuario_id"], papel="administrador"
    )
    tarefas_rotulador = repo_usuarios.listar_tarefas_do_usuario(
        pesquisador["usuario_id"], papel="rotulador"
    )

    assert papeis == ["administrador", "rotulador"]
    assert len(tarefas_admin) == 1
    assert len(tarefas_rotulador) == 1
    assert tarefas_rotulador[0]["vaga_atribuida"] == "vaga_1"


@pytest.mark.integration
def test_persistencia_anotacoes_recupera_posicao_pendente_da_fila_apos_reabrir_banco(
    tmp_path: Path,
) -> None:
    caminho_db = tmp_path / "recuperacao.db"
    banco_1 = BancoDadosSQLite(caminho_db)
    repo_usuarios_1 = RepositorioUsuarios(banco_1)
    repo_estudo_1 = RepositorioEstudo(banco_1, repo_usuarios_1)
    usuario = repo_usuarios_1.criar_usuario("rot_persistente", gerar_hash_senha("Senha123", rodadas=4))
    tarefa = repo_estudo_1.criar_tarefa(
        criado_por_usuario_id=usuario["usuario_id"],
        pool_videos=_pool_videos_exemplo(),
        quantidade_videos_principal=4,
        numero_vagas=1,
    )
    repo_estudo_1.vincular_rotulador_na_tarefa(
        tarefa["tarefa_id"], usuario["usuario_id"], "rot_persistente"
    )
    fila_inicial = repo_estudo_1.carregar_atribuicoes_tarefa_df(
        tarefa["tarefa_id"], "rot_persistente"
    )
    primeiro_item = fila_inicial.iloc[0]
    repo_estudo_1.registrar_anotacao(
        tarefa_id=tarefa["tarefa_id"],
        assignment_id=str(primeiro_item["assignment_id"]),
        rotulador="rot_persistente",
        video_id=str(primeiro_item["video_id"]),
        url=str(primeiro_item["url"]),
        target=str(primeiro_item["target"]),
        posicao="A Favor",
        tempo_analise_segundos=18.4,
        video_duration=str(primeiro_item["video_duration"]),
    )

    banco_reaberto = BancoDadosSQLite(caminho_db)
    repo_estudo_2 = RepositorioEstudo(banco_reaberto)
    fila_reaberta = repo_estudo_2.carregar_atribuicoes_tarefa_df(
        tarefa["tarefa_id"], "rot_persistente"
    )
    anotadas_reabertas = repo_estudo_2.carregar_anotacoes_tarefa_df(
        tarefa["tarefa_id"], "rot_persistente"
    )
    ids_concluidos = set(anotadas_reabertas["assignment_id"].astype(str))
    pendentes = fila_reaberta[~fila_reaberta["assignment_id"].isin(ids_concluidos)]

    assert len(fila_reaberta) == 4
    assert len(anotadas_reabertas) == 1
    assert len(pendentes) == 3
    assert str(pendentes.iloc[0]["assignment_id"]) == str(fila_inicial.iloc[1]["assignment_id"])


@pytest.mark.integration
def test_isolamento_relacional_entre_duas_tarefas_distintas_no_mesmo_banco(
    tmp_path: Path,
) -> None:
    banco = BancoDadosSQLite(tmp_path / "multitarefa.db")
    repo_usuarios = RepositorioUsuarios(banco)
    repo_estudo = RepositorioEstudo(banco, repo_usuarios)
    admin = repo_usuarios.criar_usuario("coordenador", gerar_hash_senha("Senha123", rodadas=4))

    tarefa_a = repo_estudo.criar_tarefa(
        criado_por_usuario_id=admin["usuario_id"],
        pool_videos=_pool_videos_exemplo().iloc[:2],
        titulo="Tarefa A",
        opcoes_posicao=["Sim", "Não"],
        codigo_convite="TOK-TAREFA-A",
    )
    tarefa_b = repo_estudo.criar_tarefa(
        criado_por_usuario_id=admin["usuario_id"],
        pool_videos=_pool_videos_exemplo().iloc[2:6],
        titulo="Tarefa B",
        opcoes_posicao=["Positivo", "Negativo", "Neutro"],
        codigo_convite="TOK-TAREFA-B",
    )
    videos_a = repo_estudo.carregar_videos_tarefa_df(tarefa_a["tarefa_id"], "principal")
    videos_b = repo_estudo.carregar_videos_tarefa_df(tarefa_b["tarefa_id"], "principal")

    assert len(videos_a) == 2
    assert len(videos_b) == 4
    assert tarefa_a["opcoes_posicao"] == ["Sim", "Não"]
    assert tarefa_b["opcoes_posicao"] == ["Positivo", "Negativo", "Neutro"]


@pytest.mark.integration
def test_exportar_arquivos_tarefa_gera_oito_artefatos_csv_e_json_sob_demanda(
    tmp_path: Path,
) -> None:
    banco = BancoDadosSQLite(tmp_path / "exportacao.db")
    repo_usuarios = RepositorioUsuarios(banco)
    repo_estudo = RepositorioEstudo(banco, repo_usuarios)
    admin = repo_usuarios.criar_usuario("admin_export", gerar_hash_senha("Senha123", rodadas=4))
    tarefa = repo_estudo.criar_tarefa(
        criado_por_usuario_id=admin["usuario_id"],
        pool_videos=_pool_videos_exemplo(),
        quantidade_videos_principal=4,
        numero_vagas=2,
        percentual_sobreposicao=100,
    )
    repo_estudo.vincular_rotulador_na_tarefa(
        tarefa["tarefa_id"], admin["usuario_id"], "admin_export"
    )
    fila = repo_estudo.carregar_atribuicoes_tarefa_df(tarefa["tarefa_id"], "admin_export")
    item = fila.iloc[0]
    repo_estudo.registrar_anotacao(
        tarefa_id=tarefa["tarefa_id"],
        assignment_id=str(item["assignment_id"]),
        rotulador="admin_export",
        video_id=str(item["video_id"]),
        url=str(item["url"]),
        target=str(item["target"]),
        posicao="Contra",
        tempo_analise_segundos=14.0,
    )
    repo_estudo.registrar_log_acesso("admin_export", "login", tarefa["tarefa_id"], 0.0)

    caminhos = repo_estudo.exportar_arquivos_tarefa(
        tarefa["tarefa_id"], tmp_path / "artefatos_admin"
    )
    config_exportada = json.loads(caminhos.arquivo_configuracao.read_text(encoding="utf-8"))
    concordancia_exportada = json.loads(
        caminhos.arquivo_concordancia.read_text(encoding="utf-8")
    )

    assert caminhos.arquivo_configuracao.exists()
    assert caminhos.arquivo_videos.exists()
    assert caminhos.arquivo_videos_reserva.exists()
    assert caminhos.arquivo_atribuicoes.exists()
    assert caminhos.arquivo_resultados.exists()
    assert caminhos.arquivo_erros.exists()
    assert caminhos.arquivo_log.exists()
    assert caminhos.arquivo_concordancia.exists()
    assert config_exportada["tarefa"] == "Detecção de Posição"
    assert "metrica" in concordancia_exportada


@pytest.mark.integration
def test_violacao_chave_estrangeira_em_membros_tarefa_e_bloqueada_pelo_sqlite(
    tmp_path: Path,
) -> None:
    banco = BancoDadosSQLite(tmp_path / "fk_erro.db")
    repo_usuarios = RepositorioUsuarios(banco)

    with pytest.raises(sqlite3.IntegrityError):
        repo_usuarios.adicionar_membro_tarefa(
            tarefa_id=9999,
            usuario_id=8888,
            papel="rotulador",
        )



@pytest.mark.integration
def test_executar_distingue_lastrowid_para_insert_e_rowcount_para_update_delete(
    tmp_path: Path,
) -> None:
    banco = BancoDadosSQLite(tmp_path / "rowcount_test.db")

    id_inserido = banco.executar(
        "INSERT INTO usuarios (nome_usuario, senha_hash, criado_em) VALUES (?, ?, ?);",
        ("usuario_teste", "hash_teste", "2026-10-31 12:00:00"),
    )
    linhas_afetadas_update = banco.executar(
        "UPDATE usuarios SET senha_hash = ? WHERE usuario_id = ?;",
        ("novo_hash", id_inserido),
    )
    linhas_afetadas_delete = banco.executar(
        "DELETE FROM usuarios WHERE usuario_id = ?;",
        (id_inserido,),
    )

    assert id_inserido >= 1
    assert linhas_afetadas_update == 1
    assert linhas_afetadas_delete == 1


@pytest.mark.integration
def test_listar_tarefas_do_usuario_deserializa_opcoes_posicao_e_distancias(
    tmp_path: Path,
) -> None:
    banco = BancoDadosSQLite(tmp_path / "tarefas_deserializadas.db")
    repo_usuarios = RepositorioUsuarios(banco)
    repo_estudo = RepositorioEstudo(banco, repo_usuarios)
    admin = repo_usuarios.criar_usuario("admin_json", "hash_seguro")

    tarefa = repo_estudo.criar_tarefa(
        criado_por_usuario_id=admin["usuario_id"],
        pool_videos=_pool_videos_exemplo(),
        opcoes_posicao=["A Favor", "Contra"],
        distancias_rotulos={"A Favor|Contra": 2.5},
    )
    tarefas_admin = repo_usuarios.listar_tarefas_do_usuario(
        admin["usuario_id"], papel="administrador"
    )

    assert len(tarefas_admin) == 1
    assert tarefas_admin[0]["opcoes_posicao"] == ["A Favor", "Contra"]
    assert tarefas_admin[0]["distancias_rotulos"]["A Favor|Contra"] == 2.5
