"""Camada ativa de protecao contra SQL Injection, sanitizacao estrita e prevencao de ataques a banco."""

from __future__ import annotations

import re
import unicodedata

# Padroes compilados de ataque de injecao SQL conhecidos (OWASP Injection Cheat Sheet)
_PADROES_SQLI = [
    re.compile(r"\bUNION(\s+ALL)?\s+SELECT\b", re.IGNORECASE),
    re.compile(r"\b(DROP|ALTER|TRUNCATE)\s+TABLE\b", re.IGNORECASE),
    re.compile(r"\bINSERT\s+INTO\b", re.IGNORECASE),
    re.compile(r";\s*(DELETE|DROP|INSERT|UPDATE|ALTER|SELECT)\b", re.IGNORECASE),
    re.compile(r"\b(OR|AND)\s+['\"]?[\w\d]+['\"]?\s*=\s*['\"]?[\w\d]+['\"]?", re.IGNORECASE),
    re.compile(r"(--|/\*|\*/|#)", re.IGNORECASE),
    re.compile(r"\b(XP_CMDSHELL|EXEC|EXECUTE)\b", re.IGNORECASE),
    re.compile(r"\b(SLEEP|BENCHMARK)\s*\(", re.IGNORECASE),
]


def detectar_tentativa_sqli(texto: str) -> bool:
    """Retorna True se a string informada contiver assinaturas caracteristicas de ataque SQLi."""
    if not isinstance(texto, str) or not texto.strip():
        return False

    texto_limpo = texto.strip()
    return any(padrao.search(texto_limpo) is not None for padrao in _PADROES_SQLI)


def sanitizar_texto_seguro(
    valor: str,
    tamanho_maximo: int = 512,
) -> str:
    """Normaliza texto para Unicode NFC, remove bytes nulos e caracteres de controle perigosos."""
    if not isinstance(valor, str):
        raise ValueError("O valor informado não é uma string válida.")

    if "\x00" in valor:
        raise ValueError("O valor informado contém caracteres nulos inválidos.")

    # Normalizacao Unicode padrao canônico
    texto_norm = unicodedata.normalize("NFC", valor)

    # Filtrar caracteres de controle invisiveis (exceto espaco, tab, quebra de linha)
    filtrado = "".join(
        ch for ch in texto_norm if unicodedata.category(ch) != "Cc" or ch in ("\n", "\r", "\t")
    ).strip()

    if len(filtrado) > int(tamanho_maximo):
        raise ValueError(f"O campo excede o limite máximo permitido de {tamanho_maximo} caracteres.")

    return filtrado


def validar_campo_seguro(
    valor: str,
    nome_campo: str = "campo",
    tamanho_maximo: int = 512,
    bloquear_sqli: bool = True,
) -> str:
    """Sanitiza e valida campos estruturados contra sobrecarga e tentativas de injecao SQL."""
    texto_limpo = sanitizar_texto_seguro(valor, tamanho_maximo=tamanho_maximo)

    if bloquear_sqli and detectar_tentativa_sqli(texto_limpo):
        raise ValueError(
            f"O valor informado para {nome_campo} contém caracteres ou padrões não permitidos por segurança."
        )

    return texto_limpo

