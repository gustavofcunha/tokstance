"""Gerenciador relacional SQLite com integridade referencial e consultas parametrizadas."""

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
import sqlite3
from typing import Any

from tokstance.config import resolver_caminhos_dados

DDL_ESQUEMA_RELACIONAL = (
    """
    CREATE TABLE IF NOT EXISTS usuarios (
        usuario_id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome_usuario TEXT NOT NULL UNIQUE,
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
    "CREATE INDEX IF NOT EXISTS idx_membros_tarefa_usuario ON membros_tarefa(usuario_id, papel);",
    "CREATE INDEX IF NOT EXISTS idx_videos_tarefa_pool ON videos_tarefa(tarefa_id, tipo_pool);",
    "CREATE INDEX IF NOT EXISTS idx_atribuicoes_tarefa_rotulador ON atribuicoes(tarefa_id, labeler, ordem_fila);",
    "CREATE INDEX IF NOT EXISTS idx_anotacoes_tarefa_rotulador ON anotacoes(tarefa_id, labeler);",
    "CREATE INDEX IF NOT EXISTS idx_erros_videos_tarefa ON erros_videos(tarefa_id, video_id);",
    "CREATE INDEX IF NOT EXISTS idx_logs_acesso_tarefa ON logs_acesso(tarefa_id, timestamp);",
)


class BancoDadosSQLite:
    """Gerencia conexoes SQLite com chaves estrangeiras ativas e queries parametrizadas."""

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
        self.caminho_banco.parent.mkdir(parents=True, exist_ok=True)
        if inicializar:
            self.inicializar_esquema()

    @contextmanager
    def conectar(self) -> Iterator[sqlite3.Connection]:
        """Abre uma conexao transacional SQLite com integridade referencial habilitada."""
        conexao = sqlite3.connect(str(self.caminho_banco), timeout=30.0)
        conexao.row_factory = sqlite3.Row
        try:
            #integridade referencial obrigatoria em cada conexao sqlite
            conexao.execute("PRAGMA foreign_keys = ON;")
            yield conexao
            conexao.commit()
        except Exception:
            conexao.rollback()
            raise
        finally:
            conexao.close()

    def inicializar_esquema(self) -> None:
        """Cria todas as tabelas e indices relacionais caso ainda nao existam."""
        with self.conectar() as conexao:
            for comando_ddl in DDL_ESQUEMA_RELACIONAL:
                conexao.execute(comando_ddl)

    def executar(self, sql: str, parametros: Sequence[Any] = ()) -> int:
        """Executa um comando parametrizado de escrita e retorna o id inserido ou linhas afetadas."""
        with self.conectar() as conexao:
            cursor = conexao.execute(sql, tuple(parametros))
            sql_comando = sql.strip().split()[0].upper()
            if sql_comando == "INSERT" and cursor.lastrowid is not None:
                return int(cursor.lastrowid)
            return int(cursor.rowcount)

    def consultar_um(
        self,
        sql: str,
        parametros: Sequence[Any] = (),
    ) -> dict[str, Any] | None:
        """Executa uma consulta parametrizada e retorna a primeira linha como dicionario."""
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

