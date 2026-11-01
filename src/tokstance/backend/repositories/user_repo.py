"""Repositorio relacional de contas de usuarios e associacao multi-papel por tarefa."""

import json
import sqlite3
from typing import Any

from tokstance.backend.domain.models import PAPEIS_VALIDOS
from tokstance.backend.repositories.database import BancoDadosSQLite
from tokstance.backend.security.validators import validar_nome_usuario
from tokstance.config import formatar_data_hora_brt


class RepositorioUsuarios:
    """Gerencia a persistencia de usuarios e seus papeis por tarefa no SQLite."""

    def __init__(self, banco: BancoDadosSQLite | None = None) -> None:
        self.banco = banco or BancoDadosSQLite()

    def criar_usuario(
        self,
        nome_usuario: str,
        senha_hash: str,
        email: str = "",
        criado_em: str | None = None,
    ) -> dict[str, Any]:
        """Registra um novo usuario na tabela usuarios e retorna seus dados."""
        nome_limpo = validar_nome_usuario(nome_usuario)
        if not isinstance(senha_hash, str) or not senha_hash.strip():
            raise ValueError("O hash da senha é obrigatório.")
        email_limpo = str(email or "").strip().lower()
        instante = str(criado_em or formatar_data_hora_brt())
        try:
            usuario_id = self.banco.executar(
                """
                INSERT INTO usuarios (nome_usuario, email, senha_hash, criado_em)
                VALUES (?, ?, ?, ?);
                """,
                (nome_limpo, email_limpo, senha_hash.strip(), instante),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"O nome de usuário '{nome_limpo}' já está cadastrado.") from exc

        criado = self.buscar_por_id(usuario_id)
        if criado is None:
            raise RuntimeError("Falha ao recuperar usuário recém-criado.")
        return criado

    def buscar_por_nome_usuario(self, nome_usuario: str) -> dict[str, Any] | None:
        """Busca um usuario pelo nome de usuario usando consulta parametrizada."""
        if not isinstance(nome_usuario, str) or not nome_usuario.strip():
            return None
        return self.banco.consultar_um(
            """
            SELECT usuario_id, nome_usuario, email, senha_hash, criado_em
            FROM usuarios
            WHERE nome_usuario = ?;
            """,
            (nome_usuario.strip(),),
        )

    def buscar_por_email(self, email: str) -> dict[str, Any] | None:
        """Busca um usuario pelo endereco de e-mail cadastrado."""
        if not isinstance(email, str) or not email.strip():
            return None
        return self.banco.consultar_um(
            """
            SELECT usuario_id, nome_usuario, email, senha_hash, criado_em
            FROM usuarios
            WHERE LOWER(email) = ?;
            """,
            (email.strip().lower(),),
        )

    def buscar_por_id(self, usuario_id: int) -> dict[str, Any] | None:
        """Busca um usuario pela chave primaria usuario_id."""
        return self.banco.consultar_um(
            """
            SELECT usuario_id, nome_usuario, email, senha_hash, criado_em
            FROM usuarios
            WHERE usuario_id = ?;
            """,
            (int(usuario_id),),
        )

    def atualizar_senha(self, usuario_id: int, nova_senha_hash: str) -> bool:
        """Atualiza a senha hash de um usuario existente."""
        if not isinstance(nova_senha_hash, str) or not nova_senha_hash.strip():
            raise ValueError("O hash da nova senha é obrigatório.")
        linhas = self.banco.executar(
            """
            UPDATE usuarios
            SET senha_hash = ?
            WHERE usuario_id = ?;
            """,
            (nova_senha_hash.strip(), int(usuario_id)),
        )
        return linhas > 0

    def salvar_codigo_recuperacao(
        self,
        usuario_id: int,
        codigo_recuperacao: str,
        expira_em: str,
    ) -> int:
        """Armazena um codigo de recuperacao para o usuario."""
        instante = formatar_data_hora_brt()
        # Invalida codigos anteriores nao usados
        self.banco.executar(
            """
            UPDATE recuperacao_senha
            SET usado = 1
            WHERE usuario_id = ? AND usado = 0;
            """,
            (int(usuario_id),),
        )
        return self.banco.executar(
            """
            INSERT INTO recuperacao_senha (usuario_id, codigo_recuperacao, expira_em, usado, criado_em)
            VALUES (?, ?, ?, 0, ?);
            """,
            (int(usuario_id), str(codigo_recuperacao).strip(), str(expira_em), instante),
        )

    def validar_codigo_recuperacao(
        self,
        usuario_id: int,
        codigo_recuperacao: str,
    ) -> bool:
        """Verifica se o codigo de recuperacao e valido, nao usado e dentro do prazo."""
        registro = self.banco.consultar_um(
            """
            SELECT recuperacao_id, expira_em, usado
            FROM recuperacao_senha
            WHERE usuario_id = ? AND codigo_recuperacao = ? AND usado = 0
            ORDER BY recuperacao_id DESC
            LIMIT 1;
            """,
            (int(usuario_id), str(codigo_recuperacao).strip()),
        )
        if registro is None:
            return False
        agora = formatar_data_hora_brt()
        return str(agora) <= str(registro["expira_em"])

    def consumir_codigo_recuperacao(
        self,
        usuario_id: int,
        codigo_recuperacao: str,
    ) -> None:
        """Marca o codigo de recuperacao como utilizado."""
        self.banco.executar(
            """
            UPDATE recuperacao_senha
            SET usado = 1
            WHERE usuario_id = ? AND codigo_recuperacao = ?;
            """,
            (int(usuario_id), str(codigo_recuperacao).strip()),
        )

    def listar_usuarios(self) -> list[dict[str, Any]]:
        """Retorna todos os usuarios cadastrados em ordem de criacao."""
        return self.banco.consultar_todos(
            """
            SELECT usuario_id, nome_usuario, email, criado_em
            FROM usuarios
            ORDER BY usuario_id ASC;
            """
        )

    def adicionar_membro_tarefa(
        self,
        tarefa_id: int,
        usuario_id: int,
        papel: str,
        vaga_atribuida: str = "",
        entrou_em: str | None = None,
    ) -> dict[str, Any]:
        """Associa um usuario a uma tarefa com papel de administrador ou rotulador."""
        papel_limpo = str(papel or "").strip().lower()
        if papel_limpo not in PAPEIS_VALIDOS:
            raise ValueError(f"Papel inválido '{papel}'. Use 'administrador' ou 'rotulador'.")
        instante = str(entrou_em or formatar_data_hora_brt())
        vaga_limpa = str(vaga_atribuida or "").strip()

        existente = self.buscar_membro_tarefa(
            tarefa_id=int(tarefa_id),
            usuario_id=int(usuario_id),
            papel=papel_limpo,
        )
        if existente is not None:
            if vaga_limpa and existente.get("vaga_atribuida") != vaga_limpa:
                self.banco.executar(
                    """
                    UPDATE membros_tarefa
                    SET vaga_atribuida = ?
                    WHERE membro_id = ?;
                    """,
                    (vaga_limpa, int(existente["membro_id"])),
                )
                atualizado = self.buscar_membro_tarefa(
                    tarefa_id=int(tarefa_id),
                    usuario_id=int(usuario_id),
                    papel=papel_limpo,
                )
                if atualizado is not None:
                    return atualizado
            return existente

        self.banco.executar(
            """
            INSERT INTO membros_tarefa (tarefa_id, usuario_id, papel, vaga_atribuida, entrou_em)
            VALUES (?, ?, ?, ?, ?);
            """,
            (int(tarefa_id), int(usuario_id), papel_limpo, vaga_limpa, instante),
        )
        criado = self.buscar_membro_tarefa(
            tarefa_id=int(tarefa_id),
            usuario_id=int(usuario_id),
            papel=papel_limpo,
        )
        if criado is None:
            raise RuntimeError("Falha ao registrar associação do membro na tarefa.")
        return criado

    def buscar_membro_tarefa(
        self,
        tarefa_id: int,
        usuario_id: int,
        papel: str | None = None,
    ) -> dict[str, Any] | None:
        """Retorna o vinculo de um usuario em uma tarefa, opcionalmente filtrado por papel."""
        if papel is not None:
            return self.banco.consultar_um(
                """
                SELECT m.membro_id, m.tarefa_id, m.usuario_id, u.nome_usuario,
                       m.papel, m.vaga_atribuida, m.entrou_em
                FROM membros_tarefa m
                JOIN usuarios u ON u.usuario_id = m.usuario_id
                WHERE m.tarefa_id = ? AND m.usuario_id = ? AND m.papel = ?;
                """,
                (int(tarefa_id), int(usuario_id), str(papel).strip().lower()),
            )
        return self.banco.consultar_um(
            """
            SELECT m.membro_id, m.tarefa_id, m.usuario_id, u.nome_usuario,
                   m.papel, m.vaga_atribuida, m.entrou_em
            FROM membros_tarefa m
            JOIN usuarios u ON u.usuario_id = m.usuario_id
            WHERE m.tarefa_id = ? AND m.usuario_id = ?
            ORDER BY m.membro_id ASC;
            """,
            (int(tarefa_id), int(usuario_id)),
        )

    def listar_papeis_usuario_na_tarefa(
        self,
        tarefa_id: int,
        usuario_id: int,
    ) -> list[str]:
        """Lista os papeis ('administrador', 'rotulador') que o usuario possui na tarefa."""
        linhas = self.banco.consultar_todos(
            """
            SELECT papel
            FROM membros_tarefa
            WHERE tarefa_id = ? AND usuario_id = ?
            ORDER BY membro_id ASC;
            """,
            (int(tarefa_id), int(usuario_id)),
        )
        return [str(linha["papel"]) for linha in linhas]

    def listar_membros_da_tarefa(
        self,
        tarefa_id: int,
        papel: str | None = None,
    ) -> list[dict[str, Any]]:
        """Lista todos os membros associados a uma tarefa."""
        if papel is not None:
            return self.banco.consultar_todos(
                """
                SELECT m.membro_id, m.tarefa_id, m.usuario_id, u.nome_usuario,
                       m.papel, m.vaga_atribuida, m.entrou_em
                FROM membros_tarefa m
                JOIN usuarios u ON u.usuario_id = m.usuario_id
                WHERE m.tarefa_id = ? AND m.papel = ?
                ORDER BY m.membro_id ASC;
                """,
                (int(tarefa_id), str(papel).strip().lower()),
            )
        return self.banco.consultar_todos(
            """
            SELECT m.membro_id, m.tarefa_id, m.usuario_id, u.nome_usuario,
                   m.papel, m.vaga_atribuida, m.entrou_em
            FROM membros_tarefa m
            JOIN usuarios u ON u.usuario_id = m.usuario_id
            WHERE m.tarefa_id = ?
            ORDER BY m.membro_id ASC;
            """,
            (int(tarefa_id),),
        )

    def _deserializar_item_tarefa(self, linha: dict[str, Any]) -> dict[str, Any]:
        copia = dict(linha)
        if "opcoes_json" in copia:
            try:
                copia["opcoes_posicao"] = json.loads(str(copia.pop("opcoes_json") or "[]"))
            except Exception:
                copia["opcoes_posicao"] = []
        if "distancias_rotulos_json" in copia:
            try:
                copia["distancias_rotulos"] = json.loads(str(copia.pop("distancias_rotulos_json") or "{}"))
            except Exception:
                copia["distancias_rotulos"] = {}
        return copia

    def listar_tarefas_do_usuario(
        self,
        usuario_id: int,
        papel: str | None = None,
    ) -> list[dict[str, Any]]:
        """Retorna todas as tarefas vinculadas ao usuario, com filtro opcional de papel."""
        if papel is not None:
            linhas = self.banco.consultar_todos(
                """
                SELECT t.tarefa_id, t.slug_tarefa, t.titulo, t.pergunta,
                       t.opcoes_json, t.distancias_rotulos_json,
                       t.numero_vagas, t.videos_por_rotulador, t.percentual_sobreposicao,
                       t.codigo_convite, t.versao_atribuicao, t.criado_em,
                       m.papel, m.vaga_atribuida, m.entrou_em
                FROM membros_tarefa m
                JOIN tarefas t ON t.tarefa_id = m.tarefa_id
                WHERE m.usuario_id = ? AND m.papel = ?
                ORDER BY t.tarefa_id DESC;
                """,
                (int(usuario_id), str(papel).strip().lower()),
            )
            return [self._deserializar_item_tarefa(linha) for linha in linhas]
        linhas = self.banco.consultar_todos(
            """
            SELECT t.tarefa_id, t.slug_tarefa, t.titulo, t.pergunta,
                   t.opcoes_json, t.distancias_rotulos_json,
                   t.numero_vagas, t.videos_por_rotulador, t.percentual_sobreposicao,
                   t.codigo_convite, t.versao_atribuicao, t.criado_em,
                   m.papel, m.vaga_atribuida, m.entrou_em
            FROM membros_tarefa m
            JOIN tarefas t ON t.tarefa_id = m.tarefa_id
            WHERE m.usuario_id = ?
            ORDER BY t.tarefa_id DESC, m.membro_id ASC;
            """,
            (int(usuario_id),),
        )
        return [self._deserializar_item_tarefa(linha) for linha in linhas]
