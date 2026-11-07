"""Gerenciador relacional SQLite com integridade referencial e consultas parametrizadas."""

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
import sqlite3
import time
from typing import Any

from tokstance.backend.repositories.persistence_vault import DiarioAnotacoesPersistencia
from tokstance.config import FUSO_BRT, resolver_caminhos_dados

DDL_ESQUEMA_RELACIONAL = (
    """
    CREATE TABLE IF NOT EXISTS usuarios (
        usuario_id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome_usuario TEXT NOT NULL UNIQUE,
        nome_completo TEXT NOT NULL DEFAULT '',
        email TEXT NOT NULL DEFAULT '',
        senha_hash TEXT NOT NULL,
        criado_em TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS tarefas (
        tarefa_id INTEGER PRIMARY KEY AUTOINCREMENT,
        slug_tarefa TEXT NOT NULL UNIQUE,
        titulo TEXT NOT NULL,
        pergunta TEXT NOT NULL,
        opcoes_json TEXT NOT NULL,
        distancias_rotulos_json TEXT NOT NULL,
        numero_vagas INTEGER NOT NULL DEFAULT 2,
        videos_por_rotulador INTEGER NOT NULL DEFAULT 0,
        percentual_sobreposicao INTEGER NOT NULL DEFAULT 0,
        codigo_convite TEXT NOT NULL UNIQUE,
        versao_atribuicao TEXT NOT NULL DEFAULT '',
        criado_por_usuario_id INTEGER NOT NULL,
        criado_em TEXT NOT NULL,
        FOREIGN KEY (criado_por_usuario_id) REFERENCES usuarios(usuario_id) ON DELETE RESTRICT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS membros_tarefa (
        membro_id INTEGER PRIMARY KEY AUTOINCREMENT,
        tarefa_id INTEGER NOT NULL,
        usuario_id INTEGER NOT NULL,
        papel TEXT NOT NULL CHECK (papel IN ('administrador', 'rotulador')),
        vaga_atribuida TEXT NOT NULL DEFAULT '',
        entrou_em TEXT NOT NULL,
        UNIQUE(tarefa_id, usuario_id, papel),
        FOREIGN KEY (tarefa_id) REFERENCES tarefas(tarefa_id) ON DELETE CASCADE,
        FOREIGN KEY (usuario_id) REFERENCES usuarios(usuario_id) ON DELETE CASCADE
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS videos_tarefa (
        video_tarefa_id INTEGER PRIMARY KEY AUTOINCREMENT,
        tarefa_id INTEGER NOT NULL,
        video_id TEXT NOT NULL,
        tipo_pool TEXT NOT NULL CHECK (tipo_pool IN ('principal', 'reserva')),
        url TEXT NOT NULL,
        target TEXT NOT NULL,
        video_description TEXT NOT NULL DEFAULT '',
        voice_to_text TEXT NOT NULL DEFAULT '',
        video_duration TEXT NOT NULL DEFAULT '',
        UNIQUE(tarefa_id, tipo_pool, video_id),
        FOREIGN KEY (tarefa_id) REFERENCES tarefas(tarefa_id) ON DELETE CASCADE
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS atribuicoes (
        atribuicao_pk INTEGER PRIMARY KEY AUTOINCREMENT,
        tarefa_id INTEGER NOT NULL,
        assignment_version TEXT NOT NULL,
        assignment_id TEXT NOT NULL,
        labeler TEXT NOT NULL,
        usuario_id INTEGER,
        video_id TEXT NOT NULL,
        url TEXT NOT NULL,
        target TEXT NOT NULL,
        video_description TEXT NOT NULL DEFAULT '',
        voice_to_text TEXT NOT NULL DEFAULT '',
        video_duration TEXT NOT NULL DEFAULT '',
        ordem_fila INTEGER NOT NULL DEFAULT 0,
        UNIQUE(tarefa_id, assignment_id),
        FOREIGN KEY (tarefa_id) REFERENCES tarefas(tarefa_id) ON DELETE CASCADE,
        FOREIGN KEY (usuario_id) REFERENCES usuarios(usuario_id) ON DELETE SET NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS anotacoes (
        anotacao_id INTEGER PRIMARY KEY AUTOINCREMENT,
        tarefa_id INTEGER NOT NULL,
        assignment_id TEXT NOT NULL,
        usuario_id INTEGER,
        labeler TEXT NOT NULL,
        video_id TEXT NOT NULL,
        url TEXT NOT NULL,
        target TEXT NOT NULL,
        stance TEXT NOT NULL,
        tempo_analise_segundos REAL NOT NULL DEFAULT 0.0,
        video_duration TEXT NOT NULL DEFAULT '',
        timestamp TEXT NOT NULL,
        UNIQUE(tarefa_id, assignment_id),
        FOREIGN KEY (tarefa_id) REFERENCES tarefas(tarefa_id) ON DELETE CASCADE,
        FOREIGN KEY (usuario_id) REFERENCES usuarios(usuario_id) ON DELETE SET NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS erros_videos (
        erro_id INTEGER PRIMARY KEY AUTOINCREMENT,
        tarefa_id INTEGER NOT NULL,
        timestamp TEXT NOT NULL,
        video_id TEXT NOT NULL,
        url TEXT NOT NULL,
        usuario_id INTEGER,
        labeler TEXT NOT NULL,
        assignment_id TEXT NOT NULL,
        replacement_video_id TEXT NOT NULL DEFAULT '',
        replacement_url TEXT NOT NULL DEFAULT '',
        replacement_assignment_id TEXT NOT NULL DEFAULT '',
        replacement_status TEXT NOT NULL DEFAULT '',
        FOREIGN KEY (tarefa_id) REFERENCES tarefas(tarefa_id) ON DELETE CASCADE,
        FOREIGN KEY (usuario_id) REFERENCES usuarios(usuario_id) ON DELETE SET NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS logs_acesso (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        tarefa_id INTEGER,
        usuario_id INTEGER,
        usuario TEXT NOT NULL,
        acao TEXT NOT NULL,
        tempo_desde_login_segundos REAL,
        timestamp TEXT NOT NULL,
        FOREIGN KEY (tarefa_id) REFERENCES tarefas(tarefa_id) ON DELETE SET NULL,
        FOREIGN KEY (usuario_id) REFERENCES usuarios(usuario_id) ON DELETE SET NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS recuperacao_senha (
        recuperacao_id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER NOT NULL,
        codigo_recuperacao TEXT NOT NULL,
        expira_em TEXT NOT NULL,
        usado INTEGER NOT NULL DEFAULT 0,
        criado_em TEXT NOT NULL,
        FOREIGN KEY (usuario_id) REFERENCES usuarios(usuario_id) ON DELETE CASCADE
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_membros_tarefa_usuario ON membros_tarefa(usuario_id, papel);",
    "CREATE INDEX IF NOT EXISTS idx_videos_tarefa_pool ON videos_tarefa(tarefa_id, tipo_pool);",
    "CREATE INDEX IF NOT EXISTS idx_atribuicoes_tarefa_rotulador ON atribuicoes(tarefa_id, labeler, ordem_fila);",
    "CREATE INDEX IF NOT EXISTS idx_anotacoes_tarefa_rotulador ON anotacoes(tarefa_id, labeler);",
    "CREATE INDEX IF NOT EXISTS idx_erros_videos_tarefa ON erros_videos(tarefa_id, video_id);",
    "CREATE INDEX IF NOT EXISTS idx_logs_acesso_tarefa ON logs_acesso(tarefa_id, timestamp);",
    "CREATE INDEX IF NOT EXISTS idx_recuperacao_usuario ON recuperacao_senha(usuario_id, codigo_recuperacao);",
)


class BancoDadosSQLite:
    """Gerencia conexões SQLite com durabilidade WAL, chaves estrangeiras ativas, queries parametrizadas e cofre de persistência."""

    def __init__(
        self,
        caminho_banco: Path | str | None = None,
        inicializar: bool = True,
    ) -> None:
        if caminho_banco is None:
            caminho_efetivo = resolver_caminhos_dados().arquivo_banco_dados
        else:
            caminho_efetivo = Path(caminho_banco)
        self.caminho_banco = caminho_efetivo
        if str(self.caminho_banco) != ":memory:":
            self.caminho_banco.parent.mkdir(parents=True, exist_ok=True)
            self.caminho_journal = self.caminho_banco.parent / f"{self.caminho_banco.stem}_journal.jsonl"
        else:
            self.caminho_journal = Path(resolver_caminhos_dados().diretorio_base) / "memory_journal.jsonl"

        self.diario_anotacoes = DiarioAnotacoesPersistencia(self.caminho_journal)
        if inicializar:
            self.inicializar_esquema()

    def _aplicar_pragmas(self, conexao: sqlite3.Connection) -> None:
        """Aplica diretrizes de durabilidade WAL, integridade referencial e timeout de concorrência."""
        conexao.execute("PRAGMA foreign_keys = ON;")
        conexao.execute("PRAGMA busy_timeout = 30000;")
        if str(self.caminho_banco) != ":memory:":
            try:
                conexao.execute("PRAGMA journal_mode = WAL;")
                conexao.execute("PRAGMA synchronous = NORMAL;")
                conexao.execute("PRAGMA wal_autocheckpoint = 1000;")
            except Exception:
                pass

    @contextmanager
    def conectar(self) -> Iterator[sqlite3.Connection]:
        """Abre uma conexão transacional SQLite com integridade referencial e modo WAL."""
        conexao = sqlite3.connect(str(self.caminho_banco), timeout=30.0)
        conexao.row_factory = sqlite3.Row
        try:
            self._aplicar_pragmas(conexao)
            yield conexao
            conexao.commit()
        except Exception:
            conexao.rollback()
            raise
        finally:
            conexao.close()

    @contextmanager
    def transacao(self) -> Iterator[sqlite3.Connection]:
        """Alias para conectar() com gerenciamento transacional de commit e rollback."""
        with self.conectar() as conn:
            yield conn

    @contextmanager
    def transacao_imediata(self) -> Iterator[sqlite3.Connection]:
        """Abre transação com BEGIN IMMEDIATE para reservar lock exclusivo e prevenir deadlocks."""
        conexao = sqlite3.connect(str(self.caminho_banco), timeout=30.0)
        conexao.row_factory = sqlite3.Row
        try:
            self._aplicar_pragmas(conexao)
            conexao.execute("BEGIN IMMEDIATE;")
            yield conexao
            conexao.commit()
        except Exception:
            conexao.rollback()
            raise
        finally:
            conexao.close()

    def inicializar_esquema(self) -> None:
        """Cria todas as tabelas e índices relacionais caso ainda não existam e reconcilia pendências."""
        with self.conectar() as conexao:
            for comando_ddl in DDL_ESQUEMA_RELACIONAL:
                conexao.execute(comando_ddl)
            # migração incremental para colunas email e nome_completo em usuarios se ainda não existirem
            cols_usuarios = [r[1] for r in conexao.execute("PRAGMA table_info(usuarios);").fetchall()]
            if "email" not in cols_usuarios:
                conexao.execute("ALTER TABLE usuarios ADD COLUMN email TEXT NOT NULL DEFAULT '';")
            if "nome_completo" not in cols_usuarios:
                conexao.execute("ALTER TABLE usuarios ADD COLUMN nome_completo TEXT NOT NULL DEFAULT '';")

        # Auto-reconciliação de anotações pendentes do diário na inicialização
        try:
            self.diario_anotacoes.sincronizar_com_banco(self)
        except Exception:
            pass

    def _validar_consulta_segura(self, sql: str, parametros: Sequence[Any]) -> None:
        """Garante defesa em profundidade validando contagem exata de placeholders e rejeitando bytes nulos."""
        if not isinstance(sql, str):
            raise ValueError("Comando SQL deve ser uma string válida.")
        if "\x00" in sql:
            raise ValueError("Tentativa de injeção detectada: byte nulo na query SQL.")
        qtd_placeholders = sql.count("?")
        qtd_parametros = len(parametros)
        if qtd_placeholders != qtd_parametros:
            raise ValueError(
                f"Inconsistência de parâmetros SQL: {qtd_placeholders} marcadores '?' informados, "
                f"mas {qtd_parametros} parâmetros fornecidos."
            )

    def executar(
        self,
        sql: str,
        parametros: Sequence[Any] = (),
        max_tentativas: int = 5,
        espera_base: float = 0.05,
    ) -> int:
        """Executa um comando parametrizado de escrita com retry defensivo em caso de lock temporário."""
        self._validar_consulta_segura(sql, parametros)
        tentativa = 0
        ultimo_erro = None
        while tentativa < max_tentativas:
            try:
                with self.conectar() as conexao:
                    cursor = conexao.execute(sql, tuple(parametros))
                    sql_comando = sql.strip().split()[0].upper()
                    if sql_comando == "INSERT" and cursor.lastrowid is not None:
                        return int(cursor.lastrowid)
                    return int(cursor.rowcount)
            except sqlite3.OperationalError as exc:
                ultimo_erro = exc
                if "locked" in str(exc).lower() or "busy" in str(exc).lower():
                    tentativa += 1
                    time.sleep(espera_base * (2 ** (tentativa - 1)))
                else:
                    raise
        raise sqlite3.OperationalError(
            f"Banco de dados travado após {max_tentativas} tentativas: {ultimo_erro}"
        )

    def consultar_um(
        self,
        sql: str,
        parametros: Sequence[Any] = (),
    ) -> dict[str, Any] | None:
        """Executa uma consulta parametrizada e retorna a primeira linha como dicionario."""
        self._validar_consulta_segura(sql, parametros)
        with self.conectar() as conexao:
            cursor = conexao.execute(sql, tuple(parametros))
            linha = cursor.fetchone()
            return dict(linha) if linha is not None else None

    def consultar_todos(
        self,
        sql: str,
        parametros: Sequence[Any] = (),
    ) -> list[dict[str, Any]]:
        """Executa uma consulta parametrizada e retorna todas as linhas como dicionarios."""
        self._validar_consulta_segura(sql, parametros)
        with self.conectar() as conexao:
            cursor = conexao.execute(sql, tuple(parametros))
            return [dict(linha) for linha in cursor.fetchall()]

    def listar_tabelas(self) -> list[str]:
        """Retorna os nomes das tabelas de dominio criadas no banco SQLite."""
        linhas = self.consultar_todos(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name ASC;
            """
        )
        return [str(linha["name"]) for linha in linhas]

    def verificar_integridade(self) -> dict[str, Any]:
        """Executa checagens profundas de integridade física e relacional no SQLite."""
        with self.conectar() as conexao:
            qc = conexao.execute("PRAGMA quick_check;").fetchall()
            quick_ok = len(qc) == 1 and qc[0][0] == "ok"

            ic = conexao.execute("PRAGMA integrity_check;").fetchall()
            integrity_ok = len(ic) == 1 and ic[0][0] == "ok"

            fk_erros = [dict(r) for r in conexao.execute("PRAGMA foreign_key_check;").fetchall()]

            jm_res = conexao.execute("PRAGMA journal_mode;").fetchone()
            journal_mode = str(jm_res[0]) if jm_res else "desconhecido"

            status_geral = "ok" if (quick_ok and integrity_ok and not fk_erros) else "alerta"
            return {
                "status": status_geral,
                "quick_check": "ok" if quick_ok else str(qc),
                "integrity_check": "ok" if integrity_ok else str(ic),
                "foreign_keys_erros": fk_erros,
                "journal_mode": journal_mode,
            }

    def fazer_backup(
        self,
        caminho_destino: Path | str | None = None,
        manter_ultimos: int = 5,
    ) -> Path:
        """Gera um snapshot consistente e atômico do banco de dados via SQLite Online Backup API."""
        if str(self.caminho_banco) == ":memory:":
            raise ValueError("Não é possível realizar backup de banco em memória.")

        if caminho_destino is None:
            pasta_backups = self.caminho_banco.parent / "backups"
            pasta_backups.mkdir(parents=True, exist_ok=True)
            agora_str = datetime.now(FUSO_BRT).strftime("%Y%m%d_%H%M%S")
            destino = pasta_backups / f"tokstance_backup_{agora_str}.db"
        else:
            destino = Path(caminho_destino)
            destino.parent.mkdir(parents=True, exist_ok=True)

        with self.conectar() as conn_origem:
            conn_dest = sqlite3.connect(str(destino))
            try:
                conn_origem.backup(conn_dest)
            finally:
                conn_dest.close()

        if manter_ultimos > 0 and caminho_destino is None:
            pasta_backups = self.caminho_banco.parent / "backups"
            backups_existentes = sorted(
                pasta_backups.glob("tokstance_backup_*.db"),
                key=lambda p: p.stat().st_mtime,
            )
            while len(backups_existentes) > manter_ultimos:
                antigo = backups_existentes.pop(0)
                try:
                    antigo.unlink(missing_ok=True)
                except Exception:
                    pass

        return destino

    def restaurar_backup(self, caminho_backup: Path | str) -> bool:
        """Restaura o banco a partir de um backup validado e reconcilia o diário de anotações."""
        origem = Path(caminho_backup)
        if not origem.exists():
            raise FileNotFoundError(f"Arquivo de backup não encontrado: {origem}")

        conn_teste = sqlite3.connect(str(origem))
        try:
            res = conn_teste.execute("PRAGMA quick_check;").fetchall()
            if not (len(res) == 1 and res[0][0] == "ok"):
                raise ValueError("O arquivo de backup está corrompido.")
        finally:
            conn_teste.close()

        conn_origem = sqlite3.connect(str(origem))
        try:
            with self.conectar() as conn_dest:
                conn_origem.backup(conn_dest)
        finally:
            conn_origem.close()

        # Reconcilia de forma transparente anotações preservadas no diário
        self.diario_anotacoes.sincronizar_com_banco(self)
        return True

