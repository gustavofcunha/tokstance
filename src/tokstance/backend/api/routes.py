"""Rotas REST do backend FastAPI para monitoramento de integridade e sumario operacional."""

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from tokstance.backend.repositories.database import BancoDadosSQLite
from tokstance.backend.repositories.study_repo import RepositorioEstudo
from tokstance.backend.services.admin_service import ServicoAdministracao

roteador_api = APIRouter(prefix="/api", tags=["TokStance API"])


@roteador_api.get("/health")
def verificar_saude() -> dict[str, Any]:
    """Retorna o status operacional da API e a integridade do banco SQLite."""
    banco = BancoDadosSQLite()
    try:
        tabelas = banco.listar_tabelas()
        return {
            "status": "ok",
            "servico": "tokstance",
            "banco": "conectado",
            "tabelas_disponiveis": len(tabelas),
        }
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Falha na conexao com o banco SQLite: {exc}",
        ) from exc


@roteador_api.get("/summary")
def obter_resumo_tarefas(
    tarefa_id: int | None = Query(default=None, description="Identificador da tarefa para resumo detalhado"),
) -> dict[str, Any]:
    """Retorna metricas e sumario operacional de uma tarefa ou a contagem geral de tarefas cadastradas."""
    banco = BancoDadosSQLite()
    repo_estudo = RepositorioEstudo(banco)
    servico_admin = ServicoAdministracao(banco=banco, repo_estudo=repo_estudo)

    if tarefa_id is not None:
        try:
            return servico_admin.obter_metricas_operacionais(int(tarefa_id))
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    tarefas = repo_estudo.listar_tarefas()
    return {
        "total_tarefas": len(tarefas),
        "tarefas": [
            {
                "tarefa_id": int(t["tarefa_id"]),
                "slug_tarefa": str(t["slug_tarefa"]),
                "titulo": str(t["titulo"]),
                "numero_vagas": int(t["numero_vagas"]),
                "percentual_sobreposicao": int(t["percentual_sobreposicao"]),
                "codigo_convite": str(t["codigo_convite"]),
                "criado_em": str(t["criado_em"]),
            }
            for t in tarefas
        ],
    }
