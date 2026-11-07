"""Testes unitarios focados em fluxos de interface, dominio e servicos para alta cobertura."""

from datetime import datetime
import json
from pathlib import Path
import tempfile
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from tokstance.backend.domain.replacements import (
    aplicar_substituicoes_reserva,
    garantir_esquema_erros,
    garantir_esquema_resultados,
    ler_erros_atribuicoes,
    ler_resultados,
    carregar_atribuicoes,
)
from tokstance.backend.repositories.database import BancoDadosSQLite
from tokstance.backend.repositories.study_repo import RepositorioEstudo
from tokstance.backend.repositories.user_repo import RepositorioUsuarios
from tokstance.backend.services.admin_service import ServicoAdministracao
from tokstance.backend.services.auth_service import ServicoAutenticacao
from tokstance.backend.services.queue_service import ServicoFilaAnotacao
from tokstance.config import resolver_caminhos_dados
from tokstance.frontend.components import access_statistics, annotation_daily_chart
from tokstance.frontend.gradio_ui import (
    construir_interface,
    gerar_tabela_penalidades_df,
    renderizar_configuracao_admin_html,
    renderizar_hub_tabelas_html,
    renderizar_visao_geral_acervo_html,
)


@pytest.fixture()
def ambiente_completo(tmp_path: Path):
    db_path = tmp_path / "teste_cobertura.db"
    banco = BancoDadosSQLite(db_path)
    repo_u = RepositorioUsuarios(banco)
    repo_e = RepositorioEstudo(banco, repo_usuarios=repo_u)
    auth = ServicoAutenticacao(banco, repo_usuarios=repo_u, repo_estudo=repo_e)
    admin = ServicoAdministracao(banco, repo_usuarios=repo_u, repo_estudo=repo_e)
    fila = ServicoFilaAnotacao(banco, repo_usuarios=repo_u, repo_estudo=repo_e)

    #cria usuarios basicos
    u_admin = auth.cadastrar_usuario("admin_cob", "senhaForte123", email="admin_cob@ufmg.br", nome_completo="ADMIN COBERTURA")
    u_rot = auth.cadastrar_usuario("rot_cob", "senhaForte123", email="rot_cob@ufmg.br", nome_completo="ROTULADOR COBERTURA")

    pool = pd.DataFrame([
        {"id": f"v_{i}", "url": f"https://www.tiktok.com/@u/video/{i}", "target": "Alvo A" if i < 10 else "Alvo B", "video_description": f"desc {i}", "voice_to_text": f"text {i}", "video_duration": "15.0"}
        for i in range(20)
    ])
    reserva = pd.DataFrame([
        {"id": f"res_{i}", "url": f"https://www.tiktok.com/@u/video/{200+i}", "target": "Alvo A", "video_description": f"res desc {i}", "voice_to_text": f"res text {i}", "video_duration": "15.0"}
        for i in range(5)
    ])

    tarefa = admin.criar_nova_tarefa(
        usuario_administrador_id=int(u_admin["usuario_id"]),
        pool_videos=pool,
        quantidade_videos_principal=16,
        videos_reserva_explicitos=reserva,
        titulo="Tarefa Cobertura",
        pergunta="Qual o stance para {target}?",
        opcoes_posicao=["Contra", "A Favor", "Neutro", "Não Sei"],
        numero_vagas=2,
        percentual_sobreposicao=50.0,
        codigo_convite="TOK-COB01",
        permitir_admin_como_rotulador=True,
    )
    auth.entrar_na_tarefa_por_convite(int(u_rot["usuario_id"]), "TOK-COB01")

    app = construir_interface(servico_auth=auth, servico_fila=fila, servico_admin=admin)
    handlers = {getattr(fn.fn, "__name__", ""): fn.fn for fn in app.fns.values() if getattr(fn.fn, "__name__", "")}

    return {
        "banco": banco,
        "repo_u": repo_u,
        "repo_e": repo_e,
        "auth": auth,
        "admin": admin,
        "fila": fila,
        "u_admin": u_admin,
        "u_rot": u_rot,
        "tarefa": tarefa,
        "app": app,
        "handlers": handlers,
    }


@pytest.mark.unit
def test_handlers_gradio_autenticacao_e_acesso(ambiente_completo) -> None:
    h = ambiente_completo["handlers"]

    #login sucesso
    res_login = h["executar_login"]("admin_cob", "senhaForte123")
    sessao_admin = res_login[3]
    assert sessao_admin["usuario_id"] is not None
    assert sessao_admin["nome_usuario"] == "admin_cob"

    #login falha senha errada
    res_err = h["executar_login"]("admin_cob", "senhaErrada1")
    assert "Credenciais inválidas" in res_err[2]

    #login falha usuario inexistente
    res_inex = h["executar_login"]("usuario_fantasma", "senhaErrada1")
    assert "não encontrado" in res_err[2] or "inválidas" in res_inex[2]

    #cadastro sucesso
    res_cad = h["executar_cadastro"]("NOVO ANOTADOR", "novo_anot_cob", "novo@ufmg.br", "SenhaValida123", "SenhaValida123", "")
    sessao_cad = res_cad[3]
    assert sessao_cad["nome_usuario"] == "novo_anot_cob"

    #cadastro falha nome completo vazio
    res_cad_err = h["executar_cadastro"]("", "outro_u", "outro@ufmg.br", "SenhaValida123", "SenhaValida123", "")
    assert "nome completo" in res_cad_err[2].lower()

    #logout
    res_logout = h["executar_logout"](sessao_admin)
    assert res_logout[6]["usuario_id"] is None


@pytest.mark.unit
def test_handlers_gradio_recuperacao_de_senha(ambiente_completo) -> None:
    h = ambiente_completo["handlers"]

    #trocar identificador
    res_troca = h["executar_trocar_identificador"]()
    assert len(res_troca) > 0

    #solicitar recuperacao usuario existente
    res_sol = h["executar_solicitar_recuperacao"]("admin_cob")
    assert "enviado" in res_sol[0].lower() or "código" in res_sol[0].lower()

    #solicitar recuperacao usuario inexistente
    res_sol_err = h["executar_solicitar_recuperacao"]("nao_existe_123")
    assert "encontrado" in res_sol_err[0].lower() or "inválido" in res_sol_err[0].lower()

    #pega o codigo gerado no banco
    banco = ambiente_completo["banco"]
    row = banco.consultar_um(
        "SELECT codigo_recuperacao FROM recuperacao_senha WHERE usuario_id = ? ORDER BY recuperacao_id DESC LIMIT 1",
        (int(ambiente_completo["u_admin"]["usuario_id"]),),
    )
    assert row is not None
    codigo_real = str(row["codigo_recuperacao"])

    #verificar codigo invalido
    res_ver_err = h["executar_verificar_codigo"]("admin_cob", "000000")
    assert "inválido" in res_ver_err[0].lower()

    #verificar codigo valido
    res_ver_ok = h["executar_verificar_codigo"]("admin_cob", codigo_real)
    assert len(res_ver_ok) > 0

    #testes de redefinicao de senha com requisitos invalidos
    res_red_dif = h["executar_redefinir_senha"]("admin_cob", codigo_real, "NovaSenha123", "Outra456")
    assert "não coincidem" in res_red_dif[0].lower()

    res_red_fraca = h["executar_redefinir_senha"]("admin_cob", codigo_real, "fraca", "fraca")
    assert "6 caracteres" in res_red_fraca[0].lower()

    #redefinicao com sucesso
    res_red_ok = h["executar_redefinir_senha"]("admin_cob", codigo_real, "NovaSenhaForte999", "NovaSenhaForte999")
    assert "sucesso" in res_red_ok[0].lower()


@pytest.mark.unit
def test_handlers_gradio_wizard_e_convites(ambiente_completo) -> None:
    h = ambiente_completo["handlers"]
    sessao_admin = {"usuario_id": ambiente_completo["u_admin"]["usuario_id"], "nome_usuario": "admin_cob", "nome_completo": "ADMIN"}

    #abrir modal convite e fechar
    res_abrir_conv = h["abrir_modal_convite"]()
    res_fechar_conv = h["fechar_modal_convite"]()
    assert len(res_abrir_conv) > 0 and len(res_fechar_conv) > 0

    #validar gerador de codigo de convite
    from tokstance.backend.security.validators import gerar_codigo_convite
    novo_cod = gerar_codigo_convite()
    assert str(novo_cod).startswith("TOK-")

    #atualizar matriz de pares
    df_pares = h["atualizar_matriz_pares"]("Opção 1\nOpção 2\nOpção 3")
    assert len(df_pares) > 0
    df_pares_vazio = h["atualizar_matriz_pares"]("ApenasUma")
    assert df_pares_vazio.empty

    #abrir wizard criacao e voltar
    res_wiz = h["abrir_wizard_criacao"]()
    res_voltar = h["voltar_hub_de_wizard"](sessao_admin)
    assert len(res_wiz) > 0 and len(res_voltar) > 0

    #entrar por convite invalido
    res_conv_err = h["executar_entrar_convite"]("CONVITE_FALSO", sessao_admin)
    assert "encontrada" in res_conv_err[0].lower() or "inválido" in res_conv_err[0].lower()

    #entrar por convite valido
    sessao_rot = {"usuario_id": ambiente_completo["u_rot"]["usuario_id"], "nome_usuario": "rot_cob", "nome_completo": "ROT"}
    res_conv_ok = h["executar_entrar_convite"]("TOK-COB01", sessao_rot)
    assert len(res_conv_ok) > 0


@pytest.mark.unit
def test_handlers_gradio_navegacao_workspace_e_admin(ambiente_completo) -> None:
    h = ambiente_completo["handlers"]
    t_id = str(ambiente_completo["tarefa"]["tarefa_id"])
    sessao_admin = {"usuario_id": ambiente_completo["u_admin"]["usuario_id"], "nome_usuario": "admin_cob", "nome_completo": "ADMIN", "tarefa_ativa_id": int(t_id), "login_time": 1000.0, "start_time": 1000.0}

    #acao admin no hub
    res_hub_admin = h["processar_acao_hub"](f"admin:{t_id}", sessao_admin)
    assert len(res_hub_admin) > 0

    #acao rotular no hub
    res_hub_rot = h["processar_acao_hub"](f"rotular:{t_id}", sessao_admin)
    sessao_rotulando = res_hub_rot[-1]
    assert sessao_rotulando.get("assignment_id") != ""

    #aviso sensivel: continuar e parar
    res_cont = h["continuar_aviso_sensivel"](sessao_rotulando)
    assert len(res_cont) > 0
    res_parar = h["parar_rotulacao_sensivel"](sessao_rotulando)
    assert len(res_parar) > 0

    #salvar resposta rotulador sem selecionar opcao
    res_vazia = h["salvar_resposta_rotulador"]("", sessao_rotulando)
    assert "selecione uma opção" in res_vazia[4].lower()

    #salvar resposta com opcao valida
    res_salvo = h["salvar_resposta_rotulador"]("A Favor", sessao_rotulando)
    assert len(res_salvo) > 0

    #reportar erro de video antes do tempo minimo (deve exibir aviso de espera)
    res_erro_rapido = h["reportar_erro_rotulador"](sessao_rotulando)
    assert "aguarde" in res_erro_rapido[4].lower() or "segundos" in res_erro_rapido[4].lower()

    #voltar ao hub a partir de admin
    res_voltar_adm = h["voltar_hub_de_admin"](sessao_admin)
    assert len(res_voltar_adm) > 0

    #submeter nova tarefa com parametros invalidos
    df_pares = h["atualizar_matriz_pares"]("Op1\nOp2")
    res_sub_err = h["submeter_nova_tarefa"](
        sessao_admin, "", "", "", df_pares, 0, -10.0, "", False, None, 0
    )
    assert len(res_sub_err) > 0

    #excluir tarefa pelo admin
    res_del = h["excluir_tarefa_pelo_admin"](sessao_admin)
    assert len(res_del) > 0


@pytest.mark.unit
def test_replacements_e_helpers_de_dados(tmp_path: Path) -> None:
    #testa leitura com arquivo inexistente
    arq_inexistente = tmp_path / "inexistente.csv"
    df_vazio = ler_resultados(arq_inexistente)
    assert df_vazio.empty
    df_err_vazio = ler_erros_atribuicoes(arq_inexistente)
    assert df_err_vazio.empty

    #arquivo vazio
    arq_zerado = tmp_path / "zerado.csv"
    arq_zerado.write_text("", encoding="utf-8")
    df_zerado = ler_resultados(arq_zerado)
    assert df_zerado.empty

    #garantir_esquema_erros e garantir_esquema_resultados
    garantir_esquema_erros(tmp_path)
    garantir_esquema_resultados(tmp_path)

    #aplicar_substituicoes_reserva com videos_reserva populado
    caminhos = resolver_caminhos_dados(tmp_path)
    caminhos.arquivo_erros.write_text("timestamp,video_id,url,labeler,assignment_id,replacement_video_id,replacement_url,replacement_assignment_id,replacement_status\n2026-11-01,v1,u1,rot1,a1,,,,Pendente\n", encoding="utf-8")
    caminhos.arquivo_videos_reserva.write_text("id,url,target\nres1,http://res,T1\n", encoding="utf-8")
    caminhos.arquivo_resultados.write_text("timestamp,labeler,video_id,url,target,stance,tempo_analise_segundos,video_duration,assignment_id\n", encoding="utf-8")
    atrib = pd.DataFrame([{"assignment_version": "v1.0", "assignment_id": "a1", "labeler": "rot1", "video_id": "v1", "url": "u1", "target": "T1"}])
    res_atrib = aplicar_substituicoes_reserva(atrib, diretorio_dados=tmp_path)
    assert not res_atrib.empty


@pytest.mark.unit
def test_componentes_access_statistics_e_charts() -> None:
    #access_statistics com log populado
    log_data = [
        {"timestamp": "2026-11-01 10:00:00", "usuario": "user1", "acao": "LOGIN_LABELER", "tempo_desde_login_segundos": 0.0},
        {"timestamp": "2026-11-01 10:15:00", "usuario": "user1", "acao": "anotacao", "tempo_desde_login_segundos": 900.0},
        {"timestamp": "2026-11-01 14:00:00", "usuario": "user2", "acao": "login", "tempo_desde_login_segundos": 0.0},
        {"timestamp": "2026-11-02 09:00:00", "usuario": "user1", "acao": "login", "tempo_desde_login_segundos": 0.0},
    ]
    stats = access_statistics(log_data)
    assert "user1" in stats["session_rows"]
    assert stats["avg_minutes"] > 0
    assert "bar-fill" in stats["daily_rows"]

    #annotation_daily_chart com dados vazios e com dados de multiplos dias
    assert "não há anotações" in annotation_daily_chart(None)
    assert "não há anotações" in annotation_daily_chart(pd.DataFrame())

    chart_ok = annotation_daily_chart([
        {"timestamp": "2026-11-01 10:00:00", "labeler": "u1"},
        {"timestamp": "2026-11-01 11:00:00", "labeler": "u2"},
        {"timestamp": "2026-11-02 12:00:00", "labeler": "u1"},
    ])
    assert "<svg" in chart_ok
    assert "u1" in chart_ok and "u2" in chart_ok
