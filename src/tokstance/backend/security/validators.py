"""Validadores de entrada, sanitizacao de nome de usuario, codigos de convite e limites anti-DoS."""

import re
import secrets

from tokstance.backend.domain.models import limpar_usuarios
from tokstance.config import (
    TAMANHO_MAXIMO_CAMPO_TEXTO,
    TAMANHO_MAXIMO_USUARIO,
)

PADRAO_NOME_USUARIO = re.compile(r"^[A-Za-z0-9_.\-]+$")
PADRAO_CODIGO_CONVITE = re.compile(r"^[A-Za-z0-9_\-]+$")
PADRAO_EMAIL = re.compile(r"^[\w\.\+\-]+@[a-zA-Z0-9\-]+(\.[a-zA-Z0-9\-]+)+$")


def validar_email(email: str) -> str:
    """Valida e normaliza um endereco de e-mail para cadastro e recuperacao."""
    limpo = str(email or "").strip().lower()
    if not limpo:
        raise ValueError("O endereço de e-mail é obrigatório.")
    if len(limpo) > 120 or not PADRAO_EMAIL.match(limpo):
        raise ValueError("Informe um endereço de e-mail válido (exemplo: usuario@dominio.com).")
    return limpo


def validar_tamanho_texto(
    valor: str,
    nome_campo: str = "campo",
    tamanho_maximo: int = TAMANHO_MAXIMO_CAMPO_TEXTO,
) -> str:
    """Garante que uma string nao contem bytes nulos nem excede o limite maximo de caracteres."""
    if not isinstance(valor, str):
        raise ValueError(f"O valor de {nome_campo} é inválido.")
    if "\x00" in valor:
        raise ValueError(f"O valor de {nome_campo} contém caracteres inválidos.")
    texto = valor.strip()
    if len(texto) > int(tamanho_maximo):
        raise ValueError(
            f"O campo {nome_campo} excede o limite de {tamanho_maximo} caracteres."
        )
    return texto


def validar_nome_usuario(nome_usuario: str) -> str:
    """Valida e normaliza um identificador de usuario contra caracteres invalidos e prefixos reservados."""
    limpo = validar_tamanho_texto(
        nome_usuario,
        nome_campo="nome_usuario",
        tamanho_maximo=TAMANHO_MAXIMO_USUARIO,
    )
    if len(limpo) < 3:
        raise ValueError("O nome de usuário deve ter pelo menos 3 caracteres.")
    if not PADRAO_NOME_USUARIO.match(limpo):
        raise ValueError(
            "O nome de usuário deve conter apenas letras, números, ponto, hífen ou sublinhado."
        )
    if limpo.lower().startswith("vaga_"):
        raise ValueError("O prefixo 'vaga_' é reservado pelo sistema.")
    return limpo


def gerar_codigo_convite(prefixo: str = "TOK") -> str:
    """Gera um codigo de convite aleatorio seguro para uma nova tarefa."""
    prefixo_limpo = re.sub(r"[^A-Za-z0-9]", "", str(prefixo or "TOK")).upper()[:8] or "TOK"
    sufixo = secrets.token_hex(4).upper()
    return f"{prefixo_limpo}-{sufixo}"


def validar_codigo_convite(codigo_convite: str) -> str:
    """Valida o formato e comprimento de um codigo de convite."""
    limpo = validar_tamanho_texto(
        codigo_convite,
        nome_campo="codigo_convite",
        tamanho_maximo=TAMANHO_MAXIMO_USUARIO,
    )
    if len(limpo) < 4:
        raise ValueError("O código de convite deve ter pelo menos 4 caracteres.")
    if not PADRAO_CODIGO_CONVITE.match(limpo):
        raise ValueError(
            "O código de convite deve conter apenas letras, números, hífen ou sublinhado."
        )
    return limpo


def validar_opcoes_tarefa(
    opcoes: list[str] | tuple[str, ...] | str,
) -> list[str]:
    """Normaliza e valida a lista de respostas possiveis de uma tarefa."""
    if isinstance(opcoes, str):
        validar_tamanho_texto(
            opcoes,
            nome_campo="opcoes_posicao",
            tamanho_maximo=TAMANHO_MAXIMO_CAMPO_TEXTO * 4,
        )
    normalizadas = limpar_usuarios(opcoes)
    if len(normalizadas) < 2:
        raise ValueError("A tarefa deve possuir pelo menos 2 opções de resposta distintas.")
    validas: list[str] = []
    for opcao in normalizadas:
        opcao_limpa = validar_tamanho_texto(
            opcao,
            nome_campo="opcao_resposta",
            tamanho_maximo=120,
        )
        if "|" in opcao_limpa:
            raise ValueError("As opções de resposta não podem conter o caractere '|'.")
        validas.append(opcao_limpa)
    return validas

