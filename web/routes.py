# Author: Guilherme Crepaldi
# routes.py - Rotas FastAPI + API REST

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, FastAPI, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from config import config
from db.database import Database
from db.models import Alert, Site, Snapshot
from monitor.diff import gerar_diff, html_diff
from monitor.notifier import notificar_console_e_email, notificar_webhook
from monitor.scheduler import SiteScheduler
from monitor.snapshot import SnapshotManager
from monitor.watcher import verificar_mudanca

logger = logging.getLogger(__name__)

# ─── Inicializacao dos modulos ──────────────────────────────

db = Database(config.db_path)
snapshot_mgr = SnapshotManager(config.snapshots_dir)
scheduler = SiteScheduler()
router = APIRouter()

# Template dir relativo a este arquivo
TEMPLATES_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


# ─── Funcao de callback do scheduler ───────────────────────

def _check_site(site_id: int, url: str):
    """
    Callback chamada pelo scheduler pra verificar um site.
    Executa a pipeline completa: busca, compara, notifica, salva.
    """
    site = db.buscar_site(site_id)
    if not site or not site.ativo:
        return

    logger.info("Verificando site %d: %s", site_id, site.nome or url)

    # Carrega ultimo snapshot pra comparar
    ultimo = snapshot_mgr.carregar_ultimo_snapshot(site_id)
    conteudo_anterior, hash_anterior = ultimo if ultimo else (None, None)

    texto_atual, hash_atual, mudou = verificar_mudanca(url, hash_anterior)

    if not texto_atual:
        # Erro ao buscar — registra falha
        scheduler.registrar_falha(site_id)
        db.atualizar_site(site_id, ultima_verificacao=datetime.now().isoformat())
        logger.warning("Falha na verificacao do site %d", site_id)
        return

    # Salva snapshot SEMPRE (mesmo sem mudanca, pra ter o registro)
    filename = snapshot_mgr.salvar_snapshot(site_id, texto_atual, hash_atual)
    snapshot = Snapshot(
        site_id=site_id,
        hash=hash_atual,
        filename=filename,
        tamanho=len(texto_atual),
    )
    db.registrar_snapshot(snapshot)
    db.atualizar_site(
        site_id,
        ultimo_hash=hash_atual,
        ultima_verificacao=datetime.now().isoformat(),
    )

    if mudou:
        scheduler.registrar_sucesso(site_id)
        nome_site = site.nome or url

        # Notifica
        notificar_console_e_email(url, nome_site)

        # Registra alerta no banco
        alert = Alert(
            site_id=site_id,
            tipo="mudanca",
            mensagem=f"O site {nome_site} foi modificado!",
            old_hash=hash_anterior or "",
            new_hash=hash_atual,
        )
        db.registrar_alerta(alert)

        logger.info("MUDANCA DETECTADA no site %d (%s)", site_id, nome_site)
    else:
        logger.debug("Site %d sem mudancas", site_id)


# ─── Inicializacao ──────────────────────────────────────────

def init_app(app: FastAPI):
    """Configura rotas, static files, e inicia o scheduler"""
    # Static files
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    # Router
    app.include_router(router)

    # Configura callback do scheduler
    scheduler._check_fn = _check_site

    # Carrega sites ativos no scheduler
    for site in db.listar_sites():
        if site.ativo and site.id:
            scheduler.adicionar_site(site.id, site.url, site.intervalo_minutos)

    scheduler.start()
    logger.info("App inicializado com %d sites ativos", scheduler.sites_ativos)


# ─── Rotas da Web UI ────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Pagina inicial — dashboard com cards de resumo"""
    sites = db.listar_sites()
    stats = {
        "total_sites": db.total_sites(),
        "mudancas_hoje": db.mudancas_hoje(),
        "alertas_ativos": db.alertas_ativos(),
        "sites_monitorando": scheduler.sites_ativos,
    }
    alertas_recentes = db.listar_alertas(limit=10)
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "sites": sites,
            "stats": stats,
            "alertas": alertas_recentes,
        },
    )


@router.get("/site/{site_id}", response_class=HTMLResponse)
async def site_detail(request: Request, site_id: int):
    """Pagina de detalhe de um site — timeline de mudancas e diff"""
    site = db.buscar_site(site_id)
    if not site:
        return HTMLResponse("Site nao encontrado", status_code=404)

    snapshots = db.listar_snapshots(site_id, limit=100)
    alertas = db.listar_alertas(limit=50)
    alertas_do_site = [a for a in alertas if a.site_id == site_id]

    # Prepara dados pra timeline
    timeline = []
    for snap in snapshots:
        # Procura alerta correspondente
        alerta_relacionado = next(
            (a for a in alertas_do_site if a.new_hash == snap.hash),
            None,
        )
        # Tenta carregar o texto pra mostrar preview
        timeline.append({
            "snapshot": snap,
            "alerta": alerta_relacionado,
        })

    return templates.TemplateResponse(
        "site_detail.html",
        {
            "request": request,
            "site": site,
            "timeline": timeline,
            "snapshots": snapshots,
        },
    )


@router.get("/site/{site_id}/diff/{snapshot_id}", response_class=HTMLResponse)
async def view_diff(request: Request, site_id: int, snapshot_id: int):
    """Exibe diff entre duas snapshots consecutivas"""
    site = db.buscar_site(site_id)
    if not site:
        return HTMLResponse("Site nao encontrado", status_code=404)

    snapshots = db.listar_snapshots(site_id, limit=100)

    # Encontra a snapshot atual e a anterior
    snapshot_atual = None
    snapshot_anterior = None
    for i, snap in enumerate(snapshots):
        if snap.id == snapshot_id:
            snapshot_atual = snap
            if i + 1 < len(snapshots):
                snapshot_anterior = snapshots[i + 1]
            break

    if not snapshot_atual:
        return HTMLResponse("Snapshot nao encontrada", status_code=404)

    # Carrega textos
    texto_atual = snapshot_mgr.carregar_snapshot(site_id, snapshot_atual.filename)
    texto_anterior = ""
    if snapshot_anterior:
        texto_anterior_loaded = snapshot_mgr.carregar_snapshot(site_id, snapshot_anterior.filename)
        if texto_anterior_loaded:
            texto_anterior = texto_anterior_loaded

    diff_html = html_diff(texto_anterior, texto_atual or "")
    diff_lines = gerar_diff(texto_anterior, texto_atual or "")

    return templates.TemplateResponse(
        "site_detail.html",
        {
            "request": request,
            "site": site,
            "diff_html": diff_html,
            "diff_lines": diff_lines,
            "snapshot_atual": snapshot_atual,
            "snapshot_anterior": snapshot_anterior,
        },
    )


@router.get("/add", response_class=HTMLResponse)
async def add_site_form(request: Request):
    """Formulario pra adicionar novo site"""
    return templates.TemplateResponse("add_site.html", {"request": request})


# ─── API REST ───────────────────────────────────────────────

@router.post("/api/sites")
async def api_add_site(
    url: str = Form(...),
    nome: str = Form(""),
    intervalo_minutos: int = Form(60),
):
    """API: adiciona um novo site"""
    if not url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="URL deve comecar com http:// ou https://")

    site_id = db.adicionar_site(url, nome, intervalo_minutos)
    scheduler.adicionar_site(site_id, url, intervalo_minutos)

    # Faz primeira verificacao imediatamente
    _check_site(site_id, url)

    return {"status": "ok", "site_id": site_id, "redirect": f"/site/{site_id}"}


@router.delete("/api/sites/{site_id}")
async def api_remove_site(site_id: int):
    """API: remove um site"""
    db.remover_site(site_id)
    scheduler.remover_site(site_id)
    snapshot_mgr.deletar_snapshots(site_id)
    return {"status": "ok"}


@router.get("/api/check/{site_id}")
async def api_check_now(site_id: int):
    """API: forca verificacao imediata de um site"""
    site = db.buscar_site(site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site nao encontrado")
    _check_site(site_id, site.url)
    return {"status": "ok"}


@router.get("/api/stats")
async def api_stats():
    """API: estatisticas do dashboard"""
    return {
        "total_sites": db.total_sites(),
        "mudancas_hoje": db.mudancas_hoje(),
        "alertas_ativos": db.alertas_ativos(),
        "sites_monitorando": scheduler.sites_ativos,
    }


@router.get("/api/alertas")
async def api_alertas(limit: int = Query(20)):
    """API: lista alertas recentes"""
    alertas = db.listar_alertas(limit=limit)
    return [
        {
            "id": a.id,
            "site_id": a.site_id,
            "tipo": a.tipo,
            "mensagem": a.mensagem,
            "created_at": a.created_at,
            "lido": a.lido,
        }
        for a in alertas
    ]


@router.post("/api/alertas/{alert_id}/read")
async def api_marcar_lido(alert_id: int):
    """API: marca alerta como lido"""
    db.marcar_alerta_lido(alert_id)
    return {"status": "ok"}
