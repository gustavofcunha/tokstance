"""Testes unitarios para caminhos infelizes, validacoes e prevencao de regressao de bugs reportados.

Cobre cenarios negativos e de borda:
1. Validacao de quantidade de videos principais no particionamento do pool
2. Prevencao de colisao e duplicacao de codigos de convite
3. Bloqueio de submissao de anotacao vazia, invalida ou assignment inexistente
4. Protecao contra relato prematuro de erro de video (< 10s) e esgotamento de reserva
5. Tentativas invalidas de autenticacao e protecao contra sequestro de sessao
6. Tentativa de exclusao de tarefa por usuario nao-autorizado ou tarefa inexistente
7. Tentativa de ingresso em tarefa com codigo invalido ou vagas esgotadas
8. Robustez de conversores de entrada da interface grafica frente a dados corrompidos
"""

from pathlib import Path
from typing import Any, Dict
import pandas as pd
import pytest

from tokstance.backend.repositories.database import BancoDadosSQLite
from tokstance.backend.repositories.study_repo import RepositorioEstudo
from tokstance.backend.repositories.user_repo import RepositorioUsuarios
from tokstance.backend.services.admin_service import ServicoAdministracao
from tokstance.backend.services.auth_service import ServicoAutenticacao
from tokstance.backend.services.queue_service import ServicoFilaAnotacao
from tokstance.frontend.components import render_tiktok
from tokstance.frontend.gradio_ui import (
    converter_df_para_distancias,
    gerar_tabela_penalidades_df,
    renderizar_configuracao_admin_html,
)
from tokstance.frontend.theme import APP_CSS


def _criar_pool_minimo() -> pd.DataFrame:
    """Gera um pool minimo de videos para os testes unitarios de caminho infeliz."""
    return pd.DataFrame([
        {
            "id": f"vid_{i}",
            "url": f"https://www.tiktok.com/@canal/video/{3000 + i}",
            "target": "Tema A" if i % 2 == 0 else "Tema B",
            "video_description": f"Descricao {i}",
            "voice_to_text": f"Transcricao {i}",
            "video_duration": "20.0",
        }
        for i in range(1, 5)
    ])


@pytest.fixture
def servicos_teste(tmp_path: Path) -> Dict[str, Any]:
    """Prepara banco SQLite isolado e instancia os servicos do backend."""
    banco = BancoDadosSQLite(tmp_path / "unhappy_paths.db")
    repo_u = RepositorioUsuarios(banco)
    repo_e = RepositorioEstudo(banco, repo_u)
    auth = ServicoAutenticacao(banco, repo_u, repo_e, rodadas_bcrypt=4)
    admin = ServicoAdministracao(banco, repo_u, repo_e)
    fila = ServicoFilaAnotacao(banco, repo_u, repo_e)
    return {
        "banco": banco,
        "repo_u": repo_u,
        "repo_e": repo_e,
        "auth": auth,
        "admin": admin,
        "fila": fila,
    }


# ==============================================================================
# 1. CRIACAO DE TAREFAS: VALIDACOES E PREVENCAO DE COLISAO DE CONVITE
# ==============================================================================

@pytest.mark.unit
def test_criar_tarefa_quantidade_principal_invalida_lanca_erro(servicos_teste: Dict[str, Any]):
    """Verifica que quantidade_videos_principal negativa ou zero levanta ValueError."""
    auth = servicos_teste["auth"]
    admin = servicos_teste["admin"]
    u = auth.cadastrar_usuario("admin_val", "SenhaForte123")
    pool = _criar_pool_minimo()

    with pytest.raises(ValueError, match="quantidade de vídeos principais deve ser maior que zero"):
        admin.criar_nova_tarefa(
            usuario_administrador_id=int(u["usuario_id"]),
            pool_videos=pool,
            quantidade_videos_principal=0,
        )

    with pytest.raises(ValueError, match="quantidade de vídeos principais deve ser maior que zero"):
        admin.criar_nova_tarefa(
            usuario_administrador_id=int(u["usuario_id"]),
            pool_videos=pool,
            quantidade_videos_principal=-3,
        )


@pytest.mark.unit
def test_criar_tarefa_pool_vazio_lanca_erro(servicos_teste: Dict[str, Any]):
    """Verifica rejeicao ao tentar criar tarefa sem nenhum video no pool."""
    auth = servicos_teste["auth"]
    admin = servicos_teste["admin"]
    u = auth.cadastrar_usuario("admin_vazio", "SenhaForte123")
    pool_vazio = pd.DataFrame(columns=["id", "url", "target"])

    with pytest.raises(ValueError, match="O conjunto de vídeos da tarefa não pode estar vazio"):
        admin.criar_nova_tarefa(
            usuario_administrador_id=int(u["usuario_id"]),
            pool_videos=pool_vazio,
        )


@pytest.mark.unit
def test_criar_tarefa_codigo_convite_duplicado_rejeita_sem_corromper(servicos_teste: Dict[str, Any]):
    """Garante que codigo de convite duplicado e barrado com mensagem amigavel e sem orfaos."""
    auth = servicos_teste["auth"]
    admin = servicos_teste["admin"]
    u = auth.cadastrar_usuario("admin_convite", "SenhaForte123")
    pool = _criar_pool_minimo()

    t1 = admin.criar_nova_tarefa(
        usuario_administrador_id=int(u["usuario_id"]),
        pool_videos=pool,
        titulo="Tarefa 1",
        codigo_convite="CONVITE-UNICO-XYZ",
    )
    assert t1["tarefa_id"] is not None

    with pytest.raises(ValueError, match="já está em uso por outra tarefa"):
        admin.criar_nova_tarefa(
            usuario_administrador_id=int(u["usuario_id"]),
            pool_videos=pool,
            titulo="Tarefa 2",
            codigo_convite="CONVITE-UNICO-XYZ",
        )


# ==============================================================================
# 2. SALVAR ANOTACAO: VALIDACAO DE OPCOES E SEGURANCA DE ATRIBUICAO
# ==============================================================================

@pytest.mark.unit
def test_salvar_anotacao_sem_opcao_selecionada_lanca_erro(servicos_teste: Dict[str, Any]):
    """Verifica que tentar salvar sem escolher uma opcao levanta ValueError."""
    auth = servicos_teste["auth"]
    admin = servicos_teste["admin"]
    fila = servicos_teste["fila"]
    u = auth.cadastrar_usuario("rot_salvar1", "SenhaForte123")
    pool = _criar_pool_minimo()

    tarefa = admin.criar_nova_tarefa(
        usuario_administrador_id=int(u["usuario_id"]),
        pool_videos=pool,
        permitir_admin_como_rotulador=True,
    )
    t_id = int(tarefa["tarefa_id"])
    estado = fila.obter_estado_fila(t_id, "rot_salvar1", aviso_sensivel_aceito=True)
    vid = estado["video_atual"]
    assert vid is not None

    with pytest.raises(ValueError, match="Selecione uma opção de resposta antes de salvar"):
        fila.salvar_anotacao_e_avancar(
            tarefa_id=t_id,
            nome_usuario="rot_salvar1",
            assignment_id=vid["assignment_id"],
            posicao=None,
            tempo_analise_segundos=15.0,
        )

    with pytest.raises(ValueError, match="Selecione uma opção de resposta antes de salvar"):
        fila.salvar_anotacao(
            tarefa_id=t_id,
            nome_usuario="rot_salvar1",
            assignment_id=vid["assignment_id"],
            posicao="   ",
            tempo_analise_segundos=15.0,
        )


@pytest.mark.unit
def test_salvar_anotacao_com_opcao_fora_da_lista_lanca_erro(servicos_teste: Dict[str, Any]):
    """Verifica que rotulo nao pertencente a lista configurada para a tarefa e rejeitado."""
    auth = servicos_teste["auth"]
    admin = servicos_teste["admin"]
    fila = servicos_teste["fila"]
    u = auth.cadastrar_usuario("rot_salvar2", "SenhaForte123")
    pool = _criar_pool_minimo()

    tarefa = admin.criar_nova_tarefa(
        usuario_administrador_id=int(u["usuario_id"]),
        pool_videos=pool,
        opcoes_posicao=["A Favor", "Contra"],
        permitir_admin_como_rotulador=True,
    )
    t_id = int(tarefa["tarefa_id"])
    estado = fila.obter_estado_fila(t_id, "rot_salvar2", aviso_sensivel_aceito=True)
    vid = estado["video_atual"]

    with pytest.raises(ValueError, match="não pertence às opções desta tarefa"):
        fila.salvar_anotacao_e_avancar(
            tarefa_id=t_id,
            nome_usuario="rot_salvar2",
            assignment_id=vid["assignment_id"],
            posicao="OpcaoTotalmenteInexistente",
            tempo_analise_segundos=15.0,
        )


@pytest.mark.unit
def test_salvar_anotacao_assignment_inexistente_lanca_erro(servicos_teste: Dict[str, Any]):
    """Verifica que tentar salvar assignment inexistente lanca erro de atribuicao nao encontrada."""
    auth = servicos_teste["auth"]
    admin = servicos_teste["admin"]
    fila = servicos_teste["fila"]
    u = auth.cadastrar_usuario("rot_salvar3", "SenhaForte123")
    pool = _criar_pool_minimo()

    tarefa = admin.criar_nova_tarefa(
        usuario_administrador_id=int(u["usuario_id"]),
        pool_videos=pool,
        permitir_admin_como_rotulador=True,
    )
    t_id = int(tarefa["tarefa_id"])

    with pytest.raises(ValueError, match="Atribuição de vídeo não encontrada"):
        fila.salvar_anotacao_e_avancar(
            tarefa_id=t_id,
            nome_usuario="rot_salvar3",
            assignment_id="assignment_fantasma_999",
            posicao="A Favor",
            tempo_analise_segundos=15.0,
        )


# ==============================================================================
# 3. REPORTAR ERRO DE VIDEO: TEMPO MINIMO E ESGOTAMENTO DE RESERVA
# ==============================================================================

@pytest.mark.unit
def test_reportar_erro_antes_dos_dez_segundos_minimos_lanca_erro(servicos_teste: Dict[str, Any]):
    """Garante cumprimento da regra regulamentar dos 10 segundos antes de reportar erro."""
    auth = servicos_teste["auth"]
    admin = servicos_teste["admin"]
    fila = servicos_teste["fila"]
    u = auth.cadastrar_usuario("rot_erro1", "SenhaForte123")
    pool = _criar_pool_minimo()

    tarefa = admin.criar_nova_tarefa(
        usuario_administrador_id=int(u["usuario_id"]),
        pool_videos=pool,
        permitir_admin_como_rotulador=True,
    )
    t_id = int(tarefa["tarefa_id"])
    estado = fila.obter_estado_fila(t_id, "rot_erro1", aviso_sensivel_aceito=True)
    vid = estado["video_atual"]

    # Tentativa precoce (4.5 segundos decorridos)
    with pytest.raises(ValueError, match="Aguarde pelo menos 10 segundos"):
        fila.reportar_erro_video(
            tarefa_id=t_id,
            nome_usuario="rot_erro1",
            assignment_id=vid["assignment_id"],
            tempo_analise_segundos=4.5,
        )


@pytest.mark.unit
def test_reportar_erro_sem_videos_reserva_marca_status_sem_travar(servicos_teste: Dict[str, Any]):
    """Verifica que quando o pool de reserva esta vazio o sistema registra o erro com status seguro."""
    auth = servicos_teste["auth"]
    admin = servicos_teste["admin"]
    fila = servicos_teste["fila"]
    u = auth.cadastrar_usuario("rot_erro2", "SenhaForte123")
    pool = _criar_pool_minimo()

    # Todos os 4 videos alocados como principais -> 0 reserva
    tarefa = admin.criar_nova_tarefa(
        usuario_administrador_id=int(u["usuario_id"]),
        pool_videos=pool,
        quantidade_videos_principal=4,
        permitir_admin_como_rotulador=True,
    )
    t_id = int(tarefa["tarefa_id"])
    estado = fila.obter_estado_fila(t_id, "rot_erro2", aviso_sensivel_aceito=True)
    vid = estado["video_atual"]

    resultado = fila.reportar_erro_video(
        tarefa_id=t_id,
        nome_usuario="rot_erro2",
        assignment_id=vid["assignment_id"],
        tempo_analise_segundos=12.0,
    )
    assert resultado["status_substituicao"] in ("SEM_RESERVA_DISPONIVEL", "SUBSTITUIDO_SEM_RESERVA", "REGISTRADO_SEM_SUBSTITUICAO")
    assert resultado["erro_registrado"] is not None


# ==============================================================================
# 4. EXCLUSAO DE TAREFAS: PERMISSOES E INTEGRIDADE
# ==============================================================================

@pytest.mark.unit
def test_excluir_tarefa_inexistente_lanca_value_error(servicos_teste: Dict[str, Any]):
    """Garante que tentar excluir tarefa com ID inexistente levanta ValueError amigavel."""
    admin = servicos_teste["admin"]
    with pytest.raises(ValueError, match="não encontrada"):
        admin.excluir_tarefa(tarefa_id=999999, usuario_administrador_id=1)


@pytest.mark.unit
def test_excluir_tarefa_por_usuario_nao_administrador_lanca_permission_error(servicos_teste: Dict[str, Any]):
    """Garante que usuarios sem papel de administrador da tarefa sao impedidos de exclui-la."""
    auth = servicos_teste["auth"]
    admin = servicos_teste["admin"]
    pool = _criar_pool_minimo()

    admin_u = auth.cadastrar_usuario("admin_legitimo", "SenhaForte123")
    rotulador_u = auth.cadastrar_usuario("rotulador_comum", "SenhaForte123")

    tarefa = admin.criar_nova_tarefa(
        usuario_administrador_id=int(admin_u["usuario_id"]),
        pool_videos=pool,
        permitir_admin_como_rotulador=False,
    )
    t_id = int(tarefa["tarefa_id"])

    with pytest.raises(PermissionError, match="Apenas o administrador da tarefa pode excluí-la"):
        admin.excluir_tarefa(tarefa_id=t_id, usuario_administrador_id=int(rotulador_u["usuario_id"]))


# ==============================================================================
# 5. INGRESSO VIA CONVITE: CODIGO INEXISTENTE E LOTACAO DE VAGAS
# ==============================================================================

@pytest.mark.unit
def test_entrar_tarefa_codigo_convite_inexistente_lanca_erro(servicos_teste: Dict[str, Any]):
    """Garante que codigo de convite incorreto levanta erro amigavel."""
    auth = servicos_teste["auth"]
    u = auth.cadastrar_usuario("usuario_convite_inv", "SenhaForte123")

    with pytest.raises(ValueError, match="Nenhuma tarefa encontrada"):
        auth.entrar_na_tarefa_por_convite(int(u["usuario_id"]), "CONVITE_INVENTADO_12345")


@pytest.mark.unit
def test_entrar_tarefa_usuario_inexistente_lanca_erro(servicos_teste: Dict[str, Any]):
    """Garante que usuario inexistente nao pode ingressar em tarefas."""
    auth = servicos_teste["auth"]
    with pytest.raises(ValueError, match="Usuário não encontrado"):
        auth.entrar_na_tarefa_por_convite(usuario_id=999999, codigo_convite="QUALQUER-CONVITE")


@pytest.mark.unit
def test_entrar_tarefa_codigo_convite_vazio_lanca_erro(servicos_teste: Dict[str, Any]):
    """Garante que codigo de convite vazio ou composto apenas por espacos e rejeitado."""
    auth = servicos_teste["auth"]
    u = auth.cadastrar_usuario("usuario_convite_vazio", "SenhaForte123")
    with pytest.raises(ValueError, match="pelo menos 4 caracteres"):
        auth.entrar_na_tarefa_por_convite(int(u["usuario_id"]), "   ")


@pytest.mark.unit
def test_entrar_tarefa_ja_inscrito_reaproveita_sem_duplicar(servicos_teste: Dict[str, Any]):
    """Garante que tentar ingressar repetidas vezes na mesma tarefa preserva a vinculacao e nao duplica membros."""
    auth = servicos_teste["auth"]
    admin = servicos_teste["admin"]
    pool = _criar_pool_minimo()

    adm = auth.cadastrar_usuario("adm_tarefa_dupla", "SenhaForte123")
    user = auth.cadastrar_usuario("rot_duplo", "SenhaForte123")

    tarefa = admin.criar_nova_tarefa(
        usuario_administrador_id=int(adm["usuario_id"]),
        pool_videos=pool,
        numero_vagas=2,
        permitir_admin_como_rotulador=False,
    )
    t_convite = tarefa["codigo_convite"]

    # Primeiro ingresso
    res1 = auth.entrar_na_tarefa_por_convite(int(user["usuario_id"]), t_convite)
    assert res1["tarefa_id"] == tarefa["tarefa_id"]

    # Segundo ingresso com o mesmo codigo
    res2 = auth.entrar_na_tarefa_por_convite(int(user["usuario_id"]), t_convite)
    assert res2["tarefa_id"] == tarefa["tarefa_id"]

    # Verifica que o usuario permanece exatamente uma vez como membro
    membros = auth.repo_usuarios.listar_membros_da_tarefa(tarefa["tarefa_id"])
    membros_user = [m for m in membros if int(m["usuario_id"]) == int(user["usuario_id"])]
    assert len(membros_user) == 1


# ==============================================================================
# 6. AUTENTICACAO: SENHA INCORRETA EM SESSAO ATIVA NAO DERRUBA USUARIO LEGITIMO
# ==============================================================================

@pytest.mark.unit
def test_tentativa_login_senha_errada_com_sessao_ativa_nao_rouba_sessao(servicos_teste: Dict[str, Any]):
    """Garante que tentativa de login com senha incorreta nao derruba nem reassume sessao ativa de outro."""
    auth = servicos_teste["auth"]
    auth.cadastrar_usuario("usuario_protegido", "SenhaGenuina123")

    # Usuario genuino loga e mantem sessao ativa
    sessao_genuina = auth.autenticar_usuario("usuario_protegido", "SenhaGenuina123", exigir_sessao_unica=True)
    assert sessao_genuina["nome_usuario"] == "usuario_protegido"

    # Tentativa com senha errada com permitir_reassumir=True DEVE falhar por senha invalida
    with pytest.raises(ValueError, match="Credenciais inválidas"):
        auth.autenticar_usuario(
            "usuario_protegido", "SenhaTotalmenteErrada", permitir_reassumir=True
        )


# ==============================================================================
# 7. FUNCOES AUXILIARES DE ENTRADA DO FRONTEND: ROBUSTEZ FRENTE A DADOS CORROMPIDOS
# ==============================================================================

@pytest.mark.unit
def test_ui_converter_df_para_distancias_dados_corrompidos_retorna_dicionario_seguro():
    """Garante que o conversor da UI nao estoura excecoes frente a None, tipos incorretos ou DFs vazios."""
    assert converter_df_para_distancias(None) == {}
    assert converter_df_para_distancias("invalido") == {}
    assert converter_df_para_distancias([]) == {}
    assert converter_df_para_distancias(pd.DataFrame()) == {}
    # DataFrame com colunas ausentes
    df_incompleto = pd.DataFrame([{"ColunaErrada": 123}])
    assert converter_df_para_distancias(df_incompleto) == {}


@pytest.mark.unit
def test_ui_gerar_tabela_penalidades_df_texto_insuficiente_retorna_vazio():
    """Garante que opcoes vazias ou com menos de 2 linhas retornam DataFrame vazio seguro."""
    df_vazio = gerar_tabela_penalidades_df("")
    assert df_vazio.empty
    assert list(df_vazio.columns) == ["Opção A", "Opção B", "Penalidade"]

    df_um = gerar_tabela_penalidades_df("Apenas Uma Opção")
    assert df_um.empty


# ==============================================================================
# 8. PREVENCAO DE REGRESSAO DE BUGS ESPECIFICOS REPORTADOS PELO USUARIO
# ==============================================================================

@pytest.mark.unit
def test_regressao_configuracao_admin_alto_contraste_sem_black_box():
    """Garante que a configuracao vigente do admin utiliza HTML com pills e classes dedicadas sem crases de markdown."""
    meta = {
        "tarefa_id": 42,
        "codigo_convite": "TOK-99887766",
        "pergunta": 'Qual a posição sobre "{target}"?',
        "opcoes_posicao": ["Contra", "A favor", "Neutro"],
        "numero_vagas": 3,
        "percentual_sobreposicao": 20.0,
    }
    html = renderizar_configuracao_admin_html(meta)
    # Nao deve conter marcacoes de crase de markdown que geram caixas escuras opacas
    assert "`" not in html
    # Deve conter componentes estruturados de alto contraste
    assert "admin-config-card" in html
    assert "config-val-badge convite" in html
    assert "TOK-99887766" in html
    assert "#42" in html
    assert "config-val-text" in html


@pytest.mark.unit
def test_regressao_tema_css_alinhamento_hub_e_overlay_sensivel():
    """Garante regras CSS criticas para alinhamento de botoes, duas colunas e overlay sem rolagem."""
    # Verificacao do layout em duas colunas lado a lado
    assert ".hub-two-col" in APP_CSS
    assert "display: flex !important;" in APP_CSS
    # Verificacao de alinhamento inferior dos botoes e inputs no hub
    assert ".hub-action-row" in APP_CSS
    assert "align-items: flex-end !important;" in APP_CSS
    assert ".hub-btn" in APP_CSS
    assert "height: 42px !important;" in APP_CSS
    # Verificacao do modal sensivel como overlay fixo sem esticar a arvore DOM
    assert ".sensitive-warning-wrapper" in APP_CSS
    assert "position: fixed !important;" in APP_CSS
    assert "z-index: 99999 !important;" in APP_CSS
    # Verificacao do botao de sair do workspace
    assert ".labeler-exit-btn" in APP_CSS
    assert "margin-left: auto !important;" in APP_CSS
    assert "#9c0014" in APP_CSS
    # Verificacao do suporte e harmonia para resolucoes Widescreen
    assert ".wizard-grid" in APP_CSS
    assert ".hub-join-box" in APP_CSS
    assert "width: min(98%, 1880px)" in APP_CSS


@pytest.mark.unit
def test_regressao_tiktok_player_altura_contida():
    """Garante que o iframe do TikTok acompanha a altura da janela em proporcao 9:16 sem rolagem."""
    player_html = render_tiktok("https://www.tiktok.com/@canal/video/7123456789")
    assert "height: var(--altura-player, 500px);" in player_html
    assert "* 0.5625" in player_html
    assert "scrolling=\"no\"" in player_html


#password recovery and email validation

@pytest.mark.unit
def test_validar_email_valido_e_invalido():
    """Valida formato de e-mail e rejeita cadeias mal formatadas."""
    from tokstance.backend.security.validators import validar_email

    assert validar_email("usuario@dominio.com") == "usuario@dominio.com"
    assert validar_email("  GUSTAVO@dcc.ufmg.br  ") == "gustavo@dcc.ufmg.br"
    assert validar_email("pesquisador+rotulo@sub.dominio.org") == "pesquisador+rotulo@sub.dominio.org"

    with pytest.raises(ValueError, match="Informe um endereço de e-mail válido"):
        validar_email("email_sem_arroba.com")

    with pytest.raises(ValueError, match="Informe um endereço de e-mail válido"):
        validar_email("@dominio.com")

    with pytest.raises(ValueError, match="Informe um endereço de e-mail válido"):
        validar_email("usuario@")

    with pytest.raises(ValueError, match="Informe um endereço de e-mail válido"):
        validar_email("usuario@dominio")


@pytest.mark.unit
def test_recuperacao_senha_fluxo_completo_e_caminhos_infelizes(servicos_teste: Dict[str, Any]):
    """Testa recuperacao de senha via codigo de 6 digitos e prevencao de falhas."""
    auth = servicos_teste["auth"]
    # 1. Cadastro com email
    u = auth.cadastrar_usuario("pesquisador_rec", "SenhaAntiga123", email="recupera@exemplo.org")
    assert u["email"] == "recupera@exemplo.org"

    # 2. Caminho infeliz: solicitacao com identificador inexistente
    with pytest.raises(ValueError, match="Nenhum usuário cadastrado encontrado"):
        auth.solicitar_recuperacao_senha("usuario_fantasma_xyz")

    # 3. Solicitacao valida por nome de usuario e por e-mail
    solic1 = auth.solicitar_recuperacao_senha("pesquisador_rec")
    assert solic1["sucesso"] is True
    assert len(solic1["codigo"]) == 6
    assert solic1["codigo"].isdigit()

    solic2 = auth.solicitar_recuperacao_senha("recupera@exemplo.org")
    assert solic2["sucesso"] is True
    assert len(solic2["codigo"]) == 6

    codigo_valido = solic2["codigo"]

    # 4. Caminho infeliz: codigo incorreto
    with pytest.raises(ValueError, match="Código de recuperação inválido ou expirado"):
        auth.redefinir_senha_com_codigo("pesquisador_rec", "999999", "NovaSenha123")

    # 5. Caminho infeliz: senha muito curta (< 6 caracteres)
    with pytest.raises(ValueError, match="pelo menos 6 caracteres"):
        auth.redefinir_senha_com_codigo("pesquisador_rec", codigo_valido, "123")

    # 6. Caminho feliz: redefinicao com codigo valido
    res = auth.redefinir_senha_com_codigo("recupera@exemplo.org", codigo_valido, "NovaSenhaSegura123")
    assert res["sucesso"] is True

    # 7. Login com nova senha deve funcionar; login com senha antiga deve ser rejeitado
    auth_nova = auth.autenticar_usuario("pesquisador_rec", "NovaSenhaSegura123")
    assert auth_nova["usuario_id"] == u["usuario_id"]

    with pytest.raises(ValueError, match="Credenciais inválidas"):
        auth.autenticar_usuario("pesquisador_rec", "SenhaAntiga123")

    # 8. Caminho infeliz: codigo ja consumido nao pode ser reutilizado
    with pytest.raises(ValueError, match="Código de recuperação inválido ou expirado"):
        auth.redefinir_senha_com_codigo("pesquisador_rec", codigo_valido, "OutraSenha123")


# ==============================================================================
# 10. TABELAS MODERNAS DO HUB E BOTOES DINAMICOS DE ROTULACAO
# ==============================================================================

@pytest.mark.unit
def test_renderizar_hub_tabelas_botoes_dinamicos_progresso():
    """Garante que os botoes mudam dinamicamente entre Iniciar, Continuar e Ver Concluida."""
    from tokstance.frontend.gradio_ui import renderizar_hub_tabelas_html

    # Caso 1: Nenhuma anotação iniciada (pos = 0)
    t_rot_zero = [{"tarefa_id": 10, "titulo": "Tarefa Nova", "videos_concluidos": 0, "total_videos_fila": 15}]
    _, h_rot_zero = renderizar_hub_tabelas_html([], t_rot_zero)
    assert "▶ Iniciar Rotulação" in h_rot_zero
    assert "Não iniciada" in h_rot_zero
    assert "hub-table-btn primary" in h_rot_zero

    # Caso 2: Em andamento (0 < pos < tot)
    t_rot_meio = [{"tarefa_id": 10, "titulo": "Tarefa Em Andamento", "videos_concluidos": 7, "total_videos_fila": 15}]
    _, h_rot_meio = renderizar_hub_tabelas_html([], t_rot_meio)
    assert "▶ Continuar Rotulação" in h_rot_meio
    assert "Em andamento" in h_rot_meio
    assert "hub-table-btn in-progress" in h_rot_meio

    # Caso 3: Concluída (pos >= tot)
    t_rot_fim = [{"tarefa_id": 10, "titulo": "Tarefa Finalizada", "videos_concluidos": 15, "total_videos_fila": 15}]
    _, h_rot_fim = renderizar_hub_tabelas_html([], t_rot_fim)
    assert "✓ Ver Concluída" in h_rot_fim
    assert "Concluída" in h_rot_fim
    assert "hub-table-btn completed" in h_rot_fim


@pytest.mark.unit
def test_renderizar_hub_tabelas_acoes_administrador():
    """Garante presenca dos botoes de Abrir Console e Excluir nas tarefas administradas."""
    from tokstance.frontend.gradio_ui import renderizar_hub_tabelas_html

    t_adm = [{
        "tarefa_id": 42,
        "titulo": "Pesquisa Política 2026",
        "codigo_convite": "TOK-ABCD1234",
        "vagas_ocupadas": 2,
        "numero_vagas": 5,
        "progresso_percentual": 40.0,
    }]
    h_adm, _ = renderizar_hub_tabelas_html(t_adm, [])
    assert "Abrir Console" in h_adm
    assert "Excluir</button>" in h_adm
    assert "TOK-ABCD1234" in h_adm
    assert "2 de 5" in h_adm
    assert "40%" in h_adm
    assert "tokstanceAcao('admin', '42')" in h_adm
    assert "tokstanceAcao('excluir', '42')" in h_adm
    assert "<select" not in h_adm  # Sem menus suspensos na tabela


@pytest.mark.unit
def test_regressao_modal_sensivel_altura_contida_css():
    """Garante que a folha de estilo restringe a altura do modal sensivel evitando o bug de esticamento vertical."""
    assert ".sensitive-warning-wrapper" in APP_CSS
    assert "overflow: hidden !important;" in APP_CSS
    assert ".sensitive-warning-card" in APP_CSS
    assert "height: fit-content !important;" in APP_CSS
    assert "max-height: fit-content !important;" in APP_CSS
    assert "flex: 0 0 auto !important;" in APP_CSS
