"""Hashing seguro de senhas com bcrypt e validacao de complexidade."""

import bcrypt

from tokstance.config import TAMANHO_MAXIMO_SENHA, TAMANHO_MINIMO_SENHA

# Hash pre-computado de 12 rodadas para verificacao em tempo constante e prevencao de timing attack
HASH_DUMMY_BCRYPT = "$2b$12$e8whpUfGsmfFknFq92UjIeOqI7Vv75yCq9Xm9G5tUe3g2v6u1hW2K"


def validar_complexidade_senha(senha: str) -> str:
    """Valida comprimento e requisitos minimos de seguranca de uma senha."""
    if not isinstance(senha, str):
        raise ValueError("A senha informada é inválida.")
    limpa = senha.strip()
    if len(limpa) < TAMANHO_MINIMO_SENHA:
        raise ValueError(
            f"A senha deve ter no mínimo {TAMANHO_MINIMO_SENHA} caracteres."
        )
    if len(senha) > TAMANHO_MAXIMO_SENHA:
        raise ValueError(
            f"A senha não pode exceder {TAMANHO_MAXIMO_SENHA} caracteres."
        )
    possui_letra = any(caractere.isalpha() for caractere in limpa)
    possui_digito = any(caractere.isdigit() for caractere in limpa)
    if not (possui_letra and possui_digito):
        raise ValueError("A senha deve conter ao menos uma letra e um número.")
    return senha


def gerar_hash_senha(senha: str, rodadas: int = 12) -> str:
    """Valida a senha e gera um hash bcrypt com sal aleatorio."""
    senha_validada = validar_complexidade_senha(senha)
    sal = bcrypt.gensalt(rounds=max(4, min(14, int(rodadas))))
    #hashing salgado em tempo constante via bcrypt
    digest = bcrypt.hashpw(senha_validada.encode("utf-8"), sal)
    return digest.decode("utf-8")


def verificar_senha(senha_texto_plano: str, senha_hash: str) -> bool:
    """Verifica em tempo constante se a senha em texto plano corresponde ao hash."""
    if not isinstance(senha_texto_plano, str) or not isinstance(senha_hash, str):
        return False
    if not senha_texto_plano or not senha_hash.strip():
        return False
    if len(senha_texto_plano) > TAMANHO_MAXIMO_SENHA:
        return False
    try:
        return bool(
            bcrypt.checkpw(
                senha_texto_plano.encode("utf-8"),
                senha_hash.strip().encode("utf-8"),
            )
        )
    except ValueError:
        return False
