# Author: Guilherme Crepaldi
# database.py - SQLite com 4 tabelas: sites, snapshots, alerts, schedules

import logging
import os
import sqlite3
from datetime import datetime
from typing import List, Optional, Tuple

from db.models import Alert, Site, Snapshot

logger = logging.getLogger(__name__)

# Schema SQL pra criar as tabelas se nao existirem
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS sites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL,
    nome TEXT NOT NULL DEFAULT '',
    intervalo_minutos INTEGER NOT NULL DEFAULT 60,
    ultimo_hash TEXT,
    ultima_verificacao TEXT,
    ativo INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id INTEGER NOT NULL,
    hash TEXT NOT NULL,
    filename TEXT NOT NULL,
    tamanho INTEGER NOT NULL DEFAULT 0,
    captured_at TEXT NOT NULL,
    FOREIGN KEY (site_id) REFERENCES sites(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id INTEGER NOT NULL,
    tipo TEXT NOT NULL DEFAULT 'mudanca',
    mensagem TEXT NOT NULL DEFAULT '',
    old_hash TEXT,
    new_hash TEXT,
    created_at TEXT NOT NULL,
    lido INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (site_id) REFERENCES sites(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id INTEGER NOT NULL UNIQUE,
    intervalo_minutos INTEGER NOT NULL DEFAULT 60,
    proxima_execucao TEXT,
    ultima_execucao TEXT,
    falhas_consecutivas INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (site_id) REFERENCES sites(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_snapshots_site_id ON snapshots(site_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_captured_at ON snapshots(captured_at);
CREATE INDEX IF NOT EXISTS idx_alerts_site_id ON alerts(site_id);
CREATE INDEX IF NOT EXISTS idx_alerts_created_at ON alerts(created_at);
CREATE INDEX IF NOT EXISTS idx_schedules_site_id ON schedules(site_id);
"""


class Database:
    """Gerenciador SQLite — conexao, schema, CRUD basico"""

    def __init__(self, db_path: str):
        """
        Args:
            db_path: caminho pro arquivo .db (ex: data/site-monitor.db)
        """
        self._db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None
        self._inicializar()

    def _inicializar(self):
        """Cria conexao e aplica schema se necessario"""
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute("PRAGMA foreign_keys=ON;")
        self._conn.executescript(SCHEMA_SQL)
        self._conn.commit()
        logger.info("Banco de dados inicializado em %s", self._db_path)

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._inicializar()
        return self._conn

    # ─── Sites ───────────────────────────────────────────────

    def adicionar_site(self, url: str, nome: str = "", intervalo_minutos: int = 60) -> int:
        """Adiciona um novo site pra monitorar. Retorna o ID."""
        cur = self.conn.execute(
            "INSERT INTO sites (url, nome, intervalo_minutos, created_at) VALUES (?, ?, ?, ?)",
            (url, nome, intervalo_minutos, datetime.now().isoformat()),
        )
        self.conn.commit()

        site_id = cur.lastrowid
        # Cria schedule padrao
        self.conn.execute(
            "INSERT INTO schedules (site_id, intervalo_minutos) VALUES (?, ?)",
            (site_id, intervalo_minutos),
        )
        self.conn.commit()
        logger.info("Site adicionado: id=%d url=%s", site_id, url)
        return site_id

    def listar_sites(self) -> List[Site]:
        """Retorna todos os sites cadastrados"""
        rows = self.conn.execute(
            "SELECT * FROM sites ORDER BY created_at DESC"
        ).fetchall()
        return [self._row_to_site(r) for r in rows]

    def buscar_site(self, site_id: int) -> Optional[Site]:
        """Busca um site pelo ID"""
        row = self.conn.execute(
            "SELECT * FROM sites WHERE id = ?", (site_id,)
        ).fetchone()
        return self._row_to_site(row) if row else None

    def atualizar_site(
        self,
        site_id: int,
        nome: Optional[str] = None,
        intervalo_minutos: Optional[int] = None,
        ultimo_hash: Optional[str] = None,
        ultima_verificacao: Optional[str] = None,
        ativo: Optional[bool] = None,
    ):
        """Atualiza campos de um site"""
        updates = []
        params = []
        if nome is not None:
            updates.append("nome = ?")
            params.append(nome)
        if intervalo_minutos is not None:
            updates.append("intervalo_minutos = ?")
            params.append(intervalo_minutos)
        if ultimo_hash is not None:
            updates.append("ultimo_hash = ?")
            params.append(ultimo_hash)
        if ultima_verificacao is not None:
            updates.append("ultima_verificacao = ?")
            params.append(ultima_verificacao)
        if ativo is not None:
            updates.append("ativo = ?")
            params.append(1 if ativo else 0)

        if updates:
            params.append(site_id)
            self.conn.execute(
                f"UPDATE sites SET {', '.join(updates)} WHERE id = ?",
                params,
            )
            self.conn.commit()

    def remover_site(self, site_id: int):
        """Remove um site e seus snapshots/alerts/schedules (cascade)"""
        self.conn.execute("DELETE FROM sites WHERE id = ?", (site_id,))
        self.conn.commit()
        logger.info("Site removido: id=%d", site_id)

    # ─── Snapshots ───────────────────────────────────────────

    def registrar_snapshot(self, snapshot: Snapshot) -> int:
        """Salva um snapshot no banco"""
        cur = self.conn.execute(
            "INSERT INTO snapshots (site_id, hash, filename, tamanho, captured_at) VALUES (?, ?, ?, ?, ?)",
            (snapshot.site_id, snapshot.hash, snapshot.filename, snapshot.tamanho, snapshot.captured_at),
        )
        self.conn.commit()
        return cur.lastrowid

    def listar_snapshots(self, site_id: int, limit: int = 50) -> List[Snapshot]:
        """Lista snapshots de um site, do mais recente pro mais antigo"""
        rows = self.conn.execute(
            "SELECT * FROM snapshots WHERE site_id = ? ORDER BY captured_at DESC LIMIT ?",
            (site_id, limit),
        ).fetchall()
        return [self._row_to_snapshot(r) for r in rows]

    def ultimo_snapshot(self, site_id: int) -> Optional[Snapshot]:
        """Retorna o snapshot mais recente de um site"""
        row = self.conn.execute(
            "SELECT * FROM snapshots WHERE site_id = ? ORDER BY captured_at DESC LIMIT 1",
            (site_id,),
        ).fetchone()
        return self._row_to_snapshot(row) if row else None

    # ─── Alerts ──────────────────────────────────────────────

    def registrar_alerta(self, alert: Alert) -> int:
        """Registra um alerta no banco"""
        cur = self.conn.execute(
            "INSERT INTO alerts (site_id, tipo, mensagem, old_hash, new_hash, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (alert.site_id, alert.tipo, alert.mensagem, alert.old_hash, alert.new_hash, alert.created_at),
        )
        self.conn.commit()
        return cur.lastrowid

    def listar_alertas(self, limit: int = 50) -> List[Alert]:
        """Lista alertas recentes"""
        rows = self.conn.execute(
            "SELECT * FROM alerts ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [self._row_to_alert(r) for r in rows]

    def alertas_nao_lidos(self) -> List[Alert]:
        """Retorna alertas que ainda nao foram lidos"""
        rows = self.conn.execute(
            "SELECT * FROM alerts WHERE lido = 0 ORDER BY created_at DESC"
        ).fetchall()
        return [self._row_to_alert(r) for r in rows]

    def marcar_alerta_lido(self, alert_id: int):
        """Marca um alerta como lido"""
        self.conn.execute("UPDATE alerts SET lido = 1 WHERE id = ?", (alert_id,))
        self.conn.commit()

    # ─── Estatisticas ────────────────────────────────────────

    def total_sites(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM sites").fetchone()[0]

    def mudancas_hoje(self) -> int:
        hoje = datetime.now().strftime("%Y-%m-%d")
        return self.conn.execute(
            "SELECT COUNT(*) FROM alerts WHERE date(created_at) = ? AND tipo = 'mudanca'",
            (hoje,),
        ).fetchone()[0]

    def alertas_ativos(self) -> int:
        return self.conn.execute(
            "SELECT COUNT(*) FROM alerts WHERE lido = 0"
        ).fetchone()[0]

    # ─── Helpers ─────────────────────────────────────────────

    @staticmethod
    def _row_to_site(row: sqlite3.Row) -> Site:
        return Site(
            id=row["id"],
            url=row["url"],
            nome=row["nome"],
            intervalo_minutos=row["intervalo_minutos"],
            ultimo_hash=row["ultimo_hash"],
            ultima_verificacao=row["ultima_verificacao"],
            ativo=bool(row["ativo"]),
            created_at=row["created_at"],
        )

    @staticmethod
    def _row_to_snapshot(row: sqlite3.Row) -> Snapshot:
        return Snapshot(
            id=row["id"],
            site_id=row["site_id"],
            hash=row["hash"],
            filename=row["filename"],
            tamanho=row["tamanho"],
            captured_at=row["captured_at"],
        )

    @staticmethod
    def _row_to_alert(row: sqlite3.Row) -> Alert:
        return Alert(
            id=row["id"],
            site_id=row["site_id"],
            tipo=row["tipo"],
            mensagem=row["mensagem"],
            old_hash=row["old_hash"],
            new_hash=row["new_hash"],
            created_at=row["created_at"],
            lido=bool(row["lido"]),
        )
