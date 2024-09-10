# Author: Guilherme Crepaldi
# models.py - Dataclasses: Site, Snapshot, Alert, Schedule

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Site:
    """Representa um site sendo monitorado"""
    id: Optional[int] = None
    url: str = ""
    nome: str = ""
    intervalo_minutos: int = 60
    ultimo_hash: Optional[str] = None
    ultima_verificacao: Optional[str] = None
    ativo: bool = True
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class Snapshot:
    """Registro de uma captura de pagina — historico de mudancas"""
    id: Optional[int] = None
    site_id: int = 0
    hash: str = ""
    filename: str = ""
    tamanho: int = 0
    captured_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class Alert:
    """Alerta gerado quando uma mudanca eh detectada"""
    id: Optional[int] = None
    site_id: int = 0
    tipo: str = "mudanca"  # mudanca, erro, recuperacao
    mensagem: str = ""
    old_hash: Optional[str] = None
    new_hash: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    lido: bool = False


@dataclass
class Schedule:
    """Configuracao de agendamento (persistida)"""
    id: Optional[int] = None
    site_id: int = 0
    intervalo_minutos: int = 60
    proxima_execucao: Optional[str] = None
    ultima_execucao: Optional[str] = None
    falhas_consecutivas: int = 0
