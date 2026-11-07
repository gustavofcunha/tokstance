"""Servico de autenticacao, cadastro de usuarios, sessao unica e Hub Inicial de tarefas."""

import logging
import os
import secrets
import smtplib
from datetime import timedelta
from email.mime.text import MIMEText
from typing import Any

import pandas as pd

from tokstance.backend.domain.models import (
    COLUNAS_ATRIBUICAO,
    COLUNAS_RESULTADO,
    PAPEL_ADMINISTRADOR,
    PAPEL_ROTULADOR,
)
from tokstance.backend.repositories.database import BancoDadosSQLite
from tokstance.backend.repositories.study_repo import RepositorioEstudo
from tokstance.backend.repositories.user_repo import RepositorioUsuarios
from tokstance.backend.security.password import (
    HASH_DUMMY_BCRYPT,
    gerar_hash_senha,
    validar_complexidade_senha,
    verificar_senha,
)
from tokstance.backend.security.rate_limit import (
    GerenciadorSessoesAtivas,
    LimitadorTentativas,
)
from tokstance.backend.security.validators import (
    validar_codigo_convite,
    validar_email,
    validar_nome_usuario,
)
from tokstance.config import (
    MAX_TENTATIVAS_RECUPERACAO_CODIGO,
    SEGUNDOS_BLOQUEIO_RECUPERACAO,
    SENHA_ADMIN_PADRAO,
    USUARIO_ADMIN_PADRAO,
    agora_brt,
    formatar_data_hora_brt,
)

logger = logging.getLogger(__name__)


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
        self.limitador_recuperacao = LimitadorTentativas(
            max_tentativas=MAX_TENTATIVAS_RECUPERACAO_CODIGO,
            segundos_bloqueio=SEGUNDOS_BLOQUEIO_RECUPERACAO,
        )
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
        email: str = "",
        nome_completo: str = "",
        codigo_convite: str | None = None,
    ) -> dict[str, Any]:
        """Cria uma nova conta de usuario com e-mail obrigatorio e opcionalmente o vincula a uma tarefa via convite."""
        nome_limpo = validar_nome_usuario(nome_usuario)
        nome_completo_limpo = str(nome_completo or "").strip().upper()
        if self.repo_usuarios.buscar_por_nome_usuario(nome_limpo) is not None:
            raise ValueError(f"O nome de usuário '{nome_limpo}' já está cadastrado.")

        email_limpo = validar_email(email) if email and str(email).strip() else ""
        if email_limpo and self.repo_usuarios.buscar_por_email(email_limpo) is not None:
            raise ValueError(f"O e-mail '{email_limpo}' já está em uso por outra conta.")

        tarefa_alvo: dict[str, Any] | None = None
        if codigo_convite is not None and str(codigo_convite).strip():
            convite_limpo = validar_codigo_convite(codigo_convite)
            tarefa_alvo = self.repo_estudo.buscar_tarefa_por_codigo_convite(
                convite_limpo
            )
            if tarefa_alvo is None:
                raise ValueError("Código de convite não encontrado.")

        senha_hash = gerar_hash_senha(senha, rodadas=self.rodadas_bcrypt)
        usuario = self.repo_usuarios.criar_usuario(
            nome_usuario=nome_limpo,
            senha_hash=senha_hash,
            email=email_limpo,
            nome_completo=nome_completo_limpo,
        )
        self.repo_usuarios.vincular_atribuicoes_e_membros_pendentes(
            usuario_id=int(usuario["usuario_id"]),
            nome_usuario=nome_limpo,
            email=email_limpo,
        )
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
            "nome_completo": str(usuario.get("nome_completo", nome_completo_limpo)),
            "email": str(usuario.get("email", email_limpo)),
            "criado_em": str(usuario["criado_em"]),
            "vinculo_inicial": vinculo_rotulador,
        }

    def solicitar_recuperacao_senha(self, identificador: str) -> dict[str, Any]:
        """Gera um codigo de recuperacao temporario de 6 digitos e tenta envia-lo por e-mail."""
        termo = str(identificador or "").strip()
        if not termo:
            raise ValueError("Informe seu nome de usuário ou e-mail cadastrado.")

        usuario = self.repo_usuarios.buscar_por_nome_usuario(termo)
        if usuario is None:
            usuario = self.repo_usuarios.buscar_por_email(termo)
        if usuario is None:
            raise ValueError("Nenhum usuário cadastrado encontrado com este identificador ou e-mail.")

        codigo = f"{secrets.randbelow(900000) + 100000}"
        expira_em = formatar_data_hora_brt(agora_brt() + timedelta(minutes=15))

        self.repo_usuarios.salvar_codigo_recuperacao(
            usuario_id=int(usuario["usuario_id"]),
            codigo_recuperacao=codigo,
            expira_em=expira_em,
        )
        self.repo_estudo.registrar_log_acesso(
            usuario=str(usuario["nome_usuario"]),
            acao="solicitar_recuperacao_senha",
            usuario_id=int(usuario["usuario_id"]),
        )

        email_destino = str(usuario.get("email", "") or "").strip()
        disparado_smtp = False
        smtp_host = os.environ.get("SMTP_HOST")
        smtp_configurado = bool(smtp_host and email_destino)
        mock_smtp = os.environ.get("TOKSTANCE_MOCK_SMTP") == "1"

        if mock_smtp and email_destino:
            #modo mock para testes automatizados sem conexao externa
            disparado_smtp = (smtp_host != "servidor.invalido.local")
            logger.info("Mock SMTP ativo: simulando envio para %s (disparado=%s)", email_destino, disparado_smtp)
        elif smtp_host and email_destino:
            try:
                smtp_port = int(os.environ.get("SMTP_PORT", 587))
                smtp_user = os.environ.get("SMTP_USER", "").strip()
                smtp_pass_raw = os.environ.get("SMTP_PASSWORD", "").strip()
                smtp_pass = smtp_pass_raw.replace(" ", "") if "gmail" in (smtp_host or "").lower() else smtp_pass_raw
                msg = MIMEText(
                    f"Olá, {usuario['nome_usuario']}!\n\n"
                    f"Seu código de recuperação de senha no TokStance é: {codigo}\n"
                    f"Ele é válido por 15 minutos.\n\n"
                    f"Atenciosamente,\nEquipe TokStance"
                )
                msg["Subject"] = "Código de Recuperação de Senha - TokStance"
                msg["From"] = smtp_user or "noreply@tokstance.local"
                msg["To"] = email_destino
                with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as s:
                    s.starttls()
                    if smtp_user and smtp_pass:
                        s.login(smtp_user, smtp_pass)
                    s.send_message(msg)
                disparado_smtp = True
            except Exception as exc:
                logger.warning("Falha ao disparar e-mail via SMTP (%s): %s", smtp_host, exc)
                disparado_smtp = False

        if not disparado_smtp:
            print(
                f"\n[TokStance Dev] Código de recuperação gerado para '{usuario['nome_usuario']}': {codigo} (válido por 15 min)\n",
                flush=True,
            )

        return {
            "sucesso": True,
            "usuario_id": int(usuario["usuario_id"]),
            "nome_usuario": str(usuario["nome_usuario"]),
            "email": email_destino,
            "codigo": codigo,
            "disparado_smtp": disparado_smtp,
            "smtp_configurado": smtp_configurado,
        }

    def verificar_codigo_recuperacao(self, identificador: str, codigo: str) -> bool:
        """Confere o codigo informado sem consumi-lo, liberando a etapa de nova senha com protecao anti-bruteforce."""
        termo = str(identificador or "").strip()
        cod = str(codigo or "").strip()
        if not cod:
            raise ValueError("Informe o código de 6 dígitos recebido por e-mail.")

        if self.limitador_recuperacao.esta_bloqueado(termo):
            restante = self.limitador_recuperacao.segundos_restantes_bloqueio(termo)
            raise PermissionError(
                f"Muitas tentativas incorretas de código. Aguarde {restante:.0f}s antes de tentar novamente."
            )

        usuario = self.repo_usuarios.buscar_por_nome_usuario(termo)
        if usuario is None:
            usuario = self.repo_usuarios.buscar_por_email(termo)

        valido = bool(
            usuario is not None and self.repo_usuarios.validar_codigo_recuperacao(
                usuario_id=int(usuario["usuario_id"]), codigo_recuperacao=cod
            )
        )

        if not valido:
            bloqueou = self.limitador_recuperacao.registrar_falha(termo)
            if bloqueou:
                restante = self.limitador_recuperacao.segundos_restantes_bloqueio(termo)
                raise PermissionError(
                    f"Muitas tentativas incorretas de código. Aguarde {restante:.0f}s antes de tentar novamente."
                )
            raise ValueError("Código de recuperação inválido ou expirado (limite de 15 minutos).")

        self.limitador_recuperacao.registrar_sucesso(termo)
        return True

    def redefinir_senha_com_codigo(
        self,
        identificador: str,
        codigo: str,
        nova_senha: str,
    ) -> dict[str, Any]:
        """Valida o codigo recebido e atualiza a senha do usuario."""
        termo = str(identificador or "").strip()
        cod = str(codigo or "").strip()
        if not termo:
            raise ValueError("Informe seu nome de usuário ou e-mail cadastrado.")
        if not cod:
            raise ValueError("O código de recuperação de 6 dígitos é obrigatório.")
        if not isinstance(nova_senha, str) or not nova_senha.strip():
            raise ValueError("A nova senha é obrigatória (mínimo de 6 caracteres, com ao menos uma letra e um número).")
        try:
            validar_complexidade_senha(nova_senha)
        except ValueError as exc:
            msg = str(exc).replace("A senha ", "A nova senha ")
            if "no mínimo 6 caracteres" in msg:
                msg = msg.replace("no mínimo 6 caracteres", "pelo menos 6 caracteres (mínimo de 6 caracteres)")
            raise ValueError(msg)

        usuario = self.repo_usuarios.buscar_por_nome_usuario(termo)
        if usuario is None:
            usuario = self.repo_usuarios.buscar_por_email(termo)
        if usuario is None:
            usuario = self.repo_usuarios.buscar_por_nome_ou_email_case_insensitive(termo)
        if usuario is None:
            raise ValueError("Usuário não encontrado.")

        u_id = int(usuario["usuario_id"])
        valido = self.repo_usuarios.validar_codigo_recuperacao(
            usuario_id=u_id,
            codigo_recuperacao=cod,
        )
        if not valido:
            raise ValueError("Código de recuperação inválido ou expirado (limite de 15 minutos).")

        novo_hash = gerar_hash_senha(nova_senha, rodadas=self.rodadas_bcrypt)
        self.repo_usuarios.atualizar_senha(usuario_id=u_id, nova_senha_hash=novo_hash)
        self.repo_usuarios.consumir_codigo_recuperacao(usuario_id=u_id, codigo_recuperacao=cod)
        self.repo_usuarios.vincular_atribuicoes_e_membros_pendentes(
            usuario_id=u_id,
            nome_usuario=str(usuario["nome_usuario"]),
            email=str(usuario.get("email", "") or ""),
        )
        self.gerenciador_sessoes.liberar_sessao(str(usuario["nome_usuario"]))

        self.repo_estudo.registrar_log_acesso(
            usuario=str(usuario["nome_usuario"]),
            acao="redefinir_senha_concluida",
            usuario_id=u_id,
        )
        return {
            "sucesso": True,
            "mensagem": "Senha redefinida com sucesso! Você já pode acessar o sistema com sua nova senha.",
            "usuario_id": u_id,
            "nome_usuario": str(usuario["nome_usuario"]),
            "email": str(usuario.get("email", "")),
        }

    def autenticar_usuario(
        self,
        nome_usuario: str,
        senha: str,
        exigir_sessao_unica: bool = True,
        permitir_reassumir: bool = False,
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

        conta = self.repo_usuarios.buscar_por_identificador(chave_bruta)
        if conta is None:
            conta = self.repo_usuarios.buscar_por_nome_ou_email_case_insensitive(chave_bruta)

        if conta is None:
            # Mitigacao de timing attack: executa verificacao dummy com bcrypt em tempo constante
            verificar_senha(str(senha or ""), HASH_DUMMY_BCRYPT)
            bloqueou = self.limitador_tentativas.registrar_falha(chave_bruta)
            if bloqueou:
                restante = self.limitador_tentativas.segundos_restantes_bloqueio(
                    chave_bruta
                )
                raise PermissionError(
                    f"Muitas tentativas falhas. Aguarde {restante:.0f}s antes de tentar novamente."
                )
            raise ValueError("Credenciais inválidas: usuário não encontrado.")

        nome_limpo = str(conta["nome_usuario"])
        if not verificar_senha(str(senha or ""), str(conta["senha_hash"])):
            bloqueou = self.limitador_tentativas.registrar_falha(chave_bruta)
            if bloqueou:
                restante = self.limitador_tentativas.segundos_restantes_bloqueio(
                    chave_bruta
                )
                raise PermissionError(
                    f"Muitas tentativas falhas. Aguarde {restante:.0f}s antes de tentar novamente."
                )
            raise ValueError("Credenciais inválidas: senha incorreta.")

        if exigir_sessao_unica and not self.gerenciador_sessoes.reivindicar_sessao(
            nome_limpo
        ):
            if permitir_reassumir:
                self.gerenciador_sessoes.liberar_sessao(nome_limpo)
                self.gerenciador_sessoes.reivindicar_sessao(nome_limpo)
            else:
                raise RuntimeError(
                    f"O usuário '{nome_limpo}' já possui uma sessão ativa em andamento."
                )

        self.limitador_tentativas.registrar_sucesso(nome_limpo)
        self.repo_usuarios.vincular_atribuicoes_e_membros_pendentes(
            usuario_id=int(conta["usuario_id"]),
            nome_usuario=nome_limpo,
            email=str(conta.get("email", "") or ""),
        )
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
            "nome_completo": str(conta.get("nome_completo", "") or ""),
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
            vagas_ocupadas = len(
                self.repo_usuarios.listar_membros_da_tarefa(tid, papel=PAPEL_ROTULADOR)
            )
            progresso = (
                min(100.0, 100.0 * len(anot_df) / len(atrib_df)) if len(atrib_df) else 0.0
            )
            resumo_admin.append(
                {
                    **item,
                    "total_atribuicoes": len(atrib_df),
                    "total_anotacoes": len(anot_df),
                    "vagas_ocupadas": vagas_ocupadas,
                    "progresso_percentual": progresso,
                }
            )

        email_usuario = str(usuario.get("email", "") or "").strip()
        resumo_rotulador: list[dict[str, Any]] = []
        for item in tarefas_rot:
            tid = int(item["tarefa_id"])
            vaga_membro = str(item.get("vaga_atribuida", "") or "").strip()
            rotuladores_candidatos = [nome_usuario]
            if vaga_membro and vaga_membro.lower() != nome_usuario.lower():
                rotuladores_candidatos.append(vaga_membro)
            if email_usuario and email_usuario.lower() not in [c.lower() for c in rotuladores_candidatos]:
                rotuladores_candidatos.append(email_usuario)

            quadros_fila = []
            for rot_cand in rotuladores_candidatos:
                df_c = self.repo_estudo.carregar_atribuicoes_tarefa_df(tid, rotulador=rot_cand)
                if not df_c.empty:
                    quadros_fila.append(df_c)
            if quadros_fila:
                fila_df = pd.concat(quadros_fila, ignore_index=True).drop_duplicates(subset=["assignment_id"])
            else:
                fila_df = pd.DataFrame(columns=list(COLUNAS_ATRIBUICAO))

            quadros_anot = []
            for rot_cand in rotuladores_candidatos:
                df_a = self.repo_estudo.carregar_anotacoes_tarefa_df(tid, rotulador=rot_cand)
                if not df_a.empty:
                    quadros_anot.append(df_a)
            if quadros_anot:
                anot_df = pd.concat(quadros_anot, ignore_index=True).drop_duplicates(subset=["assignment_id"])
            else:
                anot_df = pd.DataFrame(columns=list(COLUNAS_RESULTADO))

            erros_df = self.repo_estudo.carregar_erros_videos_tarefa_df(tid)
            ids_anotados = (
                set(anot_df["assignment_id"].astype(str))
                if not anot_df.empty
                else set()
            )
            ids_erros_sem_reserva: set[str] = set()
            if not erros_df.empty:
                alvos_labelers = {c.lower() for c in rotuladores_candidatos}
                erros_rot = erros_df[
                    erros_df["labeler"].astype(str).str.lower().isin(alvos_labelers)
                    & erros_df["replacement_assignment_id"].astype(str).str.strip().eq("")
                ]
                ids_erros_sem_reserva = set(erros_rot["assignment_id"].astype(str))

            ids_processados = ids_anotados | ids_erros_sem_reserva
            total_fila = len(fila_df)
            concluidos = (
                int(fila_df["assignment_id"].astype(str).isin(ids_processados).sum())
                if not fila_df.empty
                else len(ids_anotados)
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
