# Author: Guilherme Crepaldi
# main.py - FastAPI app entry point para site-monitor

import logging
import sys

import uvicorn
from fastapi import FastAPI

from config import config
from web.routes import init_app

# ─── Logging ────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if config.debug else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


# ─── App Factory ────────────────────────────────────────────

app = FastAPI(
    title="site-monitor",
    description="Monitor de mudancas em sites — detecta alteracoes, exibe diffs, envia alertas",
    version="1.0.0",
)


@app.on_event("startup")
async def startup():
    """Inicializa banco, scheduler e carrega sites"""
    logger.info("Iniciando site-monitor...")
    init_app(app)
    logger.info("site-monitor pronto em http://%s:%d", config.host, config.port)


@app.on_event("shutdown")
async def shutdown():
    """Para o scheduler graciosamente ao desligar"""
    from web.routes import scheduler
    scheduler.stop()
    logger.info("site-monitor encerrado")


# ─── Health check ───────────────────────────────────────────

@app.get("/health")
async def health():
    """Endpoint de health check"""
    return {"status": "ok", "app": "site-monitor", "version": "1.0.0"}


# ─── Entry point ────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=config.host,
        port=config.port,
        reload=config.debug,
        log_level="debug" if config.debug else "info",
    )
