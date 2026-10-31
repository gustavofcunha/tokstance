"""Servico de autenticacao, cadastro de usuarios, sessao unica e Hub Inicial de tarefas."""

from typing import Any

from tokstance.backend.domain.models import PAPEL_ADMINISTRADOR, PAPEL_ROTULADOR
from tokstance.backend.repositories.database import BancoDadosSQLite
from tokstance.backend.repositories.study_repo import RepositorioEstudo
from tokstance.backend.repositories.user_repo import RepositorioUsuarios
from tokstance.backend.security.password import gerar_hash_senha, verificar_senha
from tokstance.backend.security.rate_limit import (
    GerenciadorSessoesAtivas,
    LimitadorTentativas,
)
from tokstance.backend.security.validators import (
    validar_codigo_convite,
    validar_nome_usuario,
)
from tokstance.config import SENHA_ADMIN_PADRAO, USUARIO_ADMIN_PADRAO


class ServicoAutenticacao:
    """Orquestra cadastro, login com bloqueio de forca bruta, sessao unica e Hub Inicial."""

    def __init__(
        self,
        banco: BancoDadosSQLite | None = None,
        repo_usuarios: RepositorioUsuarios | None = None,
        repo_estudo: RepositorioEstudo | None = None,
        limitador_tentativas: LimitadorTentativas | None = None,
        gerenciador_sessoes: GerenciadorSessoesAtivas | None = None,
        rodadas_bcrypt: int = 12,
    ) -> None:
        self.banco = banco or BancoDadosSQLite()
        self.repo_usuarios = repo_usuarios or RepositorioUsuarios(self.banco)
        self.repo_estudo = repo_estudo or RepositorioEstudo(
            self.banco, self.repo_usuarios
        )
        self.limitador_tentativas = limitador_tentativas or LimitadorTentativas()
        self.gerenciador_sessoes = gerenciador_sessoes or GerenciadorSessoesAtivas()
        self.rodadas_bcrypt = int(rodadas_bcrypt)

    def garantir_conta_admin_padrao(self) -> dict[str, Any]:
        """Garante que a conta de administrador padrao exista no banco SQLite."""
        existente = self.repo_usuarios.buscar_por_nome_usuario(USUARIO_ADMIN_PADRAO)
        if existente is not None:
            return existente
        senha_hash = gerar_hash_senha(SENHA_ADMIN_PADRAO, rodadas=self.rodadas_bcrypt)
        return self.repo_usuarios.criar_usuario(USUARIO_ADMIN_PADRAO, senha_hash)

    def cadastrar_usuario(
        self,
        nome_usuario: str,
        senha: str,
        codigo_convite: str | None = None,
    ) -> dict[str, Any]:
        """Cria uma nova conta de usuario e opcionalmente o vincula a uma tarefa via convite."""
        nome_limpo = validar_nome_usuario(nome_usuario)
        if self.repo_usuarios.buscar_por_nome_usuario(nome_limpo) is not None:
            raise ValueError(f"O nome de usuário '{nome_limpo}' já está cadastrado.")

        tarefa_alvo: dict[str, Any] | None = None
        if codigo_convite is not None and str(codigo_convite).strip():
            convite_limpo = validar_codigo_convite(codigo_convite)
            tarefa_alvo = self.repo_estudo.buscar_tarefa_por_codigo_convite(
                convite_limpo
            )
            if tarefa_alvo is None:
                raise ValueError("Código de convite não encontrado.")

        senha_hash = gerar_hash_senha(senha, rodadas=self.rodadas_bcrypt)
        usuario = self.repo_usuarios.criar_usuario(nome_limpo, senha_hash)
        self.repo_estudo.registrar_log_acesso(
            usuario=nome_limpo,
            acao="cadastro",
            usuario_id=int(usuario["usuario_id"]),
        )

        vinculo_rotulador: dict[str, Any] | None = None
        if tarefa_alvo is not None:
            vinculo_rotulador = self.repo_estudo.vincular_rotulador_na_tarefa(
                tarefa_id=int(tarefa_alvo["tarefa_id"]),
                usuario_id=int(usuario["usuario_id"]),
                nome_usuario=nome_limpo,
            )

        return {
            "usuario_id": int(usuario["usuario_id"]),
            "nome_usuario": str(usuario["nome_usuario"]),
            "criado_em": str(usuario["criado_em"]),
            "vinculo_inicial": vinculo_rotulador,
        }

    def autenticar_usuario(
        self,
        nome_usuario: str,
        senha: str,
        exigir_sessao_unica: bool = True,
    ) -> dict[str, Any]:
        """Autentica o usuario verificando bloqueio temporario, senha bcrypt e sessao ativa."""
        chave_bruta = str(nome_usuario or "").strip()
        if not chave_bruta:
            raise ValueError("Informe o nome de usuário.")

        if self.limitador_tentativas.esta_bloqueado(chave_bruta):
            restante = self.limitador_tentativas.segundos_restantes_bloqueio(
                chave_bruta
            )
            raise PermissionError(
                f"Muitas tentativas falhas. Aguarde {restante:.0f}s antes de tentar novamente."
            )

        try:
            nome_limpo = validar_nome_usuario(chave_bruta)
        except ValueError as exc:
            self.limitador_tentativas.registrar_falha(chave_bruta)
            raise ValueError("Credenciais inválidas.") from exc

        conta = self.repo_usuarios.buscar_por_nome_usuario(nome_limpo)
        if conta is None or not verificar_senha(
            str(senha or ""), str(conta["senha_hash"])
        ):
            bloqueou = self.limitador_tentativas.registrar_falha(nome_limpo)
            if bloqueou:
                restante = self.limitador_tentativas.segundos_restantes_bloqueio(
                    nome_limpo
                )
                raise PermissionError(
                    f"Muitas tentativas falhas. Aguarde {restante:.0f}s antes de tentar novamente."
                )
            raise ValueError("Credenciais inválidas.")

        if exigir_sessao_unica and not self.gerenciador_sessoes.reivindicar_sessao(
            nome_limpo
        ):
            raise RuntimeError(
                f"O usuário '{nome_limpo}' já possui uma sessão ativa em andamento."
            )

        self.limitador_tentativas.registrar_sucesso(nome_limpo)
        self.repo_estudo.registrar_log_acesso(
            usuario=nome_limpo,
            acao="login",
            usuario_id=int(conta["usuario_id"]),
            tempo_desde_login_segundos=0.0,
        )
        hub = self.obter_painel_usuario(int(conta["usuario_id"]))
        return {
            "usuario_id": int(conta["usuario_id"]),
            "nome_usuario": str(conta["nome_usuario"]),
            "tarefas_administrador": hub["tarefas_administrador"],
            "tarefas_rotulador": hub["tarefas_rotulador"],
        }

    def encerrar_sessao(
        self,
        nome_usuario: str,
        acao: str = "logout",
        tarefa_id: int | None = None,
        tempo_desde_login_segundos: float | None = None,
    ) -> None:
        """Libera a sessao ativa do usuario e registra o evento de saida em logs_acesso."""
        if not isinstance(nome_usuario, str) or not nome_usuario.strip():
            return
        nome_limpo = nome_usuario.strip()
        self.gerenciador_sessoes.liberar_sessao(nome_limpo)
        self.repo_estudo.registrar_log_acesso(
            usuario=nome_limpo,
            acao=acao,
            tarefa_id=tarefa_id,
            tempo_desde_login_segundos=tempo_desde_login_segundos,
        )

    def entrar_na_tarefa_por_convite(
        self,
        usuario_id: int,
        codigo_convite: str,
    ) -> dict[str, Any]:
        """Inscreve o usuario como rotulador na tarefa correspondente ao codigo de convite."""
        usuario = self.repo_usuarios.buscar_por_id(int(usuario_id))
        if usuario is None:
            raise ValueError("Usuário não encontrado.")

        convite_limpo = validar_codigo_convite(codigo_convite)
        tarefa = self.repo_estudo.buscar_tarefa_por_codigo_convite(convite_limpo)
        if tarefa is None:
            raise ValueError(
                f"Nenhuma tarefa encontrada para o código de convite '{convite_limpo}'."
            )

        vinculo = self.repo_estudo.vincular_rotulador_na_tarefa(
            tarefa_id=int(tarefa["tarefa_id"]),
            usuario_id=int(usuario["usuario_id"]),
            nome_usuario=str(usuario["nome_usuario"]),
        )
        self.repo_estudo.registrar_log_acesso(
            usuario=str(usuario["nome_usuario"]),
            acao="entrar_tarefa_convite",
            tarefa_id=int(tarefa["tarefa_id"]),
            usuario_id=int(usuario["usuario_id"]),
        )
        return {
            "tarefa_id": int(tarefa["tarefa_id"]),
            "titulo": str(tarefa["titulo"]),
            "pergunta": str(tarefa["pergunta"]),
            "codigo_convite": str(tarefa["codigo_convite"]),
            "papel": PAPEL_ROTULADOR,
            "vaga_atribuida": str(vinculo["vaga_atribuida"]),
        }

    def obter_painel_usuario(self, usuario_id: int) -> dict[str, Any]:
        """Retorna as tarefas administradas e as tarefas para rotular (com progresso) do usuario."""
        usuario = self.repo_usuarios.buscar_por_id(int(usuario_id))
        if usuario is None:
            raise ValueError("Usuário não encontrado.")

        nome_usuario = str(usuario["nome_usuario"])
        tarefas_admin = self.repo_usuarios.listar_tarefas_do_usuario(
            int(usuario_id), papel=PAPEL_ADMINISTRADOR
        )
        tarefas_rot = self.repo_usuarios.listar_tarefas_do_usuario(
            int(usuario_id), papel=PAPEL_ROTULADOR
        )

        resumo_admin: list[dict[str, Any]] = []
        for item in tarefas_admin:
            tid = int(item["tarefa_id"])
            atrib_df = self.repo_estudo.carregar_atribuicoes_tarefa_df(tid)
            anot_df = self.repo_estudo.carregar_anotacoes_tarefa_df(tid)
            resumo_admin.append(
                {
                    **item,
                    "total_atribuicoes": len(atrib_df),
                    "total_anotacoes": len(anot_df),
                }
            )

        resumo_rotulador: list[dict[str, Any]] = []
        for item in tarefas_rot:
            tid = int(item["tarefa_id"])
            fila_df = self.repo_estudo.carregar_atribuicoes_tarefa_df(
                tid, rotulador=nome_usuario
            )
            anot_df = self.repo_estudo.carregar_anotacoes_tarefa_df(
                tid, rotulador=nome_usuario
            )
            erros_df = self.repo_estudo.carregar_erros_videos_tarefa_df(tid)
            ids_anotados = (
                set(anot_df["assignment_id"].astype(str))
                if not anot_df.empty
                else set()
            )
            ids_erros_sem_reserva: set[str] = set()
            if not erros_df.empty:
                erros_rot = erros_df[
                    erros_df["labeler"].astype(str).eq(nome_usuario)
                    & erros_df["replacement_assignment_id"].astype(str).str.strip().eq("")
                ]
                ids_erros_sem_reserva = set(erros_rot["assignment_id"].astype(str))

            ids_processados = ids_anotados | ids_erros_sem_reserva
            total_fila = len(fila_df)
            concluidos = (
                int(fila_df["assignment_id"].astype(str).isin(ids_processados).sum())
                if not fila_df.empty
                else 0
            )
            resumo_rotulador.append(
                {
                    **item,
                    "videos_concluidos": concluidos,
                    "total_videos_fila": total_fila,
                    "pendentes": max(0, total_fila - concluidos),
                }
            )

        return {
            "usuario_id": int(usuario["usuario_id"]),
            "nome_usuario": nome_usuario,
            "tarefas_administrador": resumo_admin,
            "tarefas_rotulador": resumo_rotulador,
        }
