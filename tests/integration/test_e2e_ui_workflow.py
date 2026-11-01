"""Testes de integracao ponta a ponta (E2E) para todos os fluxos da plataforma.

Cobre a jornada completa do usuario:
1. Cadastro de novos pesquisadores e rotuladores
2. Autenticacao e gerenciamento de sessao
3. Criacao de tarefa no Wizard com pool particionado e matriz de penalidades
4. Ingresso em tarefas via codigo de convite compartilhado
5. Ciclo de rotulacao de videos (fluxo normal, aviso sensivel e relato de erro com reserva)
6. Calculo de concordancia ordinal (Alfa de Krippendorff) e metricas no Console Administrativo
7. Exportacao de relatorios e auditoria
"""

import json
from pathlib import Path
import sqlite3
from typing import Any, Dict

import pandas as pd
import pytest

from tokstance.backend.domain.agreement import calcular_concordancia
from tokstance.backend.repositories.database import BancoDadosSQLite
from tokstance.backend.repositories.study_repo import RepositorioEstudo
from tokstance.backend.repositories.user_repo import RepositorioUsuarios
from tokstance.backend.security.password import gerar_hash_senha
from tokstance.backend.services.admin_service import ServicoAdministracao
from tokstance.backend.services.auth_service import ServicoAutenticacao
from tokstance.backend.services.queue_service import ServicoFilaAnotacao


def _criar_pool_teste() -> pd.DataFrame:
    """Cria um conjunto balanceado de videos para simulacao ponta a ponta."""
    dados = []
    # 4 videos do tema 'Tecnologia'
    for i in range(1, 5):
        dados.append({
            "id": f"video_tec_{i}",
            "url": f"https://www.tiktok.com/@canal/video/{1000 + i}",
            "target": "Inteligência Artificial",
            "video_description": f"Discussão sobre IA na sociedade {i}",
            "voice_to_text": f"Transcrição do áudio sobre IA {i}",
            "video_duration": f"{15.0 + i}",
        })
    # 4 videos do tema 'Economia'
    for i in range(1, 5):
        dados.append({
            "id": f"video_eco_{i}",
            "url": f"https://www.tiktok.com/@canal/video/{2000 + i}",
            "target": "Inflação",
            "video_description": f"Análise sobre inflação e juros {i}",
            "voice_to_text": f"Transcrição sobre índices econômicos {i}",
            "video_duration": f"{20.0 + i}",
        })
    return pd.DataFrame(dados)


@pytest.fixture
def ambiente_e2e(tmp_path: Path):
    """Instancia os servicos e banco em diretorio temporario isolado."""
    banco_path = tmp_path / "tokstance_e2e.db"
    banco = BancoDadosSQLite(banco_path)
    repo_usuarios = RepositorioUsuarios(banco)
    repo_estudo = RepositorioEstudo(banco, repo_usuarios=repo_usuarios)

    servico_auth = ServicoAutenticacao(
        banco=banco,
        repo_usuarios=repo_usuarios,
        repo_estudo=repo_estudo,
    )
    servico_admin = ServicoAdministracao(
        banco=banco,
        repo_usuarios=repo_usuarios,
        repo_estudo=repo_estudo,
    )
    servico_fila = ServicoFilaAnotacao(
        banco=banco,
        repo_usuarios=repo_usuarios,
        repo_estudo=repo_estudo,
    )

    return {
        "banco": banco,
        "repo_usuarios": repo_usuarios,
        "repo_estudo": repo_estudo,
        "auth": servico_auth,
        "admin": servico_admin,
        "fila": servico_fila,
        "export_dir": tmp_path / "exports",
    }


@pytest.mark.integration
def test_jornada_e2e_completa_cadastro_criacao_e_rotulacao(ambiente_e2e: Dict[str, Any]):
    """Testa o fluxo ponta a ponta: cadastro do admin, criacao da tarefa, ingresso de rotulador e rotulacao."""
    auth = ambiente_e2e["auth"]
    admin = ambiente_e2e["admin"]
    fila = ambiente_e2e["fila"]

    # -------------------------------------------------------------------------
    # 1. Cadastro e Login do Administrador
    # -------------------------------------------------------------------------
    admin_user = auth.cadastrar_usuario("carlos_admin", "senhaCarlos123")
    assert admin_user["usuario_id"] is not None
    assert admin_user["nome_usuario"] == "carlos_admin"

    sessao_admin = auth.autenticar_usuario("carlos_admin", "senhaCarlos123")
    assert sessao_admin is not None
    assert sessao_admin["usuario_id"] == admin_user["usuario_id"]

    # -------------------------------------------------------------------------
    # 2. Criacao da Tarefa com Particionamento e Penalidades Customizadas
    # -------------------------------------------------------------------------
    pool_completo = _criar_pool_teste()
    assert len(pool_completo) == 8

    opcoes = ["A Favor", "Contra", "Neutro"]
    distancias = {
        "('A Favor', 'A Favor')": 0.0,
        "('A Favor', 'Neutro')": 1.0,
        "('A Favor', 'Contra')": 4.0,
        "('Contra', 'Contra')": 0.0,
        "('Contra', 'Neutro')": 1.0,
        "('Neutro', 'Neutro')": 0.0,
    }

    tarefa_criada = admin.criar_nova_tarefa(
        usuario_administrador_id=int(admin_user["usuario_id"]),
        pool_videos=pool_completo,
        quantidade_videos_principal=6,
        titulo="Estudo de Posicionamento E2E",
        pergunta='Qual o posicionamento com relação ao tema "{target}"?',
        opcoes_posicao=opcoes,
        distancias_rotulos=distancias,
        numero_vagas=2,
        percentual_sobreposicao=50.0,
        codigo_convite="CONVITE-E2E-2026",
        permitir_admin_como_rotulador=True,
    )

    t_id = int(tarefa_criada["tarefa_id"])
    assert t_id > 0
    assert tarefa_criada["codigo_convite"] == "CONVITE-E2E-2026"
    assert tarefa_criada["quantidade_videos_principal"] == 6
    assert tarefa_criada["quantidade_videos_reserva"] == 2

    # Verifica se o administrador foi vinculado na Vaga 1
    painel_admin_inicial = auth.obter_painel_usuario(int(admin_user["usuario_id"]))
    assert len(painel_admin_inicial["tarefas_administrador"]) == 1
    assert len(painel_admin_inicial["tarefas_rotulador"]) == 1
    assert painel_admin_inicial["tarefas_rotulador"][0]["tarefa_id"] == t_id

    # -------------------------------------------------------------------------
    # 3. Cadastro do Segundo Rotulador e Ingresso via Codigo de Convite
    # -------------------------------------------------------------------------
    rotulador_user = auth.cadastrar_usuario("mariana_rot", "senhaMariana456")
    sessao_rotulador = auth.autenticar_usuario("mariana_rot", "senhaMariana456")
    assert sessao_rotulador is not None

    sucesso_ingresso = auth.entrar_na_tarefa_por_convite(
        usuario_id=int(rotulador_user["usuario_id"]),
        codigo_convite="CONVITE-E2E-2026",
    )
    assert sucesso_ingresso["tarefa_id"] == t_id
    assert sucesso_ingresso["papel"] == "rotulador"

    painel_mariana = auth.obter_painel_usuario(int(rotulador_user["usuario_id"]))
    assert len(painel_mariana["tarefas_rotulador"]) == 1
    assert painel_mariana["tarefas_rotulador"][0]["tarefa_id"] == t_id

    # -------------------------------------------------------------------------
    # 4. Rotulacao do Primeiro Usuario (carlos_admin)
    # -------------------------------------------------------------------------
    estado_carlos = fila.obter_estado_fila(t_id, "carlos_admin", aviso_sensivel_aceito=True)
    assert estado_carlos["concluida"] is False
    assert estado_carlos["video_atual"] is not None

    while estado_carlos["video_atual"] is not None:
        v_atual = estado_carlos["video_atual"]
        asg_id = v_atual["assignment_id"]

        res = fila.salvar_anotacao_e_avancar(
            tarefa_id=t_id,
            nome_usuario="carlos_admin",
            assignment_id=asg_id,
            posicao="A Favor",
            tempo_analise_segundos=12.5,
        )
        estado_carlos = res["estado_fila"]

    assert estado_carlos["concluida"] is True

    # -------------------------------------------------------------------------
    # 5. Rotulacao do Segundo Usuario (mariana_rot)
    # -------------------------------------------------------------------------
    estado_mariana = fila.obter_estado_fila(t_id, "mariana_rot", aviso_sensivel_aceito=True)
    assert estado_mariana["concluida"] is False

    contador = 0
    while estado_mariana["video_atual"] is not None:
        v_atual = estado_mariana["video_atual"]
        asg_id = v_atual["assignment_id"]
        resp = "A Favor" if contador % 2 == 0 else "Neutro"

        res = fila.salvar_anotacao_e_avancar(
            tarefa_id=t_id,
            nome_usuario="mariana_rot",
            assignment_id=asg_id,
            posicao=resp,
            tempo_analise_segundos=14.0,
        )
        contador += 1
        estado_mariana = res["estado_fila"]

    assert estado_mariana["concluida"] is True

    # -------------------------------------------------------------------------
    # 6. Validacao de Metricas, Concordancia e Arquivos do Console do Administrador
    # -------------------------------------------------------------------------
    relatorio = admin.obter_metricas_operacionais(t_id)
    assert relatorio["tarefa_id"] == t_id
    assert len(relatorio["progresso_rotuladores"]) == 2
    assert relatorio["progresso_percentual"] == 100.0
    assert relatorio["total_anotacoes"] > 0
    assert relatorio["concordancia"] is not None

    # Verificar exportacoes
    caminhos = admin.exportar_arquivos_console(t_id)
    assert caminhos.arquivo_resultados.exists()
    assert caminhos.arquivo_log.exists()
    assert caminhos.arquivo_erros.exists()
    assert caminhos.arquivo_concordancia.exists()

    df_res = pd.read_csv(caminhos.arquivo_resultados)
    assert len(df_res) > 0
    assert "assignment_id" in df_res.columns
    assert "stance" in df_res.columns


@pytest.mark.integration
def test_e2e_substituicao_video_com_erro(ambiente_e2e: Dict[str, Any]):
    """Testa relato de erro de video e substituicao automatica a partir do pool de reserva."""
    auth = ambiente_e2e["auth"]
    admin = ambiente_e2e["admin"]
    fila = ambiente_e2e["fila"]

    user = auth.cadastrar_usuario("lucas_teste", "senhaLucas123")
    pool = _criar_pool_teste()

    tarefa = admin.criar_nova_tarefa(
        usuario_administrador_id=int(user["usuario_id"]),
        pool_videos=pool,
        quantidade_videos_principal=4,
        titulo="Estudo Erro e Reserva",
        codigo_convite="CONVITE-ERRO-123",
        permitir_admin_como_rotulador=True,
    )
    t_id = int(tarefa["tarefa_id"])

    estado_inicial = fila.obter_estado_fila(t_id, "lucas_teste", aviso_sensivel_aceito=True)
    assert estado_inicial["video_atual"] is not None
    video_problematico = estado_inicial["video_atual"]
    asg_id = video_problematico["assignment_id"]

    # Relatar erro no video apos aguardar tempo minimo regulamentar
    resultado_subst = fila.reportar_erro_video(
        tarefa_id=t_id,
        nome_usuario="lucas_teste",
        assignment_id=asg_id,
        tempo_analise_segundos=12.0,
    )
    assert "SUBSTITUIDO" in resultado_subst["status_substituicao"]
    assert resultado_subst["erro_registrado"]["video_id"] == video_problematico["video_id"]

    # Verifica se o novo estado da fila avancou ou substituiu
    novo_estado = resultado_subst["estado_fila"]
    assert novo_estado is not None


@pytest.mark.integration
def test_e2e_tentativa_codigo_duplicado_lanca_erro_amigavel(ambiente_e2e: Dict[str, Any]):
    """Verifica prevencao de colisao de codigos de convite."""
    auth = ambiente_e2e["auth"]
    admin = ambiente_e2e["admin"]
    pool = _criar_pool_teste()

    u = auth.cadastrar_usuario("prof_silva", "senhaProf123")
    admin.criar_nova_tarefa(
        usuario_administrador_id=int(u["usuario_id"]),
        pool_videos=pool,
        titulo="Estudo Original",
        codigo_convite="CODIGO-UNICO",
    )

    # Segunda tentativa com o mesmo codigo deve levantar ValueError
    with pytest.raises(ValueError, match="já está em uso por outra tarefa"):
        admin.criar_nova_tarefa(
            usuario_administrador_id=int(u["usuario_id"]),
            pool_videos=pool,
            titulo="Estudo Duplicado",
            codigo_convite="CODIGO-UNICO",
        )
