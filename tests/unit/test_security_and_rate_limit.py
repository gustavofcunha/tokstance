"""Testes unitarios para limitador de tentativas de login e bloqueio de sessao simultanea."""

from typing import Any

import pytest

from tokstance.backend.security.rate_limit import (
    GerenciadorSessoesAtivas,
    LimitadorTentativas,
    limpar_sessoes_ativas,
    listar_usuarios_ativos,
    liberar_sessao_ativa,
    reivindicar_sessao_ativa,
    usuario_esta_ativo,
)


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
