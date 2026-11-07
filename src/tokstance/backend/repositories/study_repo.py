"""Repositorio relacional de tarefas, divisao de pool de videos, anotacoes, erros, logs e exportacoes."""

import json
from pathlib import Path
import re
import sqlite3
from typing import Any

import pandas as pd

from tokstance.backend.domain.agreement import calcular_concordancia
from tokstance.backend.domain.assignments import (
    gerar_atribuicoes,
    versao_atribuicao,
    vincular_ou_alocar_vaga_rotulador,
)
from tokstance.backend.domain.models import (
    COLUNAS_ATRIBUICAO,
    COLUNAS_ERRO,
    COLUNAS_LOG,
    COLUNAS_OPCIONAIS_VIDEO,
    COLUNAS_RESULTADO,
    COLUNAS_VIDEO,
    DISTANCIAS_ROTULOS_PADRAO,
    NOME_TAREFA_PADRAO,
    OPCOES_TAREFA_PADRAO,
    PAPEL_ADMINISTRADOR,
    PAPEL_ROTULADOR,
    PERGUNTA_TAREFA_PADRAO,
    POOL_PRINCIPAL,
    POOL_RESERVA,
    TIPOS_POOL_VALIDOS,
    dividir_videos_principal_e_reserva,
    gerar_combinacoes_rotulos,
    salvar_configuracao,
)
from tokstance.backend.repositories.database import BancoDadosSQLite
from tokstance.backend.repositories.user_repo import RepositorioUsuarios
from tokstance.backend.security.validators import (
    gerar_codigo_convite,
    validar_codigo_convite,
    validar_nome_usuario,
    validar_opcoes_tarefa,
    validar_tamanho_texto,
)
from tokstance.config import (
    CaminhosDados,
    formatar_data_hora_brt,
    resolver_caminhos_dados,
)


def _normalizar_dataframe_videos(quadro: pd.DataFrame) -> pd.DataFrame:
    """Garante todas as colunas padrao de video sem valores nulos."""
    colunas = list(COLUNAS_VIDEO)
    if quadro is None or quadro.empty:
        return pd.DataFrame(columns=colunas)
    copia = quadro.copy()
    for coluna in ("id", "url", "target"):
        if coluna not in copia.columns:
            raise ValueError(f"Coluna obrigatória de vídeo ausente: {coluna}")
    for coluna in COLUNAS_OPCIONAIS_VIDEO:
        if coluna not in copia.columns:
            copia[coluna] = ""
    copia = copia[colunas].fillna("")
    copia["id"] = copia["id"].astype(str).str.strip()
    copia["url"] = copia["url"].astype(str).str.strip()
    copia["target"] = copia["target"].astype(str)
    copia = copia[(copia["id"] != "") & (copia["url"] != "")].drop_duplicates(
        subset=["id"], keep="first"
    )
    return copia.reset_index(drop=True)


class RepositorioEstudo:
    """Gerencia tarefas, pools de video, atribuicoes, anotacoes, erros e exportacoes."""

    def __init__(
        self,
        banco: BancoDadosSQLite | None = None,
        repo_usuarios: RepositorioUsuarios | None = None,
    ) -> None:
        self.banco = banco or BancoDadosSQLite()
        self.repo_usuarios = repo_usuarios or RepositorioUsuarios(self.banco)

    def _gerar_slug_unico(self, titulo: str) -> str:
        base = re.sub(r"[^a-z0-9]+", "-", str(titulo or "tarefa").lower()).strip("-")
        if not base:
            base = "tarefa"
        candidato = base[:48]
        contador = 1
        while (
            self.banco.consultar_um(
                "SELECT tarefa_id FROM tarefas WHERE slug_tarefa = ?;",
                (candidato,),
            )
            is not None
        ):
            contador += 1
            candidato = f"{base[:40]}-{contador}"
        return candidato

    def _deserializar_tarefa(self, linha: dict[str, Any] | None) -> dict[str, Any] | None:
        if linha is None:
            return None
        opcoes = json.loads(str(linha.get("opcoes_json") or "[]"))
        distancias = json.loads(str(linha.get("distancias_rotulos_json") or "{}"))
        resultado = dict(linha)
        resultado["opcoes_posicao"] = list(opcoes)
        resultado["distancias_rotulos"] = {
            str(par): float(peso) for par, peso in distancias.items()
        }
        t_id = linha.get("tarefa_id")
        if t_id is not None:
            contagem = self.banco.consultar_um(
                """
                SELECT
                    SUM(CASE WHEN tipo_pool = 'principal' THEN 1 ELSE 0 END) AS qtd_p,
                    SUM(CASE WHEN tipo_pool = 'reserva' THEN 1 ELSE 0 END) AS qtd_r
                FROM videos_tarefa
                WHERE tarefa_id = ?;
                """,
                (int(t_id),),
            )
            resultado["quantidade_videos_principal"] = int(contagem["qtd_p"] or 0) if contagem else 0
            resultado["quantidade_videos_reserva"] = int(contagem["qtd_r"] or 0) if contagem else 0
        else:
            resultado["quantidade_videos_principal"] = 0
            resultado["quantidade_videos_reserva"] = 0
        return resultado

    def criar_tarefa(
        self,
        criado_por_usuario_id: int,
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
        rotuladores_iniciais: list[str] | None = None,
        criado_em: str | None = None,
    ) -> dict[str, Any]:
        """Cria uma nova tarefa, divide os videos em principal/reserva e gera as vagas iniciais."""
        criador = self.repo_usuarios.buscar_por_id(int(criado_por_usuario_id))
        if criador is None:
            raise ValueError("Usuário criador da tarefa não encontrado.")

        titulo_limpo = validar_tamanho_texto(
            titulo or NOME_TAREFA_PADRAO, nome_campo="titulo", tamanho_maximo=160
        )
        pergunta_limpa = validar_tamanho_texto(
            pergunta or PERGUNTA_TAREFA_PADRAO,
            nome_campo="pergunta",
            tamanho_maximo=320,
        )
        opcoes_limpas = validar_opcoes_tarefa(
            opcoes_posicao if opcoes_posicao is not None else list(OPCOES_TAREFA_PADRAO)
        )
        base_distancias = (
            distancias_rotulos
            if distancias_rotulos is not None
            else (
                dict(DISTANCIAS_ROTULOS_PADRAO)
                if opcoes_limpas == list(OPCOES_TAREFA_PADRAO)
                else None
            )
        )
        distancias_limpas = gerar_combinacoes_rotulos(opcoes_limpas, base_distancias)

        vagas = max(1, int(numero_vagas))
        sobreposicao = max(0, min(100, int(round(float(percentual_sobreposicao or 0.0)))))
        convite = (
            validar_codigo_convite(codigo_convite)
            if codigo_convite and str(codigo_convite).strip()
            else gerar_codigo_convite("TOK")
        )

        pool_norm = _normalizar_dataframe_videos(pool_videos)
        if pool_norm.empty:
            raise ValueError("O conjunto de vídeos da tarefa não pode estar vazio.")

        total_disponivel = len(pool_norm)
        qtd_distribuir = (
            int(quantidade_videos_principal)
            if quantidade_videos_principal is not None
            else total_disponivel
        )
        if qtd_distribuir <= 0:
            raise ValueError(
                "A quantidade de vídeos a distribuir (vídeos principais) deve ser maior que zero."
            )
        if qtd_distribuir > total_disponivel:
            raise ValueError(
                f"A quantidade de vídeos a distribuir ({qtd_distribuir}) não pode ser maior que o total disponível na coleção ({total_disponivel})."
            )

        principais_df, excedente_reserva = dividir_videos_principal_e_reserva(
            pool_norm, qtd_distribuir
        )
        if videos_reserva_explicitos is not None:
            res_norm = _normalizar_dataframe_videos(videos_reserva_explicitos)
            reservas_df = (
                pd.concat([excedente_reserva, res_norm], ignore_index=True)
                if not excedente_reserva.empty
                else res_norm
            )
        else:
            reservas_df = excedente_reserva

        if principais_df.empty:
            raise ValueError("Nenhum vídeo principal selecionado para a tarefa.")

        rotuladores_base = (
            [str(item).strip() for item in rotuladores_iniciais if str(item).strip()]
            if rotuladores_iniciais
            else [f"vaga_{indice}" for indice in range(1, vagas + 1)]
        )
        config_calculo = {
            "administradores": [str(criador["nome_usuario"])],
            "rotuladores": rotuladores_base,
            "percentual_sobreposicao": sobreposicao,
            "tarefa": titulo_limpo,
            "pergunta": pergunta_limpa,
            "opcoes_posicao": opcoes_limpas,
            "distancias_rotulos": distancias_limpas,
            "codigo_convite": convite,
        }
        versao = versao_atribuicao(config_calculo, principais_df)
        atribuicoes_df = gerar_atribuicoes(
            config_calculo, principais_df, persistir=False
        )
        videos_por_rotulador = (
            int(
                atribuicoes_df.groupby("labeler")["video_id"].count().max()
            )
            if not atribuicoes_df.empty
            else len(principais_df)
        )
        instante = str(criado_em or formatar_data_hora_brt())
        slug = self._gerar_slug_unico(titulo_limpo)

        try:
            tarefa_id = self.banco.executar(
                """
                INSERT INTO tarefas (
                    slug_tarefa, titulo, pergunta, opcoes_json, distancias_rotulos_json,
                    numero_vagas, videos_por_rotulador, percentual_sobreposicao,
                    codigo_convite, versao_atribuicao, criado_por_usuario_id, criado_em
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    slug,
                    titulo_limpo,
                    pergunta_limpa,
                    json.dumps(opcoes_limpas, ensure_ascii=False),
                    json.dumps(distancias_limpas, ensure_ascii=False),
                    vagas,
                    videos_por_rotulador,
                    sobreposicao,
                    convite,
                    versao,
                    int(criado_por_usuario_id),
                    instante,
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError(
                f"O código de convite '{convite}' já está em uso por outra tarefa."
            ) from exc

        self.repo_usuarios.adicionar_membro_tarefa(
            tarefa_id=tarefa_id,
            usuario_id=int(criado_por_usuario_id),
            papel=PAPEL_ADMINISTRADOR,
            entrou_em=instante,
        )
        self._inserir_videos_tarefa(tarefa_id, principais_df, POOL_PRINCIPAL)
        self._inserir_videos_tarefa(tarefa_id, reservas_df, POOL_RESERVA)
        self.salvar_atribuicoes_tarefa_df(tarefa_id, atribuicoes_df)

        for rotulador_inicial in rotuladores_base:
            if not rotulador_inicial.startswith("vaga_"):
                usuario_rot = self.repo_usuarios.buscar_por_identificador(
                    rotulador_inicial
                )
                if usuario_rot is not None:
                    self.repo_usuarios.adicionar_membro_tarefa(
                        tarefa_id=tarefa_id,
                        usuario_id=int(usuario_rot["usuario_id"]),
                        papel=PAPEL_ROTULADOR,
                        vaga_atribuida=rotulador_inicial,
                        entrou_em=instante,
                    )

        criada = self.buscar_tarefa_por_id(tarefa_id)
        if criada is None:
            raise RuntimeError("Falha ao recuperar tarefa recém-criada.")
        return criada

    def _inserir_videos_tarefa(
        self,
        tarefa_id: int,
        quadro_videos: pd.DataFrame,
        tipo_pool: str,
    ) -> None:
        if tipo_pool not in TIPOS_POOL_VALIDOS:
            raise ValueError(f"Tipo de pool inválido: {tipo_pool}")
        if quadro_videos is None or quadro_videos.empty:
            return
        with self.banco.conectar() as conexao:
            for _, linha in quadro_videos.iterrows():
                conexao.execute(
                    """
                    INSERT OR REPLACE INTO videos_tarefa (
                        tarefa_id, video_id, tipo_pool, url, target,
                        video_description, voice_to_text, video_duration
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        int(tarefa_id),
                        str(linha["id"]).strip(),
                        tipo_pool,
                        str(linha["url"]).strip(),
                        str(linha["target"]),
                        str(linha.get("video_description", "")),
                        str(linha.get("voice_to_text", "")),
                        str(linha.get("video_duration", "")),
                    ),
                )

    def buscar_tarefa_por_id(self, tarefa_id: int) -> dict[str, Any] | None:
        """Busca uma tarefa pelo seu identificador primario."""
        linha = self.banco.consultar_um(
            "SELECT * FROM tarefas WHERE tarefa_id = ?;",
            (int(tarefa_id),),
        )
        return self._deserializar_tarefa(linha)

    def buscar_tarefa_por_codigo_convite(
        self,
        codigo_convite: str,
    ) -> dict[str, Any] | None:
        """Busca uma tarefa pelo seu codigo de convite exclusivo."""
        if not isinstance(codigo_convite, str) or not codigo_convite.strip():
            return None
        linha = self.banco.consultar_um(
            "SELECT * FROM tarefas WHERE codigo_convite = ?;",
            (codigo_convite.strip(),),
        )
        return self._deserializar_tarefa(linha)

    def buscar_tarefa_por_slug(self, slug_tarefa: str) -> dict[str, Any] | None:
        """Busca uma tarefa pelo seu slug textual."""
        if not isinstance(slug_tarefa, str) or not slug_tarefa.strip():
            return None
        linha = self.banco.consultar_um(
            "SELECT * FROM tarefas WHERE slug_tarefa = ?;",
            (slug_tarefa.strip(),),
        )
        return self._deserializar_tarefa(linha)

    def listar_tarefas(self) -> list[dict[str, Any]]:
        """Retorna todas as tarefas cadastradas ordenadas da mais recente para a mais antiga."""
        linhas = self.banco.consultar_todos(
            "SELECT * FROM tarefas ORDER BY tarefa_id DESC;"
        )
        return [
            deserializada
            for linha in linhas
            if (deserializada := self._deserializar_tarefa(linha)) is not None
        ]

    def obter_configuracao_tarefa(self, tarefa_id: int) -> dict[str, Any]:
        """Monta o dicionario configuracao.json correspondente ao estado atual da tarefa."""
        tarefa = self.buscar_tarefa_por_id(int(tarefa_id))
        if tarefa is None:
            raise ValueError(f"Tarefa {tarefa_id} não encontrada.")

        admins = [
            str(membro["nome_usuario"])
            for membro in self.repo_usuarios.listar_membros_da_tarefa(
                int(tarefa_id), papel=PAPEL_ADMINISTRADOR
            )
        ]
        atribuicoes_df = self.carregar_atribuicoes_tarefa_df(int(tarefa_id))
        rotuladores_atribuicoes: list[str] = []
        if not atribuicoes_df.empty:
            for nome in atribuicoes_df["labeler"].astype(str).tolist():
                if nome not in rotuladores_atribuicoes:
                    rotuladores_atribuicoes.append(nome)
        if not rotuladores_atribuicoes:
            rotuladores_atribuicoes = [
                f"vaga_{idx}" for idx in range(1, int(tarefa["numero_vagas"]) + 1)
            ]

        return {
            "administradores": admins or ["admin"],
            "rotuladores": rotuladores_atribuicoes,
            "videos_por_rotulador": int(tarefa["videos_por_rotulador"]),
            "percentual_sobreposicao": int(tarefa["percentual_sobreposicao"]),
            "tarefa": str(tarefa["titulo"]),
            "pergunta": str(tarefa["pergunta"]),
            "opcoes_posicao": list(tarefa["opcoes_posicao"]),
            "distancias_rotulos": dict(tarefa["distancias_rotulos"]),
            "codigo_convite": str(tarefa["codigo_convite"]),
        }

    def carregar_videos_tarefa_df(
        self,
        tarefa_id: int,
        tipo_pool: str = POOL_PRINCIPAL,
    ) -> pd.DataFrame:
        """Retorna um DataFrame com os videos principais ou reserva da tarefa."""
        if tipo_pool not in TIPOS_POOL_VALIDOS:
            raise ValueError(f"Tipo de pool inválido: {tipo_pool}")
        linhas = self.banco.consultar_todos(
            """
            SELECT video_id AS id, url, target, video_description, voice_to_text, video_duration
            FROM videos_tarefa
            WHERE tarefa_id = ? AND tipo_pool = ?
            ORDER BY video_tarefa_id ASC;
            """,
            (int(tarefa_id), tipo_pool),
        )
        colunas = list(COLUNAS_VIDEO)
        if not linhas:
            return pd.DataFrame(columns=colunas)
        return pd.DataFrame(linhas, columns=colunas).fillna("")

    def carregar_atribuicoes_tarefa_df(
        self,
        tarefa_id: int,
        rotulador: str | None = None,
    ) -> pd.DataFrame:
        """Retorna as atribuicoes da tarefa ordenadas pela posicao na fila."""
        if rotulador is not None:
            rot_limpo = str(rotulador).strip()
            linhas = self.banco.consultar_todos(
                """
                SELECT assignment_version, assignment_id, labeler, video_id, url,
                       target, video_description, voice_to_text, video_duration
                FROM atribuicoes
                WHERE tarefa_id = ? AND (
                    labeler = ? COLLATE NOCASE
                    OR usuario_id = (SELECT usuario_id FROM usuarios WHERE nome_usuario = ? COLLATE NOCASE OR email = ? COLLATE NOCASE)
                )
                ORDER BY ordem_fila ASC, atribuicao_pk ASC;
                """,
                (int(tarefa_id), rot_limpo, rot_limpo, rot_limpo),
            )
        else:
            linhas = self.banco.consultar_todos(
                """
                SELECT assignment_version, assignment_id, labeler, video_id, url,
                       target, video_description, voice_to_text, video_duration
                FROM atribuicoes
                WHERE tarefa_id = ?
                ORDER BY atribuicao_pk ASC;
                """,
                (int(tarefa_id),),
            )
        colunas = list(COLUNAS_ATRIBUICAO)
        if not linhas:
            return pd.DataFrame(columns=colunas)
        return pd.DataFrame(linhas, columns=colunas).fillna("")

    def salvar_atribuicoes_tarefa_df(
        self,
        tarefa_id: int,
        atribuicoes_df: pd.DataFrame,
    ) -> None:
        """Substitui de forma atomica a tabela de atribuicoes da tarefa pelo DataFrame informado."""
        colunas = list(COLUNAS_ATRIBUICAO)
        quadro = (
            atribuicoes_df.reindex(columns=colunas).fillna("")
            if atribuicoes_df is not None and not atribuicoes_df.empty
            else pd.DataFrame(columns=colunas)
        )
        usuarios_mapa: dict[str, int] = {}
        for u in self.repo_usuarios.listar_usuarios():
            uid = int(u["usuario_id"])
            nu = str(u.get("nome_usuario", "") or "").strip()
            em = str(u.get("email", "") or "").strip()
            if nu:
                usuarios_mapa[nu] = uid
                usuarios_mapa[nu.lower()] = uid
            if em:
                usuarios_mapa[em] = uid
                usuarios_mapa[em.lower()] = uid
        contadores_ordem: dict[str, int] = {}

        with self.banco.conectar() as conexao:
            conexao.execute(
                "DELETE FROM atribuicoes WHERE tarefa_id = ?;",
                (int(tarefa_id),),
            )
            for _, linha in quadro.iterrows():
                rotulador = str(linha["labeler"]).strip()
                ordem = contadores_ordem.get(rotulador, 0)
                contadores_ordem[rotulador] = ordem + 1
                uid_resolvido = usuarios_mapa.get(rotulador) or usuarios_mapa.get(rotulador.lower())
                conexao.execute(
                    """
                    INSERT INTO atribuicoes (
                        tarefa_id, assignment_version, assignment_id, labeler, usuario_id,
                        video_id, url, target, video_description, voice_to_text,
                        video_duration, ordem_fila
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        int(tarefa_id),
                        str(linha["assignment_version"]).strip(),
                        str(linha["assignment_id"]).strip(),
                        rotulador,
                        uid_resolvido,
                        str(linha["video_id"]).strip(),
                        str(linha["url"]).strip(),
                        str(linha["target"]),
                        str(linha.get("video_description", "")),
                        str(linha.get("voice_to_text", "")),
                        str(linha.get("video_duration", "")),
                        ordem,
                    ),
                )
            if not quadro.empty:
                versao_ativa = str(quadro["assignment_version"].iloc[-1]).strip()
                conexao.execute(
                    "UPDATE tarefas SET versao_atribuicao = ? WHERE tarefa_id = ?;",
                    (versao_ativa, int(tarefa_id)),
                )

    def vincular_rotulador_na_tarefa(
        self,
        tarefa_id: int,
        usuario_id: int,
        nome_usuario: str,
        entrou_em: str | None = None,
    ) -> dict[str, Any]:
        """Vincula um usuario a uma vaga da tarefa (ou fila extra) e registra em membros_tarefa."""
        nome_limpo = validar_nome_usuario(nome_usuario)
        config_atual = self.obter_configuracao_tarefa(int(tarefa_id))
        atribuicoes_df = self.carregar_atribuicoes_tarefa_df(int(tarefa_id))
        principais_df = self.carregar_videos_tarefa_df(
            int(tarefa_id), tipo_pool=POOL_PRINCIPAL
        )

        membros_rotuladores = self.repo_usuarios.listar_membros_da_tarefa(
            int(tarefa_id), papel=PAPEL_ROTULADOR
        )
        reivindicados = {
            str(m["nome_usuario"]) for m in membros_rotuladores
        } | {
            str(m["vaga_atribuida"])
            for m in membros_rotuladores
            if str(m.get("vaga_atribuida", "")).strip()
        }
        linhas_anotadas = self.banco.consultar_todos(
            "SELECT DISTINCT labeler FROM anotacoes WHERE tarefa_id = ?;",
            (int(tarefa_id),),
        )
        anotados = {str(linha["labeler"]) for linha in linhas_anotadas}

        _, novas_atribuicoes, vaga_vinculada = vincular_ou_alocar_vaga_rotulador(
            nome_usuario=nome_limpo,
            configuracao=config_atual,
            atribuicoes=atribuicoes_df,
            videos=principais_df,
            usuarios_reivindicados=reivindicados,
            rotuladores_concluidos=anotados,
        )
        self.salvar_atribuicoes_tarefa_df(int(tarefa_id), novas_atribuicoes)
        return self.repo_usuarios.adicionar_membro_tarefa(
            tarefa_id=int(tarefa_id),
            usuario_id=int(usuario_id),
            papel=PAPEL_ROTULADOR,
            vaga_atribuida=vaga_vinculada,
            entrou_em=entrou_em,
        )

    def registrar_anotacao(
        self,
        tarefa_id: int,
        assignment_id: str,
        rotulador: str,
        video_id: str,
        url: str,
        target: str,
        posicao: str,
        tempo_analise_segundos: float,
        video_duration: str = "",
        usuario_id: int | None = None,
        timestamp: str | None = None,
    ) -> dict[str, Any]:
        """Persiste uma anotacao na tabela anotacoes em fuso horario de Brasilia."""
        tarefa = self.buscar_tarefa_por_id(int(tarefa_id))
        if tarefa is None:
            raise ValueError(f"Tarefa {tarefa_id} não encontrada.")

        posicao_limpa = validar_tamanho_texto(
            posicao, nome_campo="posicao", tamanho_maximo=120
        )
        if posicao_limpa not in tarefa["opcoes_posicao"]:
            raise ValueError(
                f"A resposta '{posicao_limpa}' não pertence às opções desta tarefa."
            )

        rotulador_limpo = str(rotulador or "").strip()
        if usuario_id is None:
            usuario = self.repo_usuarios.buscar_por_identificador(rotulador_limpo)
            usuario_id = int(usuario["usuario_id"]) if usuario is not None else None

        instante = str(timestamp or formatar_data_hora_brt())
        tempo_seg = round(max(0.0, float(tempo_analise_segundos or 0.0)), 2)

        # 1. Grava no diário append-only com garantia física de fsync antes do commit no banco
        dados_diario = {
            "tarefa_id": int(tarefa_id),
            "assignment_id": str(assignment_id).strip(),
            "usuario_id": usuario_id,
            "labeler": rotulador_limpo,
            "video_id": str(video_id).strip(),
            "url": str(url).strip(),
            "target": str(target),
            "stance": posicao_limpa,
            "tempo_analise_segundos": tempo_seg,
            "video_duration": str(video_duration or ""),
            "timestamp": instante,
        }
        if hasattr(self.banco, "diario_anotacoes"):
            try:
                self.banco.diario_anotacoes.registrar_pendente(dados_diario)
            except Exception:
                pass

        # 2. Executa a inserção no banco relacional
        falha_sqlite = False
        try:
            self.banco.executar(
                """
                INSERT OR REPLACE INTO anotacoes (
                    tarefa_id, assignment_id, usuario_id, labeler, video_id,
                    url, target, stance, tempo_analise_segundos, video_duration, timestamp
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    int(tarefa_id),
                    str(assignment_id).strip(),
                    usuario_id,
                    rotulador_limpo,
                    str(video_id).strip(),
                    str(url).strip(),
                    str(target),
                    posicao_limpa,
                    tempo_seg,
                    str(video_duration or ""),
                    instante,
                ),
            )
            # 3. Confirma sincronização no diário
            if hasattr(self.banco, "diario_anotacoes"):
                try:
                    self.banco.diario_anotacoes.marcar_sincronizado(int(tarefa_id), str(assignment_id).strip())
                except Exception:
                    pass
        except Exception:
            falha_sqlite = True

        salva = self.banco.consultar_um(
            """
            SELECT * FROM anotacoes
            WHERE tarefa_id = ? AND assignment_id = ?;
            """,
            (int(tarefa_id), str(assignment_id).strip()),
        )
        if salva is not None:
            d = dict(salva)
        elif not falha_sqlite:
            raise RuntimeError("Falha ao persistir anotação.")
        else:
            # Fallback seguro vindo do diário de persistência: o rótulo jamais é perdido
            d = dict(dados_diario)
            d["salvo_em_diario_reserva"] = True

        d["posicao"] = d.get("stance", "")
        return d

    def carregar_anotacoes_tarefa_df(
        self,
        tarefa_id: int,
        rotulador: str | None = None,
    ) -> pd.DataFrame:
        """Retorna as anotacoes concluidas da tarefa no formato de resultados_anotacao.csv."""
        if rotulador is not None:
            rot_limpo = str(rotulador).strip()
            linhas = self.banco.consultar_todos(
                """
                SELECT timestamp, labeler, video_id, url, target, stance,
                       tempo_analise_segundos, video_duration, assignment_id
                FROM anotacoes
                WHERE tarefa_id = ? AND (
                    labeler = ? COLLATE NOCASE
                    OR usuario_id = (SELECT usuario_id FROM usuarios WHERE nome_usuario = ? COLLATE NOCASE OR email = ? COLLATE NOCASE)
                )
                ORDER BY anotacao_id ASC;
                """,
                (int(tarefa_id), rot_limpo, rot_limpo, rot_limpo),
            )
        else:
            linhas = self.banco.consultar_todos(
                """
                SELECT timestamp, labeler, video_id, url, target, stance,
                       tempo_analise_segundos, video_duration, assignment_id
                FROM anotacoes
                WHERE tarefa_id = ?
                ORDER BY anotacao_id ASC;
                """,
                (int(tarefa_id),),
            )
        colunas = list(COLUNAS_RESULTADO)
        if not linhas:
            return pd.DataFrame(columns=colunas)
        return pd.DataFrame(linhas, columns=colunas).fillna("")

    def registrar_erro_video(
        self,
        tarefa_id: int,
        video_id: str,
        url: str,
        rotulador: str,
        assignment_id: str,
        replacement_video_id: str = "",
        replacement_url: str = "",
        replacement_assignment_id: str = "",
        replacement_status: str = "",
        usuario_id: int | None = None,
        timestamp: str | None = None,
    ) -> dict[str, Any]:
        """Persiste um erro de video e sua substituicao por reserva em erros_videos."""
        rotulador_limpo = str(rotulador or "").strip()
        if usuario_id is None:
            usuario = self.repo_usuarios.buscar_por_identificador(rotulador_limpo)
            usuario_id = int(usuario["usuario_id"]) if usuario is not None else None
        instante = str(timestamp or formatar_data_hora_brt())

        erro_id = self.banco.executar(
            """
            INSERT INTO erros_videos (
                tarefa_id, timestamp, video_id, url, usuario_id, labeler,
                assignment_id, replacement_video_id, replacement_url,
                replacement_assignment_id, replacement_status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                int(tarefa_id),
                instante,
                str(video_id).strip(),
                str(url).strip(),
                usuario_id,
                rotulador_limpo,
                str(assignment_id).strip(),
                str(replacement_video_id or ""),
                str(replacement_url or ""),
                str(replacement_assignment_id or ""),
                str(replacement_status or ""),
            ),
        )
        salvo = self.banco.consultar_um(
            "SELECT * FROM erros_videos WHERE erro_id = ?;",
            (erro_id,),
        )
        if salvo is None:
            raise RuntimeError("Falha ao persistir registro de erro de vídeo.")
        return salvo

    def carregar_erros_videos_tarefa_df(self, tarefa_id: int) -> pd.DataFrame:
        """Retorna os erros de video da tarefa no formato de erros_videos.csv."""
        linhas = self.banco.consultar_todos(
            """
            SELECT timestamp, video_id, url, labeler, assignment_id,
                   replacement_video_id, replacement_url,
                   replacement_assignment_id, replacement_status
            FROM erros_videos
            WHERE tarefa_id = ?
            ORDER BY erro_id ASC;
            """,
            (int(tarefa_id),),
        )
        colunas = list(COLUNAS_ERRO)
        if not linhas:
            return pd.DataFrame(columns=colunas)
        return pd.DataFrame(linhas, columns=colunas).fillna("")

    def salvar_erros_videos_tarefa_df(
        self,
        tarefa_id: int,
        erros_df: pd.DataFrame,
    ) -> None:
        """Substitui de forma atomica os registros de erros_videos da tarefa pelo DataFrame."""
        colunas = list(COLUNAS_ERRO)
        quadro = (
            erros_df.reindex(columns=colunas).fillna("")
            if erros_df is not None and not erros_df.empty
            else pd.DataFrame(columns=colunas)
        )
        usuarios_mapa = {
            str(u["nome_usuario"]): int(u["usuario_id"])
            for u in self.repo_usuarios.listar_usuarios()
        }
        with self.banco.conectar() as conexao:
            conexao.execute(
                "DELETE FROM erros_videos WHERE tarefa_id = ?;",
                (int(tarefa_id),),
            )
            for _, linha in quadro.iterrows():
                rotulador = str(linha["labeler"]).strip()
                conexao.execute(
                    """
                    INSERT INTO erros_videos (
                        tarefa_id, timestamp, video_id, url, usuario_id, labeler,
                        assignment_id, replacement_video_id, replacement_url,
                        replacement_assignment_id, replacement_status
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        int(tarefa_id),
                        str(linha["timestamp"]),
                        str(linha["video_id"]).strip(),
                        str(linha["url"]).strip(),
                        usuarios_mapa.get(rotulador),
                        rotulador,
                        str(linha["assignment_id"]).strip(),
                        str(linha.get("replacement_video_id", "")),
                        str(linha.get("replacement_url", "")),
                        str(linha.get("replacement_assignment_id", "")),
                        str(linha.get("replacement_status", "")),
                    ),
                )

    def registrar_log_acesso(
        self,
        usuario: str,
        acao: str,
        tarefa_id: int | None = None,
        tempo_desde_login_segundos: float | None = None,
        usuario_id: int | None = None,
        timestamp: str | None = None,
    ) -> dict[str, Any]:
        """Registra um evento de auditoria na tabela logs_acesso em fuso BRT."""
        usuario_limpo = validar_tamanho_texto(
            usuario, nome_campo="usuario", tamanho_maximo=64
        )
        acao_limpa = validar_tamanho_texto(
            acao, nome_campo="acao", tamanho_maximo=64
        )
        if usuario_id is None:
            conta = self.repo_usuarios.buscar_por_nome_usuario(usuario_limpo)
            usuario_id = int(conta["usuario_id"]) if conta is not None else None
        instante = str(timestamp or formatar_data_hora_brt())
        tempo_valor = (
            round(max(0.0, float(tempo_desde_login_segundos)), 2)
            if tempo_desde_login_segundos is not None and tempo_desde_login_segundos != ""
            else None
        )
        log_id = self.banco.executar(
            """
            INSERT INTO logs_acesso (
                tarefa_id, usuario_id, usuario, acao, tempo_desde_login_segundos, timestamp
            )
            VALUES (?, ?, ?, ?, ?, ?);
            """,
            (
                int(tarefa_id) if tarefa_id is not None else None,
                usuario_id,
                usuario_limpo,
                acao_limpa,
                tempo_valor,
                instante,
            ),
        )
        salvo = self.banco.consultar_um(
            "SELECT * FROM logs_acesso WHERE log_id = ?;",
            (log_id,),
        )
        if salvo is None:
            raise RuntimeError("Falha ao registrar log de acesso.")
        return salvo

    def carregar_logs_acesso_df(self, tarefa_id: int | None = None) -> pd.DataFrame:
        """Retorna os logs de acesso filtrados pela tarefa ou globais no formato acessos_log.csv."""
        if tarefa_id is not None:
            linhas = self.banco.consultar_todos(
                """
                SELECT timestamp, usuario, acao, tempo_desde_login_segundos
                FROM logs_acesso
                WHERE tarefa_id = ? OR tarefa_id IS NULL
                ORDER BY log_id ASC;
                """,
                (int(tarefa_id),),
            )
        else:
            linhas = self.banco.consultar_todos(
                """
                SELECT timestamp, usuario, acao, tempo_desde_login_segundos
                FROM logs_acesso
                ORDER BY log_id ASC;
                """
            )
        colunas = list(COLUNAS_LOG)
        if not linhas:
            return pd.DataFrame(columns=colunas)
        quadro = pd.DataFrame(linhas, columns=colunas)
        quadro["tempo_desde_login_segundos"] = quadro[
            "tempo_desde_login_segundos"
        ].where(quadro["tempo_desde_login_segundos"].notna(), "")
        return quadro.fillna("")

    def carregar_logs_acesso_tarefa_df(self, tarefa_id: int) -> pd.DataFrame:
        """Alias para carregar_logs_acesso_df com escopo explicito na tarefa."""
        return self.carregar_logs_acesso_df(tarefa_id=int(tarefa_id))

    def excluir_tarefa(self, tarefa_id: int, usuario_administrador_id: int) -> bool:
        """Exclui completamente uma tarefa e todos os seus registros associados se o usuario for administrador."""
        tarefa = self.buscar_tarefa_por_id(int(tarefa_id))
        if tarefa is None:
            raise ValueError(f"Tarefa {tarefa_id} não encontrada.")

        criador_id = int(tarefa.get("criado_por_usuario_id") or 0)
        eh_admin = criador_id == int(usuario_administrador_id)
        if not eh_admin:
            membros_admin = self.repo_usuarios.listar_membros_da_tarefa(
                int(tarefa_id), papel=PAPEL_ADMINISTRADOR
            )
            eh_admin = any(
                int(m["usuario_id"]) == int(usuario_administrador_id) for m in membros_admin
            )

        if not eh_admin:
            raise PermissionError("Apenas o administrador da tarefa pode excluí-la.")

        with self.banco.conectar() as conexao:
            conexao.execute("DELETE FROM anotacoes WHERE tarefa_id = ?;", (int(tarefa_id),))
            conexao.execute("DELETE FROM erros_videos WHERE tarefa_id = ?;", (int(tarefa_id),))
            conexao.execute("DELETE FROM atribuicoes WHERE tarefa_id = ?;", (int(tarefa_id),))
            conexao.execute("DELETE FROM videos_tarefa WHERE tarefa_id = ?;", (int(tarefa_id),))
            conexao.execute("DELETE FROM membros_tarefa WHERE tarefa_id = ?;", (int(tarefa_id),))
            conexao.execute("DELETE FROM logs_acesso WHERE tarefa_id = ?;", (int(tarefa_id),))
            conexao.execute("DELETE FROM tarefas WHERE tarefa_id = ?;", (int(tarefa_id),))

        return True

    def exportar_arquivos_tarefa(
        self,
        tarefa_id: int,
        diretorio_destino: Path | str | None = None,
    ) -> CaminhosDados:
        """Exporta sob demanda todos os arquivos CSV e JSON da tarefa para download no Console Admin."""
        caminhos = resolver_caminhos_dados(diretorio_destino)
        caminhos.diretorio_base.mkdir(parents=True, exist_ok=True)

        configuracao = self.obter_configuracao_tarefa(int(tarefa_id))
        salvar_configuracao(configuracao, caminhos.arquivo_configuracao)

        videos_df = self.carregar_videos_tarefa_df(
            int(tarefa_id), tipo_pool=POOL_PRINCIPAL
        )
        reservas_df = self.carregar_videos_tarefa_df(
            int(tarefa_id), tipo_pool=POOL_RESERVA
        )
        atribuicoes_df = self.carregar_atribuicoes_tarefa_df(int(tarefa_id))
        resultados_df = self.carregar_anotacoes_tarefa_df(int(tarefa_id))
        erros_df = self.carregar_erros_videos_tarefa_df(int(tarefa_id))
        logs_df = self.carregar_logs_acesso_df(int(tarefa_id))

        videos_df.to_csv(caminhos.arquivo_videos, index=False)
        reservas_df.to_csv(caminhos.arquivo_videos_reserva, index=False)
        atribuicoes_df.to_csv(caminhos.arquivo_atribuicoes, index=False)
        resultados_df.to_csv(caminhos.arquivo_resultados, index=False)
        erros_df.to_csv(caminhos.arquivo_erros, index=False)
        logs_df.to_csv(caminhos.arquivo_log, index=False)

        relatorio_concordancia = calcular_concordancia(
            resultados=resultados_df,
            configuracao=configuracao,
        )
        caminhos.arquivo_concordancia.write_text(
            json.dumps(relatorio_concordancia, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return caminhos
