"""Servico de fila de anotacao por tarefa, aviso de conteudo sensivel, regra de 10s e substituicao."""

import tempfile
from pathlib import Path
from typing import Any

from tokstance.backend.domain.replacements import (
    aplicar_substituicoes_reserva,
    ler_erros_atribuicoes,
)
from tokstance.backend.repositories.database import BancoDadosSQLite
from tokstance.backend.repositories.study_repo import RepositorioEstudo
from tokstance.backend.repositories.user_repo import RepositorioUsuarios
from tokstance.backend.security.validators import validar_nome_usuario
from tokstance.config import SEGUNDOS_MINIMOS_REPORTE_ERRO


class ServicoFilaAnotacao:
    """Gerencia a fila de videos de um rotulador dentro de uma tarefa especifica."""

    def __init__(
        self,
        banco: BancoDadosSQLite | None = None,
        repo_usuarios: RepositorioUsuarios | None = None,
        repo_estudo: RepositorioEstudo | None = None,
        segundos_minimos_erro: float = SEGUNDOS_MINIMOS_REPORTE_ERRO,
    ) -> None:
        self.banco = banco or BancoDadosSQLite()
        self.repo_usuarios = repo_usuarios or RepositorioUsuarios(self.banco)
        self.repo_estudo = repo_estudo or RepositorioEstudo(
            self.banco, self.repo_usuarios
        )
        self.segundos_minimos_erro = float(segundos_minimos_erro)

    def obter_estado_fila(
        self,
        tarefa_id: int,
        nome_usuario: str,
        aviso_sensivel_aceito: bool = False,
    ) -> dict[str, Any]:
        """Recupera a posicao exata da fila do rotulador na tarefa e o video atual."""
        nome_limpo = validar_nome_usuario(nome_usuario)
        tarefa = self.repo_estudo.buscar_tarefa_por_id(int(tarefa_id))
        if tarefa is None:
            raise ValueError(f"Tarefa {tarefa_id} não encontrada.")

        fila_df = self.repo_estudo.carregar_atribuicoes_tarefa_df(
            int(tarefa_id), rotulador=nome_limpo
        )
        anotadas_df = self.repo_estudo.carregar_anotacoes_tarefa_df(
            int(tarefa_id), rotulador=nome_limpo
        )
        erros_df = self.repo_estudo.carregar_erros_videos_tarefa_df(int(tarefa_id))

        ids_anotados = (
            set(anotadas_df["assignment_id"].astype(str))
            if not anotadas_df.empty
            else set()
        )
        ids_erros_sem_reserva: set[str] = set()
        if not erros_df.empty:
            erros_rotulador = erros_df[
                erros_df["labeler"].astype(str).eq(nome_limpo)
                & erros_df["replacement_assignment_id"].astype(str).str.strip().eq("")
            ]
            ids_erros_sem_reserva = set(
                erros_rotulador["assignment_id"].astype(str)
            )

        ids_processados = ids_anotados | ids_erros_sem_reserva
        total_videos = len(fila_df)
        pendentes_df = (
            fila_df[~fila_df["assignment_id"].astype(str).isin(ids_processados)]
            if not fila_df.empty
            else fila_df
        )
        pendentes = len(pendentes_df)
        posicao_concluida = max(0, total_videos - pendentes)
        concluida = total_videos > 0 and pendentes == 0

        video_atual: dict[str, Any] | None = None
        if pendentes > 0:
            linha = pendentes_df.iloc[0]
            video_atual = {
                "assignment_version": str(linha["assignment_version"]),
                "assignment_id": str(linha["assignment_id"]),
                "labeler": str(linha["labeler"]),
                "video_id": str(linha["video_id"]),
                "url": str(linha["url"]),
                "target": str(linha["target"]),
                "video_description": str(linha.get("video_description", "")),
                "voice_to_text": str(linha.get("voice_to_text", "")),
                "video_duration": str(linha.get("video_duration", "")),
            }

        return {
            "tarefa_id": int(tarefa["tarefa_id"]),
            "titulo": str(tarefa["titulo"]),
            "pergunta": str(tarefa["pergunta"]),
            "opcoes_posicao": list(tarefa["opcoes_posicao"]),
            "rotulador": nome_limpo,
            "total_videos": total_videos,
            "posicao_concluida": posicao_concluida,
            "pendentes": pendentes,
            "concluida": concluida,
            "exibir_aviso_sensivel": bool(pendentes > 0 and not aviso_sensivel_aceito),
            "video_atual": video_atual,
        }

    def aceitar_aviso_conteudo_sensivel(
        self,
        tarefa_id: int,
        nome_usuario: str,
    ) -> dict[str, Any]:
        """Registra a aceitacao do aviso de conteudo sensivel e libera o primeiro video."""
        nome_limpo = validar_nome_usuario(nome_usuario)
        self.repo_estudo.registrar_log_acesso(
            usuario=nome_limpo,
            acao="aceitar_aviso_sensivel",
            tarefa_id=int(tarefa_id),
        )
        return self.obter_estado_fila(
            tarefa_id=int(tarefa_id),
            nome_usuario=nome_limpo,
            aviso_sensivel_aceito=True,
        )

    def parar_rotulacao(
        self,
        tarefa_id: int,
        nome_usuario: str,
        tempo_desde_login_segundos: float | None = None,
    ) -> dict[str, Any]:
        """Registra a interrupcao voluntaria da sessao de rotulacao pelo usuario."""
        nome_limpo = validar_nome_usuario(nome_usuario)
        self.repo_estudo.registrar_log_acesso(
            usuario=nome_limpo,
            acao="parar_rotulacao",
            tarefa_id=int(tarefa_id),
            tempo_desde_login_segundos=tempo_desde_login_segundos,
        )
        return {
            "tarefa_id": int(tarefa_id),
            "rotulador": nome_limpo,
            "interrompido": True,
        }

    def salvar_anotacao_e_avancar(
        self,
        tarefa_id: int,
        nome_usuario: str,
        assignment_id: str,
        posicao: str | None,
        tempo_analise_segundos: float,
        login_time_segundos: float = 0.0,
    ) -> dict[str, Any]:
        """Valida a resposta selecionada, salva a anotacao no SQLite e avanca para o proximo video."""
        if posicao is None or not str(posicao).strip():
            raise ValueError("Selecione uma opção de resposta antes de salvar.")

        nome_limpo = validar_nome_usuario(nome_usuario)
        fila_df = self.repo_estudo.carregar_atribuicoes_tarefa_df(
            int(tarefa_id), rotulador=nome_limpo
        )
        correspondentes = fila_df[
            fila_df["assignment_id"].astype(str).eq(str(assignment_id).strip())
        ]
        if correspondentes.empty:
            raise ValueError("Atribuição de vídeo não encontrada na fila do rotulador.")

        item = correspondentes.iloc[0]
        anotacao = self.repo_estudo.registrar_anotacao(
            tarefa_id=int(tarefa_id),
            assignment_id=str(item["assignment_id"]),
            rotulador=nome_limpo,
            video_id=str(item["video_id"]),
            url=str(item["url"]),
            target=str(item["target"]),
            posicao=str(posicao).strip(),
            tempo_analise_segundos=float(tempo_analise_segundos or 0.0),
            video_duration=str(item.get("video_duration", "")),
        )
        proximo_estado = self.obter_estado_fila(
            tarefa_id=int(tarefa_id),
            nome_usuario=nome_limpo,
            aviso_sensivel_aceito=True,
        )
        return {
            "anotacao_salva": anotacao,
            "estado_fila": proximo_estado,
        }

    def salvar_anotacao(
        self,
        tarefa_id: int,
        nome_usuario: str,
        assignment_id: str,
        posicao: str | None = None,
        tempo_analise_segundos: float = 0.0,
        stance: str | None = None,
        login_time_segundos: float = 0.0,
    ) -> dict[str, Any]:
        """Alias retrocompativel para salvar_anotacao_e_avancar."""
        escolha = posicao if posicao is not None else stance
        return self.salvar_anotacao_e_avancar(
            tarefa_id=tarefa_id,
            nome_usuario=nome_usuario,
            assignment_id=assignment_id,
            posicao=escolha,
            tempo_analise_segundos=tempo_analise_segundos,
            login_time_segundos=login_time_segundos,
        )

    def reportar_erro_video(
        self,
        tarefa_id: int,
        nome_usuario: str,
        assignment_id: str,
        tempo_analise_segundos: float,
        login_time_segundos: float = 0.0,
    ) -> dict[str, Any]:
        """Valida a espera minima de 10s, registra o erro e aciona substituicao por reserva."""
        tempo_decorrido = float(tempo_analise_segundos or 0.0)
        #regra de negocio exige aguardar 10 segundos antes de reportar erro de carregamento
        if tempo_decorrido < self.segundos_minimos_erro:
            faltam = max(1, int(round(self.segundos_minimos_erro - tempo_decorrido)))
            raise ValueError(
                f"Aguarde pelo menos {int(self.segundos_minimos_erro)} segundos tentando carregar o vídeo antes de reportar erro (faltam ~{faltam}s)."
            )

        nome_limpo = validar_nome_usuario(nome_usuario)
        fila_df = self.repo_estudo.carregar_atribuicoes_tarefa_df(
            int(tarefa_id), rotulador=nome_limpo
        )
        correspondentes = fila_df[
            fila_df["assignment_id"].astype(str).eq(str(assignment_id).strip())
        ]
        if correspondentes.empty:
            raise ValueError("Atribuição de vídeo não encontrada na fila do rotulador.")

        item = correspondentes.iloc[0]
        self.repo_estudo.registrar_erro_video(
            tarefa_id=int(tarefa_id),
            video_id=str(item["video_id"]),
            url=str(item["url"]),
            rotulador=nome_limpo,
            assignment_id=str(item["assignment_id"]),
        )

        reservas_disponiveis = self.repo_estudo.carregar_videos_tarefa_df(
            int(tarefa_id), tipo_pool="reserva"
        )
        if reservas_disponiveis.empty:
            estado_fila = self.obter_estado_fila(
                tarefa_id=int(tarefa_id),
                nome_usuario=nome_limpo,
                aviso_sensivel_aceito=True,
            )
            return {
                "tarefa_id": int(tarefa_id),
                "rotulador": nome_limpo,
                "erro_registrado": dict(item),
                "status_substituicao": "SEM_RESERVA_DISPONIVEL",
                "estado_fila": estado_fila,
            }

        with tempfile.TemporaryDirectory() as pasta_temp:
            caminhos_temp = self.repo_estudo.exportar_arquivos_tarefa(
                int(tarefa_id), Path(pasta_temp)
            )
            todas_atribuicoes = self.repo_estudo.carregar_atribuicoes_tarefa_df(
                int(tarefa_id)
            )
            atribuicoes_atualizadas = aplicar_substituicoes_reserva(
                todas_atribuicoes, caminhos_temp.diretorio_base
            )
            erros_atualizados = ler_erros_atribuicoes(caminhos_temp.arquivo_erros)
            self.repo_estudo.salvar_atribuicoes_tarefa_df(
                int(tarefa_id), atribuicoes_atualizadas
            )
            self.repo_estudo.salvar_erros_videos_tarefa_df(
                int(tarefa_id), erros_atualizados
            )

        erros_finais = self.repo_estudo.carregar_erros_videos_tarefa_df(int(tarefa_id))
        ultimo_erro = (
            erros_finais.iloc[-1].to_dict() if not erros_finais.empty else {}
        )
        proximo_estado = self.obter_estado_fila(
            tarefa_id=int(tarefa_id),
            nome_usuario=nome_limpo,
            aviso_sensivel_aceito=True,
        )
        return {
            "erro_registrado": ultimo_erro,
            "status_substituicao": str(ultimo_erro.get("replacement_status", "")),
            "estado_fila": proximo_estado,
        }
