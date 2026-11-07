"""Script de povoamento do banco relacional com dados demonstrativos para avaliacao."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys
from typing import Any

diretorio_raiz = Path(__file__).resolve().parent.parent
diretorio_src = diretorio_raiz / "src"
if str(diretorio_src) not in sys.path:
    sys.path.insert(0, str(diretorio_src))
if str(diretorio_raiz) not in sys.path:
    sys.path.insert(0, str(diretorio_raiz))

import pandas as pd

from tokstance.backend.repositories.database import BancoDadosSQLite
from tokstance.backend.repositories.study_repo import RepositorioEstudo
from tokstance.backend.repositories.user_repo import RepositorioUsuarios
from tokstance.backend.services.admin_service import ServicoAdministracao
from tokstance.backend.services.auth_service import ServicoAutenticacao
from tokstance.backend.services.queue_service import ServicoFilaAnotacao
from tokstance.config import FUSO_BRT, agora_brt, resolver_caminhos_dados


def povoar_banco_demonstrativo(
    caminho_banco: Path | None = None,
    reiniciar_tarefa_demo: bool = True,
) -> dict[str, Any]:
    #configuracao de caminhos
    caminhos = resolver_caminhos_dados()
    caminho_db_alvo = caminho_banco or caminhos.arquivo_banco_dados
    caminho_db_alvo.parent.mkdir(parents=True, exist_ok=True)

    banco = BancoDadosSQLite(caminho_db_alvo)
    banco.inicializar_esquema()

    repo_usuarios = RepositorioUsuarios(banco)
    repo_estudo = RepositorioEstudo(banco)
    servico_auth = ServicoAutenticacao(banco=banco, repo_usuarios=repo_usuarios, repo_estudo=repo_estudo)
    servico_admin = ServicoAdministracao(banco=banco, repo_estudo=repo_estudo, repo_usuarios=repo_usuarios)
    servico_fila = ServicoFilaAnotacao(banco=banco, repo_usuarios=repo_usuarios, repo_estudo=repo_estudo)

    #garantir usuarios essenciais para avaliacao
    usuarios_seed = [
        ("professor", "senha123", "professor@ufmg.br", "Professor André Hora"),
        ("rotulador_1", "senha123", "rotulador1@ufmg.br", "Rotulador 1 (Bolsista)"),
        ("rotulador_2", "senha123", "rotulador2@ufmg.br", "Rotulador 2 (Bolsista)"),
        ("gustavo", "senha123", "gustavocunha182020@gmail.com", "Gustavo Cunha"),
    ]

    usuarios_criados: dict[str, int] = {}
    for nome_u, senha_u, email_u, nome_comp_u in usuarios_seed:
        usuario_existente = repo_usuarios.buscar_por_nome_usuario(nome_u)
        if usuario_existente:
            u_id = int(usuario_existente["usuario_id"])
            usuarios_criados[nome_u] = u_id
            banco.executar(
                "UPDATE usuarios SET nome_completo = ?, email = ? WHERE usuario_id = ?",
                (nome_comp_u, email_u, u_id),
            )
        else:
            res_cad = servico_auth.cadastrar_usuario(
                nome_u, senha_u, email=email_u, nome_completo=nome_comp_u
            )
            usuarios_criados[nome_u] = int(res_cad["usuario_id"])

    prof_id = usuarios_criados["professor"]
    rot1_id = usuarios_criados["rotulador_1"]
    rot2_id = usuarios_criados["rotulador_2"]

    #apagar todos os usuarios exceto os essenciais da demonstracao e o gustavo
    usuarios_permitidos = {"professor", "rotulador_1", "rotulador_2", "gustavo"}
    todos_usuarios = banco.consultar_todos("SELECT usuario_id, nome_usuario FROM usuarios")
    for u in todos_usuarios:
        u_nome = u["nome_usuario"]
        u_id = int(u["usuario_id"])
        if u_nome not in usuarios_permitidos:
            tarefas_do_usuario = banco.consultar_todos("SELECT tarefa_id FROM tarefas WHERE criado_por_usuario_id = ?", (u_id,))
            for t in tarefas_do_usuario:
                tid = int(t["tarefa_id"])
                banco.executar("DELETE FROM anotacoes WHERE tarefa_id = ?", (tid,))
                banco.executar("DELETE FROM erros_videos WHERE tarefa_id = ?", (tid,))
                banco.executar("DELETE FROM atribuicoes WHERE tarefa_id = ?", (tid,))
                banco.executar("DELETE FROM videos_tarefa WHERE tarefa_id = ?", (tid,))
                banco.executar("DELETE FROM membros_tarefa WHERE tarefa_id = ?", (tid,))
                banco.executar("DELETE FROM tarefas WHERE tarefa_id = ?", (tid,))
            banco.executar("DELETE FROM recuperacao_senha WHERE usuario_id = ?", (u_id,))
            banco.executar("DELETE FROM membros_tarefa WHERE usuario_id = ?", (u_id,))
            banco.executar("DELETE FROM logs_acesso WHERE usuario_id = ?", (u_id,))
            banco.executar("UPDATE atribuicoes SET usuario_id = NULL WHERE usuario_id = ?", (u_id,))
            banco.executar("UPDATE anotacoes SET usuario_id = NULL WHERE usuario_id = ?", (u_id,))
            banco.executar("UPDATE erros_videos SET usuario_id = NULL WHERE usuario_id = ?", (u_id,))
            banco.executar("DELETE FROM usuarios WHERE usuario_id = ?", (u_id,))

    #remover tarefas anteriores se solicitado para garantir estado limpo
    codigo_convite_demo = "TOK-DEMO2026"
    tarefas_existentes = repo_estudo.listar_tarefas()
    if reiniciar_tarefa_demo and tarefas_existentes:
        for t in tarefas_existentes:
            tid = int(t["tarefa_id"])
            banco.executar("DELETE FROM anotacoes WHERE tarefa_id = ?", (tid,))
            banco.executar("DELETE FROM erros_videos WHERE tarefa_id = ?", (tid,))
            banco.executar("DELETE FROM atribuicoes WHERE tarefa_id = ?", (tid,))
            banco.executar("DELETE FROM videos_tarefa WHERE tarefa_id = ?", (tid,))
            banco.executar("DELETE FROM membros_tarefa WHERE tarefa_id = ?", (tid,))
            banco.executar("DELETE FROM tarefas WHERE tarefa_id = ?", (tid,))
        tarefa_demo = None
    else:
        tarefa_demo = next((t for t in tarefas_existentes if t.get("codigo_convite") == codigo_convite_demo or t.get("titulo") == "Detecção de Posição"), None)

    if not tarefa_demo:
        #carregar dataset autentico de videos de campanha
        caminho_videos_oficial = Path(__file__).resolve().parent.parent / "data" / "videos.csv"
        caminho_reserva_oficial = Path(__file__).resolve().parent.parent / "data" / "videos_reserva.csv"

        if caminho_videos_oficial.exists() and caminho_videos_oficial.stat().st_size > 100:
            df_videos = pd.read_csv(caminho_videos_oficial)
        else:
            df_videos = pd.DataFrame([
                {
                    "id": f"vid_real_{idx}",
                    "url": f"https://www.tiktok.com/@canal/video/{1000 + idx}",
                    "target": "Fim da Escala de Trabalho 6x1" if idx <= 20 else "Reforma Tributária",
                    "video_description": f"Vídeo demonstrativo #{idx} sobre temas relevantes",
                    "voice_to_text": f"Transcrição do áudio do vídeo #{idx}",
                    "video_duration": "30.0",
                }
                for idx in range(1, 31)
            ])

        if caminho_reserva_oficial.exists() and caminho_reserva_oficial.stat().st_size > 100:
            df_reserva = pd.read_csv(caminho_reserva_oficial)
        else:
            df_reserva = pd.DataFrame([
                {
                    "id": f"res_real_{idx}",
                    "url": f"https://www.tiktok.com/@reserva/video/{2000 + idx}",
                    "target": "Fim da Escala de Trabalho 6x1" if idx <= 6 else "Reforma Tributária",
                    "video_description": f"Vídeo reserva #{idx}",
                    "voice_to_text": f"Transcrição do reserva #{idx}",
                    "video_duration": "25.0",
                }
                for idx in range(1, 11)
            ])

        #distancias par a par para o alfa de krippendorff ordinal
        distancias_demo = {
            "Contra|A Favor": 4.0,
            "Contra|Neutro": 1.0,
            "Contra|Vídeo não relacionado ao target": 3.0,
            "A Favor|Neutro": 1.0,
            "A Favor|Vídeo não relacionado ao target": 3.0,
            "Neutro|Vídeo não relacionado ao target": 2.0,
        }

        #criacao da tarefa com 4 vagas e 50% de sobreposicao
        res_tarefa = servico_admin.criar_nova_tarefa(
            usuario_administrador_id=prof_id,
            pool_videos=df_videos,
            quantidade_videos_principal=30 if len(df_videos) >= 30 else len(df_videos),
            videos_reserva_explicitos=df_reserva,
            titulo="Detecção de Posição",
            pergunta="Qual a posição expressa no vídeo em relação ao target?",
            opcoes_posicao=["Contra", "A Favor", "Neutro", "Vídeo não relacionado ao target"],
            distancias_rotulos=distancias_demo,
            numero_vagas=4,
            percentual_sobreposicao=50.0,
            codigo_convite=codigo_convite_demo,
            permitir_admin_como_rotulador=True,
        )
        tarefa_id = int(res_tarefa["tarefa_id"])
    else:
        tarefa_id = int(tarefa_demo["tarefa_id"])

    agora_iso = agora_brt().isoformat()

    #inscrever rotulador_1 e rotulador_2
    servico_auth.entrar_na_tarefa_por_convite(rot1_id, codigo_convite_demo)
    servico_auth.entrar_na_tarefa_por_convite(rot2_id, codigo_convite_demo)

    #simular anotações consistentes entre rotulador_1 e rotulador_2
    df_rot1 = repo_estudo.carregar_atribuicoes_tarefa_df(tarefa_id, rotulador="rotulador_1")
    rotulos_demo = ["Contra", "A Favor", "A Favor", "Neutro", "Contra", "Contra", "A Favor", "Neutro", "Contra", "A Favor"]
    for idx, (_, row) in enumerate(df_rot1.iloc[:10].iterrows()):
        aid = str(row["assignment_id"])
        rotulo = rotulos_demo[idx % len(rotulos_demo)]
        tempo_gasto = 8.5 + (idx * 0.7)
        servico_fila.salvar_anotacao(
            tarefa_id=tarefa_id,
            nome_usuario="rotulador_1",
            assignment_id=aid,
            posicao=rotulo,
            tempo_analise_segundos=tempo_gasto,
        )

    #rotulador_2 anota com concordancia realista
    df_rot2 = repo_estudo.carregar_atribuicoes_tarefa_df(tarefa_id, rotulador="rotulador_2")
    for idx, (_, row) in enumerate(df_rot2.iloc[:8].iterrows()):
        aid = str(row["assignment_id"])
        #alta taxa de concordancia com ligeira variacao ordinal
        rotulo = rotulos_demo[idx % len(rotulos_demo)]
        if idx == 4:
            rotulo = "Neutro"
        tempo_gasto = 9.2 + (idx * 0.5)
        servico_fila.salvar_anotacao(
            tarefa_id=tarefa_id,
            nome_usuario="rotulador_2",
            assignment_id=aid,
            posicao=rotulo,
            tempo_analise_segundos=tempo_gasto,
        )

    #reportar um erro de video de teste por rotulador_1 para auditar no console admin
    if len(df_rot1) > 10:
        aid_erro = str(df_rot1.iloc[10]["assignment_id"])
        servico_fila.reportar_erro_video(
            tarefa_id=tarefa_id,
            nome_usuario="rotulador_1",
            assignment_id=aid_erro,
            tempo_analise_segundos=14.2,
        )
    elif len(df_rot1) > 0:
        aid_erro = str(df_rot1.iloc[-1]["assignment_id"])
        servico_fila.reportar_erro_video(
            tarefa_id=tarefa_id,
            nome_usuario="rotulador_1",
            assignment_id=aid_erro,
            tempo_analise_segundos=14.2,
        )

    #registrar logs de acesso em horario de brasilia
    agora_iso = agora_brt().isoformat()
    banco.executar(
        "INSERT INTO logs_acesso (tarefa_id, usuario_id, usuario, acao, tempo_desde_login_segundos, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
        (tarefa_id, prof_id, "professor", "criacao_tarefa", 0.0, agora_iso),
    )
    banco.executar(
        "INSERT INTO logs_acesso (tarefa_id, usuario_id, usuario, acao, tempo_desde_login_segundos, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
        (tarefa_id, rot1_id, "rotulador_1", "login", 0.0, agora_iso),
    )
    banco.executar(
        "INSERT INTO logs_acesso (tarefa_id, usuario_id, usuario, acao, tempo_desde_login_segundos, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
        (tarefa_id, rot2_id, "rotulador_2", "login", 0.0, agora_iso),
    )
    banco.executar(
        "INSERT INTO logs_acesso (tarefa_id, usuario_id, usuario, acao, tempo_desde_login_segundos, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
        (tarefa_id, prof_id, "professor", "login", 0.0, agora_iso),
    )

    #atualizar automaticamente o painel STATUS_BANCO.md
    try:
        from scripts.status_banco import atualizar_painel
        arquivo_md = Path(__file__).resolve().parent.parent / "STATUS_BANCO.md"
        atualizar_painel(caminho_db_alvo, arquivo_md)
    except Exception:
        pass

    return {
        "status": "sucesso",
        "banco_path": str(caminho_db_alvo),
        "tarefa_id": tarefa_id,
        "codigo_convite": codigo_convite_demo,
        "usuarios": usuarios_criados,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Povoamento de dados demonstrativos do TokStance")
    parser.add_argument("--db-path", type=Path, default=None, help="Caminho do arquivo SQLite de destino")
    parser.add_argument("--sem-reset", action="store_true", help="Nao reiniciar tarefa se ja existir")
    args = parser.parse_args()

    resultado = povoar_banco_demonstrativo(
        caminho_banco=args.db_path,
        reiniciar_tarefa_demo=not args.sem_reset,
    )

    print("=" * 60)
    print(" TokStance! - Banco Demonstrativo Povoado com Sucesso")
    print("=" * 60)
    print(f"Banco SQLite: {resultado['banco_path']}")
    print(f"Tarefa ID: {resultado['tarefa_id']}")
    print(f"Código de Convite da Tarefa: {resultado['codigo_convite']}")
    print("\nUsuários para Teste / Avaliação (Senha padrão: senha123):")
    print(" - Professor (Coordenador & Rotulador): professor")
    print(" - Rotulador 1 (Anotador ativo): rotulador_1")
    print(" - Rotulador 2 (Anotador ativo): rotulador_2")
    print(" - Gustavo: gustavo")
    print("=" * 60)


if __name__ == "__main__":
    main()
