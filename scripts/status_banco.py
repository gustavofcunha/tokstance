"""Script de monitoramento e auditoria em tempo real do banco de dados TokStance.

Gera relatorio no terminal e mantem sincronizado o arquivo STATUS_BANCO.md com:
- Usuarios cadastrados, e-mails, nomes completos, papeis e ultimo acesso a plataforma.
- Tarefas criadas, usuario criador, sobreposicao, rotuladores participantes e
  distribuicao precisa de videos (atribuicoes totais, videos distintos e videos com overlap).
"""

from __future__ import annotations

import argparse
from datetime import datetime
import os
from pathlib import Path
import sqlite3
import sys
import time
from typing import Any

FUSO_PADRAO = "BRT (UTC-03:00)"


def obter_caminho_db(caminho_informado: Path | str | None = None) -> Path:
    """Resolve o caminho absoluto do banco de dados SQLite."""
    if caminho_informado:
        return Path(caminho_informado).resolve()

    env_data = os.environ.get("TOKSTANCE_DATA_DIR")
    if env_data:
        candidato = Path(env_data) / "tokstance.db"
        if candidato.exists():
            return candidato.resolve()

    diretorio_raiz = Path(__file__).resolve().parent.parent
    candidato_data = diretorio_raiz / "data" / "tokstance.db"
    return candidato_data.resolve()


def coletar_dados_banco(caminho_db: Path) -> dict[str, Any]:
    """Extrai todas as metricas de usuarios, tarefas e distribuicao de videos do banco SQLite."""
    if not caminho_db.exists():
        return {
            "status": "erro",
            "mensagem": f"Banco de dados nao encontrado em: {caminho_db}",
            "usuarios": [],
            "tarefas": [],
            "timestamp": datetime.now().isoformat(),
        }

    conexao = sqlite3.connect(str(caminho_db))
    conexao.row_factory = sqlite3.Row
    cursor = conexao.cursor()

    # 1. Metricas de Usuarios
    query_usuarios = """
        SELECT
            u.usuario_id,
            u.nome_usuario,
            u.nome_completo,
            u.email,
            u.criado_em,
            MAX(l.timestamp) AS ultimo_acesso,
            COUNT(DISTINCT l.log_id) AS total_acessos,
            (
                SELECT l2.acao
                FROM logs_acesso l2
                WHERE l2.usuario_id = u.usuario_id OR l2.usuario = u.nome_usuario
                ORDER BY l2.log_id DESC
                LIMIT 1
            ) AS ultima_acao
        FROM usuarios u
        LEFT JOIN logs_acesso l ON l.usuario_id = u.usuario_id OR l.usuario = u.nome_usuario
        GROUP BY u.usuario_id
        ORDER BY u.usuario_id ASC;
    """
    linhas_usuarios = cursor.execute(query_usuarios).fetchall()
    usuarios: list[dict[str, Any]] = []

    for row in linhas_usuarios:
        u_id = int(row["usuario_id"])
        # Coletar papeis do usuario em todas as tarefas
        papeis_linhas = cursor.execute(
            """
            SELECT m.tarefa_id, t.titulo, m.papel, m.vaga_atribuida
            FROM membros_tarefa m
            JOIN tarefas t ON t.tarefa_id = m.tarefa_id
            WHERE m.usuario_id = ?
            ORDER BY m.tarefa_id ASC;
            """,
            (u_id,),
        ).fetchall()

        papeis_desc = [
            f"{p['titulo']} ({p['papel']}{' - ' + p['vaga_atribuida'] if p['vaga_atribuida'] else ''})"
            for p in papeis_linhas
        ]

        usuarios.append(
            {
                "usuario_id": u_id,
                "nome_usuario": row["nome_usuario"],
                "nome_completo": row["nome_completo"] or "(nao preenchido)",
                "email": row["email"] or "(nao informado)",
                "criado_em": row["criado_em"],
                "ultimo_acesso": row["ultimo_acesso"] or "Nunca acessou",
                "total_acessos": int(row["total_acessos"]),
                "ultima_acao": row["ultima_acao"] or "-",
                "papeis": papeis_desc,
            }
        )

    # 2. Metricas de Tarefas
    query_tarefas = """
        SELECT
            t.tarefa_id,
            t.slug_tarefa,
            t.titulo,
            t.pergunta,
            t.numero_vagas,
            t.percentual_sobreposicao,
            t.codigo_convite,
            t.criado_por_usuario_id,
            COALESCE(u.nome_usuario, 'Desconhecido') AS criador_nome,
            COALESCE(u.email, '') AS criador_email,
            t.criado_em
        FROM tarefas t
        LEFT JOIN usuarios u ON u.usuario_id = t.criado_por_usuario_id
        ORDER BY t.tarefa_id ASC;
    """
    linhas_tarefas = cursor.execute(query_tarefas).fetchall()
    tarefas: list[dict[str, Any]] = []

    for t in linhas_tarefas:
        t_id = int(t["tarefa_id"])

        # Rotuladores participantes
        membros_rotuladores = cursor.execute(
            """
            SELECT u.usuario_id, u.nome_usuario, u.nome_completo, m.vaga_atribuida, m.entrou_em
            FROM membros_tarefa m
            JOIN usuarios u ON u.usuario_id = m.usuario_id
            WHERE m.tarefa_id = ? AND m.papel = 'rotulador'
            ORDER BY m.vaga_atribuida ASC, m.membro_id ASC;
            """,
            (t_id,),
        ).fetchall()

        rotuladores_lista = [
            {
                "usuario_id": int(m["usuario_id"]),
                "nome_usuario": m["nome_usuario"],
                "nome_completo": m["nome_completo"],
                "vaga": m["vaga_atribuida"],
                "entrou_em": m["entrou_em"],
            }
            for m in membros_rotuladores
        ]

        # Administradores da tarefa
        membros_admins = cursor.execute(
            """
            SELECT u.usuario_id, u.nome_usuario
            FROM membros_tarefa m
            JOIN usuarios u ON u.usuario_id = m.usuario_id
            WHERE m.tarefa_id = ? AND m.papel = 'administrador'
            ORDER BY m.membro_id ASC;
            """,
            (t_id,),
        ).fetchall()
        admins_lista = [a["nome_usuario"] for a in membros_admins]
        if t["criador_nome"] not in admins_lista and t["criador_nome"] != "Desconhecido":
            admins_lista.insert(0, t["criador_nome"])

        # Metricas de Atribuicoes e Videos
        total_atribuicoes = cursor.execute(
            "SELECT count(*) FROM atribuicoes WHERE tarefa_id = ?",
            (t_id,),
        ).fetchone()[0]

        total_videos_distintos = cursor.execute(
            "SELECT count(DISTINCT video_id) FROM atribuicoes WHERE tarefa_id = ?",
            (t_id,),
        ).fetchone()[0]

        # Videos com sobreposicao (atribuidos a mais de 1 rotulador/vaga)
        videos_overlap = cursor.execute(
            """
            SELECT count(*) FROM (
                SELECT video_id FROM atribuicoes
                WHERE tarefa_id = ?
                GROUP BY video_id
                HAVING count(DISTINCT labeler) > 1
            );
            """,
            (t_id,),
        ).fetchone()[0]

        videos_exclusivos = cursor.execute(
            """
            SELECT count(*) FROM (
                SELECT video_id FROM atribuicoes
                WHERE tarefa_id = ?
                GROUP BY video_id
                HAVING count(DISTINCT labeler) = 1
            );
            """,
            (t_id,),
        ).fetchone()[0]

        # Anotacoes concluidas
        total_anotacoes = cursor.execute(
            "SELECT count(*) FROM anotacoes WHERE tarefa_id = ?",
            (t_id,),
        ).fetchone()[0]

        # Anotacoes por rotulador
        anotacoes_por_rotulador = cursor.execute(
            """
            SELECT labeler, count(*) as total
            FROM anotacoes
            WHERE tarefa_id = ?
            GROUP BY labeler
            ORDER BY total DESC;
            """,
            (t_id,),
        ).fetchall()
        progresso_rotuladores = {row["labeler"]: int(row["total"]) for row in anotacoes_por_rotulador}

        # Erros reportados
        erros_reportados = cursor.execute(
            "SELECT count(*) FROM erros_videos WHERE tarefa_id = ?",
            (t_id,),
        ).fetchone()[0]

        # Videos no pool de reserva
        videos_reserva = cursor.execute(
            "SELECT count(*) FROM videos_tarefa WHERE tarefa_id = ? AND tipo_pool = 'reserva'",
            (t_id,),
        ).fetchone()[0]

        vagas_ocupadas = len(rotuladores_lista)
        vagas_totais = int(t["numero_vagas"])
        vagas_restantes = max(0, vagas_totais - vagas_ocupadas)

        tarefas.append(
            {
                "tarefa_id": t_id,
                "titulo": t["titulo"],
                "codigo_convite": t["codigo_convite"],
                "criador_nome": t["criador_nome"],
                "criador_id": t["criado_por_usuario_id"],
                "criado_em": t["criado_em"],
                "sobreposicao_percentual": t["percentual_sobreposicao"],
                "vagas_totais": vagas_totais,
                "vagas_ocupadas": vagas_ocupadas,
                "vagas_restantes": vagas_restantes,
                "administradores": admins_lista,
                "rotuladores": rotuladores_lista,
                "distribuicao": {
                    "total_atribuicoes": int(total_atribuicoes),
                    "videos_distintos": int(total_videos_distintos),
                    "videos_overlap": int(videos_overlap),
                    "videos_exclusivos": int(videos_exclusivos),
                    "videos_reserva": int(videos_reserva),
                },
                "progresso": {
                    "anotacoes_feitas": int(total_anotacoes),
                    "erros_reportados": int(erros_reportados),
                    "por_rotulador": progresso_rotuladores,
                    "percentual_conclusao": round(
                        (total_anotacoes / total_atribuicoes * 100.0) if total_atribuicoes > 0 else 0.0,
                        1,
                    ),
                },
            }
        )

    # 3. Metricas de integridade SQLite e cofre de persistencia
    res_ic = cursor.execute("PRAGMA integrity_check;").fetchall()
    ic_ok = len(res_ic) == 1 and res_ic[0][0] == "ok"
    jm = cursor.execute("PRAGMA journal_mode;").fetchone()[0]

    conexao.close()

    # Estatisticas do diario append-only
    caminho_journal = caminho_db.parent / f"{caminho_db.stem}_journal.jsonl"
    total_journal = 0
    pendentes_journal = 0
    if caminho_journal.exists():
        from tokstance.backend.repositories.persistence_vault import DiarioAnotacoesPersistencia
        diario = DiarioAnotacoesPersistencia(caminho_journal)
        consol = diario.ler_registros_consolidados()
        total_journal = len(consol)
        pendentes_journal = len([r for r in consol.values() if r.get("status") == "pendente"])

    return {
        "status": "sucesso",
        "caminho_db": str(caminho_db),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "usuarios": usuarios,
        "tarefas": tarefas,
        "integridade": {
            "status": "OK" if ic_ok else "ALERTA",
            "journal_mode": str(jm).upper(),
            "anotacoes_diario": total_journal,
            "pendentes_diario": pendentes_journal,
        },
    }


def gerar_markdown(dados: dict[str, Any]) -> str:
    """Gera representacao Markdown rica e profissional com os dados do banco."""
    ts = dados.get("timestamp", "-")
    caminho_db = dados.get("caminho_db", "-")
    usuarios = dados.get("usuarios", [])
    tarefas = dados.get("tarefas", [])
    integ = dados.get("integridade", {})
    status_ic = integ.get("status", "OK")
    jm = integ.get("journal_mode", "WAL")
    tot_j = integ.get("anotacoes_diario", 0)
    pend_j = integ.get("pendentes_diario", 0)

    linhas: list[str] = [
        "# TokStance - Painel de Monitoramento em Tempo Real do Banco de Dados",
        "",
        f"> **Atualizado em:** `{ts}` ({FUSO_PADRAO})  ",
        f"> **Arquivo do Banco:** `{caminho_db}`  ",
        f"> **Integridade SQLite:** `{status_ic}` (Modo `{jm}`) | **Cofre de Persistência:** `{tot_j}` consolidadas, `{pend_j}` pendentes  ",
        f"> **Total de Usuários:** `{len(usuarios)}` | **Total de Tarefas:** `{len(tarefas)}`",
        "",
        "---",
        "",
        "## 1. Usuários Cadastrados e Detalhes de Acesso",
        "",
        "| ID | Nome de Usuário | Nome Completo | E-mail | Cadastrado Em | Último Acesso | Acessos | Tarefas / Papéis |",
        "|---|---|---|---|---|---|---|---|",
    ]

    for u in usuarios:
        papeis_txt = "<br>".join(u["papeis"]) if u["papeis"] else "(nenhum)"
        linhas.append(
            f"| `{u['usuario_id']}` | **{u['nome_usuario']}** | {u['nome_completo']} | `{u['email']}` | "
            f"{u['criado_em']} | {u['ultimo_acesso']} | {u['total_acessos']} | {papeis_txt} |"
        )

    linhas.extend(
        [
            "",
            "---",
            "",
            "## 2. Tarefas Criadas e Distribuição de Vídeos",
            "",
        ]
    )

    if not tarefas:
        linhas.append("*Nenhuma tarefa cadastrada no banco de dados.*")
    else:
        for t in tarefas:
            dist = t["distribuicao"]
            prog = t["progresso"]
            rotuladores_str = (
                ", ".join(f"`{r['nome_usuario']}` ({r['vaga']})" for r in t["rotuladores"])
                if t["rotuladores"]
                else "Nenhum rotulador inscrito ainda"
            )
            admins_str = ", ".join(f"`{a}`" for a in t["administradores"])

            linhas.extend(
                [
                    f"### Tarefa #{t['tarefa_id']}: {t['titulo']}",
                    "",
                    f"- **Código de Convite:** `{t['codigo_convite']}`",
                    f"- **Criada por:** `{t['criador_nome']}` (ID {t['criador_id']}) em `{t['criado_em']}`",
                    f"- **Administradores:** {admins_str}",
                    f"- **Sobreposição Configurada:** **{t['sobreposicao_percentual']}%**",
                    f"- **Vagas:** {t['vagas_ocupadas']} ocupadas de {t['vagas_totais']} totais ({t['vagas_restantes']} disponíveis)",
                    f"- **Rotuladores Participantes:** {rotuladores_str}",
                    "",
                    "#### Distribuição de Vídeos",
                    "",
                    "| Métrica | Quantidade | Descrição |",
                    "|---|---|---|",
                    f"| **Total de Atribuições** | `{dist['total_atribuicoes']}` | Soma de vídeos nas filas de todas as vagas |",
                    f"| **Vídeos Distintos** | `{dist['videos_distintos']}` | Vídeos únicos no dataset principal da tarefa |",
                    f"| **Vídeos com Sobreposição (Overlap)** | `{dist['videos_overlap']}` | Vídeos distribuídos para mais de um rotulador ({t['sobreposicao_percentual']}%) |",
                    f"| **Vídeos Exclusivos** | `{dist['videos_exclusivos']}` | Vídeos atribuídos a um único rotulador |",
                    f"| **Vídeos no Pool Reserva** | `{dist['videos_reserva']}` | Vídeos reservas disponíveis para substituição |",
                    "",
                    "#### Progresso de Anotações",
                    "",
                    f"- **Anotações Concluídas:** `{prog['anotacoes_feitas']}` / `{dist['total_atribuicoes']}` ({prog['percentual_conclusao']}%)",
                    f"- **Erros de Vídeo Reportados:** `{prog['erros_reportados']}`",
                ]
            )

            if prog["por_rotulador"]:
                detalhes_rot = ", ".join(
                    f"`{rot}`: {qtd} anotações" for rot, qtd in prog["por_rotulador"].items()
                )
                linhas.append(f"- **Detalhamento por Rotulador:** {detalhes_rot}")

            linhas.extend(["", "---", ""])

    return "\n".join(linhas) + "\n"


def imprimir_terminal(dados: dict[str, Any]) -> None:
    """Imprime relatorio formatado diretamente no terminal."""
    ts = dados.get("timestamp", "-")
    caminho_db = dados.get("caminho_db", "-")
    usuarios = dados.get("usuarios", [])
    tarefas = dados.get("tarefas", [])

    print("=" * 80)
    print(f"  TOKSTANCE - MONITORAMENTO DO BANCO DE DADOS [{ts}]")
    print(f"  Banco SQLite: {caminho_db}")
    print("=" * 80)

    print("\n--- 1. USUARIOS CADASTRADOS ---")
    cabecalho_u = f"{'ID':<4} {'USUARIO':<15} {'NOME COMPLETO':<22} {'EMAIL':<25} {'ULTIMO ACESSO':<20}"
    print(cabecalho_u)
    print("-" * 88)
    for u in usuarios:
        print(
            f"{u['usuario_id']:<4} {u['nome_usuario']:<15} {u['nome_completo'][:20]:<22} "
            f"{u['email'][:24]:<25} {str(u['ultimo_acesso'])[:19]:<20}"
        )

    print("\n--- 2. TAREFAS E DISTRIBUICAO DE VIDEOS ---")
    if not tarefas:
        print("  (Nenhuma tarefa registrada)")
    for t in tarefas:
        d = t["distribuicao"]
        p = t["progresso"]
        print(f"\n[Tarefa #{t['tarefa_id']}] {t['titulo']} (Convite: {t['codigo_convite']})")
        print(f"  Criador: {t['criador_nome']} | Criada em: {t['criado_em']}")
        print(f"  Sobreposicao: {t['sobreposicao_percentual']}% | Vagas: {t['vagas_ocupadas']}/{t['vagas_totais']}")
        rot_nomes = [f"{r['nome_usuario']} ({r['vaga']})" for r in t["rotuladores"]]
        print(f"  Rotuladores: {', '.join(rot_nomes) if rot_nomes else 'Nenhum'}")
        print(
            f"  Videos Distribuídos: Total={d['total_atribuicoes']} | "
            f"Distintos={d['videos_distintos']} | Overlap={d['videos_overlap']} | Exclusivos={d['videos_exclusivos']}"
        )
        print(
            f"  Progresso: {p['anotacoes_feitas']}/{d['total_atribuicoes']} anotados ({p['percentual_conclusao']}%) | "
            f"Erros reportados: {p['erros_reportados']} | Reservas: {d['videos_reserva']}"
        )

    print("\n" + "=" * 80 + "\n")


def atualizar_painel(caminho_db: Path, arquivo_saida: Path | None = None) -> dict[str, Any]:
    """Coleta os dados do banco e atualiza o arquivo Markdown se especificado."""
    dados = coletar_dados_banco(caminho_db)
    if arquivo_saida:
        conteudo_md = gerar_markdown(dados)
        arquivo_saida.write_text(conteudo_md, encoding="utf-8")
    return dados


def main() -> None:
    parser = argparse.ArgumentParser(description="Monitor de banco de dados do TokStance")
    parser.add_argument("--db-path", type=Path, default=None, help="Caminho do banco SQLite")
    parser.add_argument("--saida", type=Path, default=Path("STATUS_BANCO.md"), help="Arquivo Markdown de saida")
    parser.add_argument("--watch", type=float, default=0.0, help="Intervalo em segundos para atualizacao continua")
    parser.add_argument("--quiet", action="store_true", help="Nao imprimir no terminal, apenas gravar arquivo")
    args = parser.parse_args()

    caminho_db = obter_caminho_db(args.db_path)
    arquivo_saida = args.saida.resolve() if args.saida else None

    if args.watch > 0:
        print(f"Monitorando {caminho_db} a cada {args.watch}s (Pressione Ctrl+C para encerrar)...")
        try:
            while True:
                dados = atualizar_painel(caminho_db, arquivo_saida)
                if not args.quiet:
                    # Limpar terminal para efeito em tempo real
                    os.system("cls" if os.name == "nt" else "clear")
                    imprimir_terminal(dados)
                    if arquivo_saida:
                        print(f"[Painel sincronizado em: {arquivo_saida}]")
                time.sleep(args.watch)
        except KeyboardInterrupt:
            print("\nMonitoramento encerrado pelo usuario.")
    else:
        dados = atualizar_painel(caminho_db, arquivo_saida)
        if not args.quiet:
            imprimir_terminal(dados)
        if arquivo_saida:
            print(f"[Painel sincronizado com sucesso em: {arquivo_saida}]")


if __name__ == "__main__":
    main()

