"""Servico de administracao de tarefas, metricas operacionais e concordancia."""

from pathlib import Path
from typing import Any

import pandas as pd

from tokstance.backend.domain.agreement import (
    calcular_concordancia,
    encontrar_anotacoes_rapidas,
)
from tokstance.backend.domain.models import (
    NOME_TAREFA_PADRAO,
    OPCOES_TAREFA_PADRAO,
    PERGUNTA_TAREFA_PADRAO,
    POOL_PRINCIPAL,
    POOL_RESERVA,
)
from tokstance.backend.repositories.database import BancoDadosSQLite
from tokstance.backend.repositories.study_repo import RepositorioEstudo
from tokstance.backend.repositories.user_repo import RepositorioUsuarios
from tokstance.config import CaminhosDados


class ServicoAdministracao:
    """Gerencia casos de uso administrativos: criacao de tarefas, KPIs e auditoria."""

    def __init__(
        self,
        banco: BancoDadosSQLite | None = None,
        repo_usuarios: RepositorioUsuarios | None = None,
        repo_estudo: RepositorioEstudo | None = None,
    ) -> None:
        self.banco = banco or BancoDadosSQLite()
        self.repo_usuarios = repo_usuarios or RepositorioUsuarios(self.banco)
        self.repo_estudo = repo_estudo or RepositorioEstudo(
            self.banco, self.repo_usuarios
        )

    def criar_nova_tarefa(
        self,
        usuario_administrador_id: int,
        pool_videos: pd.DataFrame,
        quantidade_videos_principal: int | None = None,
        videos_reserva_explicitos: pd.DataFrame | None = None,
        titulo: str = NOME_TAREFA_PADRAO,
        pergunta: str = PERGUNTA_TAREFA_PADRAO,
        opcoes_posicao: list[str] | tuple[str, ...] | str | None = None,
        distancias_rotulos: dict[str, float] | None = None,
        numero_vagas: int = 2,
        percentual_sobreposicao: float = 0.0,
        codigo_convite: str | None = None,
        permitir_admin_como_rotulador: bool = True,
    ) -> dict[str, Any]:
        """Cria uma tarefa, particiona o pool e vincula o criador como administrador e rotulador."""
        tarefa = self.repo_estudo.criar_tarefa(
            criado_por_usuario_id=int(usuario_administrador_id),
            pool_videos=pool_videos,
            quantidade_videos_principal=quantidade_videos_principal,
            videos_reserva_explicitos=videos_reserva_explicitos,
            titulo=titulo,
            pergunta=pergunta,
            opcoes_posicao=opcoes_posicao if opcoes_posicao is not None else list(OPCOES_TAREFA_PADRAO),
            distancias_rotulos=distancias_rotulos,
            numero_vagas=numero_vagas,
            percentual_sobreposicao=percentual_sobreposicao,
            codigo_convite=codigo_convite,
        )

        usuario_admin = self.repo_usuarios.buscar_por_id(int(usuario_administrador_id))
        if permitir_admin_como_rotulador and usuario_admin is not None:
            self.repo_estudo.vincular_rotulador_na_tarefa(
                tarefa_id=int(tarefa["tarefa_id"]),
                usuario_id=int(usuario_administrador_id),
                nome_usuario=str(usuario_admin["nome_usuario"]),
            )

        self.repo_estudo.registrar_log_acesso(
            usuario=str(usuario_admin["nome_usuario"]) if usuario_admin else "admin",
            acao="criar_tarefa",
            tarefa_id=int(tarefa["tarefa_id"]),
            usuario_id=int(usuario_administrador_id),
        )
        return tarefa

    def obter_metricas_operacionais(self, tarefa_id: int) -> dict[str, Any]:
        """Calcula progresso global, status de vagas e alertas de tempo de uma tarefa."""
        tarefa = self.repo_estudo.buscar_tarefa_por_id(int(tarefa_id))
        if tarefa is None:
            raise ValueError(f"Tarefa {tarefa_id} não encontrada.")

        principais = self.repo_estudo.carregar_videos_tarefa_df(
            int(tarefa_id), tipo_pool=POOL_PRINCIPAL
        )
        reservas = self.repo_estudo.carregar_videos_tarefa_df(
            int(tarefa_id), tipo_pool=POOL_RESERVA
        )
        atribuicoes = self.repo_estudo.carregar_atribuicoes_tarefa_df(int(tarefa_id))
        anotacoes = self.repo_estudo.carregar_anotacoes_tarefa_df(int(tarefa_id))
        erros = self.repo_estudo.carregar_erros_videos_tarefa_df(int(tarefa_id))

        total_atribuicoes = len(atribuicoes)
        total_anotacoes = len(anotacoes)
        progresso_pct = (
            round((total_anotacoes / total_atribuicoes) * 100.0, 1)
            if total_atribuicoes > 0
            else 0.0
        )

        todos_videos = (
            pd.concat([principais, reservas], ignore_index=True)
            if not reservas.empty
            else principais
        )
        anotacoes_rapidas = encontrar_anotacoes_rapidas(anotacoes, todos_videos)
        configuracao = self.repo_estudo.obter_configuracao_tarefa(int(tarefa_id))
        concordancia = calcular_concordancia(anotacoes, configuracao)

        #distribuicao tematica por target
        targets_principais = (
            principais["target"].dropna().astype(str).str.strip().tolist()
            if not principais.empty and "target" in principais.columns
            else []
        )
        targets_reservas = (
            reservas["target"].dropna().astype(str).str.strip().tolist()
            if not reservas.empty and "target" in reservas.columns
            else []
        )
        todos_targets = sorted(list(set(targets_principais + targets_reservas)))
        total_acervo = len(principais) + len(reservas)

        distribuicao_targets: list[dict[str, Any]] = []
        for alvo in todos_targets:
            if not alvo:
                continue
            qtd_p = targets_principais.count(alvo)
            qtd_r = targets_reservas.count(alvo)
            qtd_t = qtd_p + qtd_r
            pct = round((qtd_t / total_acervo) * 100.0, 1) if total_acervo > 0 else 0.0
            distribuicao_targets.append(
                {
                    "target": alvo,
                    "principais": qtd_p,
                    "reservas": qtd_r,
                    "total": qtd_t,
                    "percentual": pct,
                }
            )

        #progresso individual por rotulador
        progresso_rotuladores: list[dict[str, Any]] = []
        if not atribuicoes.empty:
            for rotulador, grupo_atrib in atribuicoes.groupby("labeler"):
                ids_grupo = set(grupo_atrib["assignment_id"].astype(str))
                anotadas_grupo = (
                    int(anotacoes["assignment_id"].astype(str).isin(ids_grupo).sum())
                    if not anotacoes.empty
                    else 0
                )
                progresso_rotuladores.append(
                    {
                        "rotulador": str(rotulador),
                        "total": len(grupo_atrib),
                        "concluidas": anotadas_grupo,
                        "pendentes": max(0, len(grupo_atrib) - anotadas_grupo),
                    }
                )

        return {
            "tarefa_id": int(tarefa["tarefa_id"]),
            "titulo": str(tarefa["titulo"]),
            "total_videos_acervo": total_acervo,
            "total_videos_principais": len(principais),
            "total_videos_reservas": len(reservas),
            "distribuicao_targets": distribuicao_targets,
            "total_atribuicoes": total_atribuicoes,
            "total_anotacoes": total_anotacoes,
            "progresso_percentual": progresso_pct,
            "total_erros_reportados": len(erros),
            "total_anotacoes_rapidas": len(anotacoes_rapidas),
            "alfa_krippendorff": concordancia.get("alfa"),
            "progresso_rotuladores": progresso_rotuladores,
            "concordancia": concordancia,
        }

    def exportar_arquivos_console(
        self,
        tarefa_id: int,
        diretorio_destino: Path | str | None = None,
    ) -> CaminhosDados:
        """Gera sob demanda os 8 artefatos CSV/JSON para download no Console Admin."""
        return self.repo_estudo.exportar_arquivos_tarefa(
            tarefa_id=int(tarefa_id),
            diretorio_destino=diretorio_destino,
        )

    def excluir_tarefa(self, tarefa_id: int, usuario_administrador_id: int) -> bool:
        """Exclui uma tarefa criada pelo administrador e todos os dados associados."""
        return self.repo_estudo.excluir_tarefa(
            tarefa_id=int(tarefa_id),
            usuario_administrador_id=int(usuario_administrador_id),
        )
