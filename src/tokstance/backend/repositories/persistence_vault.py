"""Cofre e Diário de Gravação Antecipada (WAL / Journal) para Anotações com Garantia Zero Perda."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import threading
import time
from typing import Any


class DiarioAnotacoesPersistencia:
    """Diário append-only com fsync obrigatório para persistência e recuperação de anotações de vídeos."""

    def __init__(self, caminho_journal: Path | str) -> None:
        self.caminho_journal = Path(caminho_journal).resolve()
        self.caminho_journal.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _calcular_checksum(self, tarefa_id: int, assignment_id: str, stance: str, timestamp: str) -> str:
        """Gera checksum SHA-256 para verificação criptográfica de integridade do registro."""
        conteudo = f"{tarefa_id}:{assignment_id}:{stance}:{timestamp}".encode("utf-8")
        return hashlib.sha256(conteudo).hexdigest()

    def registrar_pendente(self, dados: dict[str, Any]) -> dict[str, Any]:
        """Grava uma anotação no diário append-only com garantia física de fsync antes da transação SQLite."""
        tarefa_id = int(dados["tarefa_id"])
        assignment_id = str(dados["assignment_id"]).strip()
        stance = str(dados.get("stance", "") or dados.get("posicao", "")).strip()
        timestamp = str(dados.get("timestamp", "") or "")

        checksum = self._calcular_checksum(tarefa_id, assignment_id, stance, timestamp)

        registro = {
            "tipo": "anotacao",
            "tarefa_id": tarefa_id,
            "assignment_id": assignment_id,
            "usuario_id": dados.get("usuario_id"),
            "labeler": str(dados.get("labeler", "") or dados.get("rotulador", "")).strip(),
            "video_id": str(dados.get("video_id", "")).strip(),
            "url": str(dados.get("url", "")).strip(),
            "target": str(dados.get("target", "")),
            "stance": stance,
            "tempo_analise_segundos": float(dados.get("tempo_analise_segundos", 0.0) or 0.0),
            "video_duration": str(dados.get("video_duration", "") or ""),
            "timestamp": timestamp,
            "status": "pendente",
            "checksum": checksum,
            "gravado_em": time.time(),
        }

        linha = json.dumps(registro, ensure_ascii=False) + "\n"
        with self._lock:
            with open(self.caminho_journal, "a", encoding="utf-8") as f:
                f.write(linha)
                f.flush()
                os.fsync(f.fileno())

        return registro

    def marcar_sincronizado(self, tarefa_id: int, assignment_id: str) -> None:
        """Registra a confirmação de persistência (ack) no diário após commit no banco relacional."""
        ack = {
            "tipo": "ack",
            "tarefa_id": int(tarefa_id),
            "assignment_id": str(assignment_id).strip(),
            "status": "sincronizado",
            "gravado_em": time.time(),
        }
        linha = json.dumps(ack, ensure_ascii=False) + "\n"
        with self._lock:
            with open(self.caminho_journal, "a", encoding="utf-8") as f:
                f.write(linha)
                f.flush()
                os.fsync(f.fileno())

    def ler_registros_consolidados(self) -> dict[str, dict[str, Any]]:
        """Lê o diário append-only sequencialmente e consolida o estado final de cada anotação."""
        if not self.caminho_journal.exists():
            return {}

        consolidado: dict[str, dict[str, Any]] = {}
        with self._lock:
            with open(self.caminho_journal, "r", encoding="utf-8", errors="replace") as f:
                for linha in f:
                    linha = linha.strip()
                    if not linha:
                        continue
                    try:
                        obj = json.loads(linha)
                    except json.JSONDecodeError:
                        #ignora linhas incompletas decorrentes de interrupcao abrupta
                        continue

                    chave = f"{obj.get('tarefa_id')}:{obj.get('assignment_id')}"
                    tipo = obj.get("tipo", "anotacao")

                    if tipo == "anotacao":
                        consolidado[chave] = dict(obj)
                    elif tipo == "ack" and chave in consolidado:
                        consolidado[chave]["status"] = "sincronizado"

        return consolidado

    def obter_pendentes(self) -> list[dict[str, Any]]:
        """Retorna todas as anotações gravadas no diário que ainda não tiveram ack de sincronização."""
        consolidado = self.ler_registros_consolidados()
        return [reg for reg in consolidado.values() if reg.get("status") == "pendente"]

    def sincronizar_com_banco(self, banco: Any) -> int:
        """Reconcilia e persiste no banco SQLite quaisquer anotações que constem como pendentes."""
        pendentes = self.obter_pendentes()
        if not pendentes:
            return 0

        sincronizados = 0
        for reg in pendentes:
            try:
                banco.executar(
                    """
                    INSERT OR REPLACE INTO anotacoes (
                        tarefa_id, assignment_id, usuario_id, labeler, video_id,
                        url, target, stance, tempo_analise_segundos, video_duration, timestamp
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        int(reg["tarefa_id"]),
                        str(reg["assignment_id"]).strip(),
                        reg.get("usuario_id"),
                        str(reg.get("labeler", "")),
                        str(reg.get("video_id", "")),
                        str(reg.get("url", "")),
                        str(reg.get("target", "")),
                        str(reg.get("stance", "")),
                        float(reg.get("tempo_analise_segundos", 0.0) or 0.0),
                        str(reg.get("video_duration", "") or ""),
                        str(reg.get("timestamp", "")),
                    ),
                )
                self.marcar_sincronizado(reg["tarefa_id"], reg["assignment_id"])
                sincronizados += 1
            except Exception:
                #continua tentando os demais registros mesmo se um falhar
                continue

        return sincronizados

    def reconstruir_banco(self, banco: Any, tarefa_id: int | None = None) -> int:
        """Restaura todas as anotações do diário para o SQLite (ex: em caso de banco restaurado ou recriado)."""
        consolidado = self.ler_registros_consolidados()
        reconstruidos = 0
        for reg in consolidado.values():
            t_id = int(reg["tarefa_id"])
            if tarefa_id is not None and t_id != int(tarefa_id):
                continue
            banco.executar(
                """
                INSERT OR REPLACE INTO anotacoes (
                    tarefa_id, assignment_id, usuario_id, labeler, video_id,
                    url, target, stance, tempo_analise_segundos, video_duration, timestamp
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    t_id,
                    str(reg["assignment_id"]).strip(),
                    reg.get("usuario_id"),
                    str(reg.get("labeler", "")),
                    str(reg.get("video_id", "")),
                    str(reg.get("url", "")),
                    str(reg.get("target", "")),
                    str(reg.get("stance", "")),
                    float(reg.get("tempo_analise_segundos", 0.0) or 0.0),
                    str(reg.get("video_duration", "") or ""),
                    str(reg.get("timestamp", "")),
                ),
            )
            reconstruidos += 1
        return reconstruidos

    def compactar(self) -> None:
        """Compacta o diário de forma atômica, mantendo apenas a última versão consolidada de cada anotação."""
        if not self.caminho_journal.exists():
            return

        with self._lock:
            consolidado = self.ler_registros_consolidados()
            caminho_tmp = self.caminho_journal.with_suffix(".tmp")
            with open(caminho_tmp, "w", encoding="utf-8") as f:
                for reg in consolidado.values():
                    f.write(json.dumps(reg, ensure_ascii=False) + "\n")
                f.flush()
                os.fsync(f.fileno())
            os.replace(caminho_tmp, self.caminho_journal)
