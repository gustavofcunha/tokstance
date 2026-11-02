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
        nome_completo: str = "",
        criado_em: str | None = None,
    ) -> dict[str, Any]:
        """Registra um novo usuario na tabela usuarios e retorna seus dados."""
        nome_limpo = validar_nome_usuario(nome_usuario)
        if not isinstance(senha_hash, str) or not senha_hash.strip():
            raise ValueError("O hash da senha é obrigatório.")
        email_limpo = str(email or "").strip().lower()
        nome_completo_limpo = str(nome_completo or "").strip().upper()
        instante = str(criado_em or formatar_data_hora_brt())
        try:
            usuario_id = self.banco.executar(
                """
                INSERT INTO usuarios (nome_usuario, nome_completo, email, senha_hash, criado_em)
                VALUES (?, ?, ?, ?, ?);
                """,
                (nome_limpo, nome_completo_limpo, email_limpo, senha_hash.strip(), instante),
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
            SELECT usuario_id, nome_usuario, nome_completo, email, senha_hash, criado_em
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
            SELECT usuario_id, nome_usuario, nome_completo, email, senha_hash, criado_em
            FROM usuarios
            WHERE LOWER(email) = ?;
            """,
            (email.strip().lower(),),
        )

    def buscar_por_nome_ou_email_case_insensitive(
        self, identificador: str
    ) -> dict[str, Any] | None:
        """Busca um usuario por nome de usuario ou email sem diferenciacao de maiusculas e minusculas."""
        if not isinstance(identificador, str) or not identificador.strip():
            return None
        limpo = identificador.strip()
        return self.banco.consultar_um(
            """
            SELECT usuario_id, nome_usuario, nome_completo, email, senha_hash, criado_em
            FROM usuarios
            WHERE nome_usuario = ? COLLATE NOCASE OR email = ? COLLATE NOCASE
            LIMIT 1;
            """,
            (limpo, limpo),
        )

    def buscar_por_identificador(self, identificador: str) -> dict[str, Any] | None:
        """Alias para buscar_por_nome_ou_email_case_insensitive."""
        return self.buscar_por_nome_ou_email_case_insensitive(identificador)

    def buscar_por_id(self, usuario_id: int) -> dict[str, Any] | None:
        """Busca um usuario pela chave primaria usuario_id."""
        return self.banco.consultar_um(
            """
            SELECT usuario_id, nome_usuario, nome_completo, email, senha_hash, criado_em
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
            SELECT usuario_id, nome_usuario, nome_completo, email, criado_em
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

    def vincular_atribuicoes_e_membros_pendentes(
        self,
        usuario_id: int,
        nome_usuario: str,
        email: str = "",
    ) -> int:
        """Garante que atribuicoes membros_tarefa e anotacoes pre-existentes fiquem vinculados ao usuario."""
        u_id = int(usuario_id)
        nome_limpo = str(nome_usuario or "").strip()
        email_limpo = str(email or "").strip()
        modificados = 0
        with self.banco.conectar() as conexao:
            #atualiza atribuicoes com usuario_id nulo ou correspondente por nome ou email
            if email_limpo:
                cur = conexao.execute(
                    """
                    UPDATE atribuicoes
                    SET usuario_id = ?
                    WHERE (usuario_id IS NULL OR usuario_id = ?)
                      AND (labeler = ? COLLATE NOCASE OR labeler = ? COLLATE NOCASE);
                    """,
                    (u_id, u_id, nome_limpo, email_limpo),
                )
            else:
                cur = conexao.execute(
                    """
                    UPDATE atribuicoes
                    SET usuario_id = ?
                    WHERE (usuario_id IS NULL OR usuario_id = ?)
                      AND labeler = ? COLLATE NOCASE;
                    """,
                    (u_id, u_id, nome_limpo),
                )
            modificados += cur.rowcount

            #atualiza anotacoes com usuario_id nulo ou correspondente por nome ou email
            if email_limpo:
                cur = conexao.execute(
                    """
                    UPDATE anotacoes
                    SET usuario_id = ?
                    WHERE (usuario_id IS NULL OR usuario_id = ?)
                      AND (labeler = ? COLLATE NOCASE OR labeler = ? COLLATE NOCASE);
                    """,
                    (u_id, u_id, nome_limpo, email_limpo),
                )
            else:
                cur = conexao.execute(
                    """
                    UPDATE anotacoes
                    SET usuario_id = ?
                    WHERE (usuario_id IS NULL OR usuario_id = ?)
                      AND labeler = ? COLLATE NOCASE;
                    """,
                    (u_id, u_id, nome_limpo),
                )
            modificados += cur.rowcount

            #garante vinculo em membros_tarefa como rotulador para tarefas com atribuicoes
            instante = formatar_data_hora_brt()
            conexao.execute(
                """
                INSERT OR IGNORE INTO membros_tarefa (tarefa_id, usuario_id, papel, vaga_atribuida, entrou_em)
                SELECT DISTINCT a.tarefa_id, ?, 'rotulador', a.labeler, ?
                FROM atribuicoes a
                WHERE a.usuario_id = ?
                   OR a.labeler = ? COLLATE NOCASE
                   OR (? != '' AND a.labeler = ? COLLATE NOCASE);
                """,
                (u_id, instante, u_id, nome_limpo, email_limpo, email_limpo),
            )

            #garante vinculo em membros_tarefa como administrador para tarefas criadas pelo usuario
            conexao.execute(
                """
                INSERT OR IGNORE INTO membros_tarefa (tarefa_id, usuario_id, papel, vaga_atribuida, entrou_em)
                SELECT t.tarefa_id, ?, 'administrador', '', t.criado_em
                FROM tarefas t
                WHERE t.criado_por_usuario_id = ?;
                """,
                (u_id, u_id),
            )
        return modificados

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
        """Retorna todas as tarefas vinculadas ao usuario garantindo preservacao de administracao e atribuicoes."""
        u_id = int(usuario_id)
        if papel is not None:
            p_limpo = str(papel).strip().lower()
            linhas = self.banco.consultar_todos(
                """
                SELECT t.tarefa_id, t.slug_tarefa, t.titulo, t.pergunta,
                       t.opcoes_json, t.distancias_rotulos_json,
                       t.numero_vagas, t.videos_por_rotulador, t.percentual_sobreposicao,
                       t.codigo_convite, t.versao_atribuicao, t.criado_em,
                       COALESCE(m.papel, ?) AS papel,
                       COALESCE(m.vaga_atribuida, '') AS vaga_atribuida,
                       COALESCE(m.entrou_em, t.criado_em) AS entrou_em
                FROM tarefas t
                LEFT JOIN membros_tarefa m ON m.tarefa_id = t.tarefa_id AND m.usuario_id = ? AND m.papel = ?
                WHERE m.papel = ?
                   OR (t.criado_por_usuario_id = ? AND ? = 'administrador')
                   OR (? = 'rotulador' AND t.tarefa_id IN (
                       SELECT DISTINCT tarefa_id FROM atribuicoes
                       WHERE usuario_id = ?
                          OR labeler = (SELECT nome_usuario FROM usuarios WHERE usuario_id = ?)
                          OR (labeler != '' AND labeler = (SELECT email FROM usuarios WHERE usuario_id = ? AND email IS NOT NULL AND email != ''))
                   ))
                ORDER BY t.tarefa_id DESC;
                """,
                (
                    p_limpo,
                    u_id, p_limpo,
                    p_limpo,
                    u_id, p_limpo,
                    p_limpo, u_id, u_id, u_id,
                ),
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
            UNION
            SELECT t.tarefa_id, t.slug_tarefa, t.titulo, t.pergunta,
                   t.opcoes_json, t.distancias_rotulos_json,
                   t.numero_vagas, t.videos_por_rotulador, t.percentual_sobreposicao,
                   t.codigo_convite, t.versao_atribuicao, t.criado_em,
                   'administrador' AS papel, '' AS vaga_atribuida, t.criado_em AS entrou_em
            FROM tarefas t
            WHERE t.criado_por_usuario_id = ?
              AND NOT EXISTS (
                  SELECT 1 FROM membros_tarefa m2
                  WHERE m2.tarefa_id = t.tarefa_id AND m2.usuario_id = ? AND m2.papel = 'administrador'
              )
            UNION
            SELECT t.tarefa_id, t.slug_tarefa, t.titulo, t.pergunta,
                   t.opcoes_json, t.distancias_rotulos_json,
                   t.numero_vagas, t.videos_por_rotulador, t.percentual_sobreposicao,
                   t.codigo_convite, t.versao_atribuicao, t.criado_em,
                   'rotulador' AS papel, '' AS vaga_atribuida, t.criado_em AS entrou_em
            FROM tarefas t
            WHERE t.tarefa_id IN (
                SELECT DISTINCT tarefa_id FROM atribuicoes
                WHERE usuario_id = ?
                   OR labeler = (SELECT nome_usuario FROM usuarios WHERE usuario_id = ?)
                   OR (labeler != '' AND labeler = (SELECT email FROM usuarios WHERE usuario_id = ? AND email IS NOT NULL AND email != ''))
            )
            ORDER BY tarefa_id DESC;
            """,
            (u_id, u_id, u_id, u_id, u_id, u_id),
        )
        return [self._deserializar_item_tarefa(linha) for linha in linhas]
