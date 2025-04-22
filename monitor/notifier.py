# Author: Guilherme Crepaldi
# notifier.py - Notifica mudancas detectadas: console + opcional email + webhook

import json
import logging
import smtplib
from email.mime.text import MIMEText
from typing import Optional

import aiohttp

from config import config

logger = logging.getLogger(__name__)


def notificar_console(url: str, site_name: str):
    """Exibe alerta no console com emoji — visivel no terminal do servidor"""
    logger.info(
        "🔔 MUDANCA DETECTADA | Site: %s | URL: %s",
        site_name,
        url,
    )
    print(
        f"\n{'='*60}\n"
        f"🔔 MUDANCA DETECTADA\n"
        f"   Site: {site_name}\n"
        f"   URL:  {url}\n"
        f"   Hora: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"{'='*60}\n"
    )


def notificar_email(
    url: str,
    site_name: str,
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_pass: str,
    from_addr: str,
    to_addr: str,
):
    """
    Envia alerta por email via SMTP.
    Configuravel via config.py ou env vars.
    """
    if not all([smtp_host, smtp_user, smtp_pass, from_addr, to_addr]):
        logger.warning("Email notifier: configuracao incompleta, pulando email")
        return

    subject = f"🔔 site-monitor: Mudanca detectada em {site_name}"
    body = (
        f"O site {site_name} foi modificado!\n\n"
        f"URL: {url}\n"
        f"Data/hora: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"Acesse o dashboard para ver o diff: http://localhost:{config.port}\n"
    )

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        logger.info("Email de alerta enviado para %s", to_addr)
    except smtplib.SMTPException as e:
        logger.error("Falha ao enviar email: %s", e)


def notificar_console_e_email(
    url: str,
    site_name: str = "desconhecido",
):
    """Atalho que dispara console + email (se configurado) simultaneamente"""
    notificar_console(url, site_name)

    email_cfg = config.email
    if email_cfg.enabled:
        notificar_email(
            url=url,
            site_name=site_name,
            smtp_host=email_cfg.smtp_host,
            smtp_port=email_cfg.smtp_port,
            smtp_user=email_cfg.smtp_user,
            smtp_pass=email_cfg.smtp_pass,
            from_addr=email_cfg.from_addr,
            to_addr=email_cfg.to_addr,
        )


async def notificar_webhook(url: str, site_name: str, site_url: str):
    """
    Envia alerta para webhook (Slack, Discord, etc).
    Usa aiohttp pra nao bloquear o event loop.
    """
    webhook_cfg = config.webhook
    if not webhook_cfg.enabled or not webhook_cfg.url:
        return

    payload = {
        "text": f"🔔 *site-monitor*\nMudanca detectada em *{site_name}*\nURL: {site_url}\nDashboard: http://localhost:{config.port}",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                webhook_cfg.url,
                json=payload,
                headers=webhook_cfg.headers or {"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status not in (200, 201, 204):
                    logger.warning("Webhook retornou status %d", resp.status)
                else:
                    logger.info("Webhook enviado com sucesso")
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        logger.error("Falha ao enviar webhook: %s", e)
