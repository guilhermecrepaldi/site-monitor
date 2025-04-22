# Author: Guilherme Crepaldi
# snapshot.py - Salva snapshots das paginas (historico de mudancas)

import json
import logging
import os
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class SnapshotManager:
    """
    Gerencia snapshots de paginas — cada versao capturada de um site
    eh salva como um arquivo JSON individual no diretorio de snapshots.
    """

    def __init__(self, snapshots_dir: str):
        """
        Args:
            snapshots_dir: diretorio onde os snapshots serao salvos
        """
        self._snapshots_dir = snapshots_dir
        os.makedirs(snapshots_dir, exist_ok=True)

    def _site_dir(self, site_id: int) -> str:
        """Retorna o path do diretorio de snapshots de um site especifico"""
        path = os.path.join(self._snapshots_dir, str(site_id))
        os.makedirs(path, exist_ok=True)
        return path

    def salvar_snapshot(self, site_id: int, texto: str, hash_atual: str) -> str:
        """
        Salva uma nova snapshot da pagina.

        Args:
            site_id: ID do site no banco
            texto: texto puro extraido da pagina
            hash_atual: SHA256 do texto

        Returns:
            str: filename do snapshot salvo
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"snapshot_{timestamp}_{hash_atual[:12]}.json"
        filepath = os.path.join(self._site_dir(site_id), filename)

        snapshot_data = {
            "site_id": site_id,
            "timestamp": datetime.now().isoformat(),
            "hash": hash_atual,
            "conteudo": texto,
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(snapshot_data, f, ensure_ascii=False, indent=2)

        logger.debug("Snapshot salvo: %s", filepath)
        return filename

    def listar_snapshots(self, site_id: int) -> list[dict]:
        """
        Lista todos os snapshots de um site, ordenados do mais recente ao mais antigo.

        Returns:
            Lista de dicts com metadados (sem o conteudo completo)
        """
        site_dir = self._site_dir(site_id)
        snapshots = []

        if not os.path.isdir(site_dir):
            return snapshots

        for fname in sorted(os.listdir(site_dir), reverse=True):
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(site_dir, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                snapshots.append({
                    "filename": fname,
                    "timestamp": data.get("timestamp", ""),
                    "hash": data.get("hash", ""),
                })
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Erro ao ler snapshot %s: %s", fname, e)

        return snapshots

    def carregar_snapshot(self, site_id: int, filename: str) -> Optional[str]:
        """
        Carrega o texto de um snapshot especifico.

        Returns:
            str: conteudo textual do snapshot, ou None se erro
        """
        filepath = os.path.join(self._site_dir(site_id), filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("conteudo")
        except (json.JSONDecodeError, OSError) as e:
            logger.error("Erro ao carregar snapshot %s: %s", filename, e)
            return None

    def carregar_ultimo_snapshot(self, site_id: int) -> Optional[tuple]:
        """
        Carrega o snapshot mais recente de um site.

        Returns:
            tuple: (texto, hash) ou None se nao houver snapshot
        """
        snapshots = self.listar_snapshots(site_id)
        if not snapshots:
            return None

        ultimo = snapshots[0]  # mais recente
        texto = self.carregar_snapshot(site_id, ultimo["filename"])
        if texto is None:
            return None

        return (texto, ultimo["hash"])

    def deletar_snapshots(self, site_id: int):
        """Remove todos os snapshots de um site (ex: quando o site eh removido)"""
        site_dir = self._site_dir(site_id)
        if os.path.isdir(site_dir):
            for fname in os.listdir(site_dir):
                os.remove(os.path.join(site_dir, fname))
            os.rmdir(site_dir)
            logger.info("Snapshots do site %d removidos", site_id)
