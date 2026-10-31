"""Testes unitarios para hashing de senha, complexidade e validadores de entrada."""

import pytest

from tokstance.backend.security.password import (
    gerar_hash_senha,
    validar_complexidade_senha,
    verificar_senha,
)
from tokstance.backend.security.validators import (
    gerar_codigo_convite,
    validar_codigo_convite,
    validar_nome_usuario,
    validar_opcoes_tarefa,
)


@pytest.mark.unit
def test_gerar_hash_senha_com_senha_valida_produz_hash_diferente_e_verificavel() -> None:
    senha_plana = "Segura2026!"

    hash_1 = gerar_hash_senha(senha_plana, rodadas=4)
    hash_2 = gerar_hash_senha(senha_plana, rodadas=4)

    assert hash_1 != senha_plana
    assert hash_1 != hash_2
    assert verificar_senha(senha_plana, hash_1) is True
    assert verificar_senha(senha_plana, hash_2) is True


@pytest.mark.unit
def test_verificar_senha_com_senha_incorreta_ou_vazia_retorna_falso() -> None:
    hash_valido = gerar_hash_senha("Correta123", rodadas=4)

    resultado_errada = verificar_senha("Errada123", hash_valido)
    resultado_vazia = verificar_senha("", hash_valido)
    resultado_hash_invalido = verificar_senha("Correta123", "hash-malformado")

    assert resultado_errada is False
    assert resultado_vazia is False
    assert resultado_hash_invalido is False


@pytest.mark.unit
def test_validar_complexidade_senha_curta_levanta_erro() -> None:
    senha_curta = "Ab12"

    with pytest.raises(ValueError, match="no mínimo"):
        validar_complexidade_senha(senha_curta)


@pytest.mark.unit
def test_validar_complexidade_senha_sem_numero_ou_sem_letra_levanta_erro() -> None:
    senha_apenas_letras = "ApenasLetras"
    senha_apenas_numeros = "12345678"

    with pytest.raises(ValueError, match="letra e um número"):
        validar_complexidade_senha(senha_apenas_letras)

    with pytest.raises(ValueError, match="letra e um número"):
        validar_complexidade_senha(senha_apenas_numeros)


@pytest.mark.unit
def test_validar_nome_usuario_valido_remove_espacos_nas_bordas() -> None:
    entrada = "  rotulador_ufmg.01-br  "

    normalizado = validar_nome_usuario(entrada)

    assert normalizado == "rotulador_ufmg.01-br"


@pytest.mark.unit
def test_validar_nome_usuario_com_prefixo_reservado_vaga_levanta_erro() -> None:
    nome_reservado = "vaga_1"

    with pytest.raises(ValueError, match="reservado"):
        validar_nome_usuario(nome_reservado)


@pytest.mark.unit
def test_validar_nome_usuario_com_caracteres_especiais_levanta_erro() -> None:
    nome_malicioso = "admin' OR '1'='1"

    with pytest.raises(ValueError, match="apenas letras, números"):
        validar_nome_usuario(nome_malicioso)


@pytest.mark.unit
def test_gerar_e_validar_codigo_convite_produz_token_formatado_e_unico() -> None:
    codigo_1 = gerar_codigo_convite("UFMG")
    codigo_2 = gerar_codigo_convite("UFMG")

    validado_1 = validar_codigo_convite(codigo_1)
    validado_2 = validar_codigo_convite(codigo_2)

    assert validado_1.startswith("UFMG-")
    assert validado_1 != validado_2


@pytest.mark.unit
def test_validar_codigo_convite_curto_ou_invalido_levanta_erro() -> None:
    codigo_curto = "AB"
    codigo_com_espaco = "TOK 2026!"

    with pytest.raises(ValueError, match="pelo menos 4"):
        validar_codigo_convite(codigo_curto)

    with pytest.raises(ValueError, match="apenas letras, números"):
        validar_codigo_convite(codigo_com_espaco)


@pytest.mark.unit
def test_validar_opcoes_tarefa_rejeita_menos_de_duas_opcoes_ou_caractere_pipe() -> None:
    opcoes_validas = validar_opcoes_tarefa("A Favor, Contra, Neutro, Contra")

    assert opcoes_validas == ["A Favor", "Contra", "Neutro"]

    with pytest.raises(ValueError, match="pelo menos 2"):
        validar_opcoes_tarefa(["Apenas Uma"])

    with pytest.raises(ValueError, match="caractere '|'"):
        validar_opcoes_tarefa(["Opcao A", "Opcao|B"])
