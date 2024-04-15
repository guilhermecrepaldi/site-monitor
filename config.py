# Author: Guilherme Crepaldi
# Configuracoes centralizadas do site-monitor

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class EmailConfig:
    """Configuracoes de email para notificacoes"""
    enabled: bool = False
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_pass: str = ""
    from_addr: str = ""
    to_addr: str = ""


@dataclass
class WebhookConfig:
    """Webhook opcional tipo Slack/Discord"""
    enabled: bool = False
    url: str = ""
    headers: dict = field(default_factory=dict)


@dataclass
class SchedulerConfig:
    """Config da varredura periodica"""
    intervalo_padrao_minutos: int = 60  # 1 hora default
    max_consecutivos_erro: int = 5      # para silenciar alertas


@dataclass
class AppConfig:
    """Configuracao geral da aplicacao"""
    db_path: str = "data/site-monitor.db"
    snapshots_dir: str = "data/snapshots"
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True
    email: EmailConfig = field(default_factory=EmailConfig)
    webhook: WebhookConfig = field(default_factory=WebhookConfig)
    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)


# Singleton de config — carrega de variaveis de ambiente se existirem
def load_config() -> AppConfig:
    """Carrega config, priorizando env vars"""
    cfg = AppConfig()

    # DB path
    cfg.db_path = os.getenv("SM_DB_PATH", cfg.db_path)
    cfg.snapshots_dir = os.getenv("SM_SNAPSHOTS_DIR", cfg.snapshots_dir)
    cfg.host = os.getenv("SM_HOST", cfg.host)
    cfg.port = int(os.getenv("SM_PORT", str(cfg.port)))
    cfg.debug = os.getenv("SM_DEBUG", str(cfg.debug)).lower() == "true"

    # Email
    cfg.email.enabled = os.getenv("SM_EMAIL_ENABLED", "false").lower() == "true"
    cfg.email.smtp_host = os.getenv("SM_SMTP_HOST", cfg.email.smtp_host)
    cfg.email.smtp_port = int(os.getenv("SM_SMTP_PORT", str(cfg.email.smtp_port)))
    cfg.email.smtp_user = os.getenv("SM_SMTP_USER", "")
    cfg.email.smtp_pass = os.getenv("SM_SMTP_PASS", "")
    cfg.email.from_addr = os.getenv("SM_FROM_ADDR", "")
    cfg.email.to_addr = os.getenv("SM_TO_ADDR", "")
    cfg.webhook.enabled = os.getenv("SM_WEBHOOK_ENABLED", "false").lower() == "true"
    cfg.webhook.url = os.getenv("SM_WEBHOOK_URL", "")

    return cfg


config = load_config()
