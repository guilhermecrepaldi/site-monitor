# Author: Guilherme Crepaldi
# scheduler.py - Varredura periodica (a cada N minutos/horas) em thread separada

import logging
import threading
import time
from typing import Callable, Dict, Optional

logger = logging.getLogger(__name__)


class SiteScheduler:
    """
    Agendador de varredura periodica de sites.
    Roda em uma thread separada para nao bloquear a web UI.
    Cada site tem seu proprio intervalo entre verificacoes.
    """

    def __init__(self, check_fn: Optional[Callable] = None):
        """
        Args:
            check_fn: funcao a ser chamada quando um site precisar ser verificado.
                      Recebe (site_id: int, url: str) como argumentos.
        """
        self._check_fn = check_fn
        self._agenda: Dict[int, dict] = {}  # site_id -> {url, intervalo, ultima_verificacao, falhas_consecutivas}
        self._thread: Optional[threading.Thread] = None
        self._rodando = False
        self._lock = threading.Lock()

    def adicionar_site(self, site_id: int, url: str, intervalo_minutos: int = 60):
        """Adiciona um site na agenda do scheduler"""
        with self._lock:
            self._agenda[site_id] = {
                "url": url,
                "intervalo": intervalo_minutos * 60,  # converte pra segundos
                "ultima_verificacao": 0,
                "falhas_consecutivas": 0,
            }
            logger.info(
                "Site %d (%s) adicionado ao scheduler (intervalo=%d min)",
                site_id,
                url,
                intervalo_minutos,
            )

    def remover_site(self, site_id: int):
        """Remove um site da agenda"""
        with self._lock:
            self._agenda.pop(site_id, None)
            logger.info("Site %d removido do scheduler", site_id)

    def atualizar_intervalo(self, site_id: int, intervalo_minutos: int):
        """Atualiza o intervalo de varredura de um site"""
        with self._lock:
            if site_id in self._agenda:
                self._agenda[site_id]["intervalo"] = intervalo_minutos * 60

    def registrar_falha(self, site_id: int):
        """Incrementa contador de falhas consecutivas"""
        with self._lock:
            if site_id in self._agenda:
                self._agenda[site_id]["falhas_consecutivas"] += 1

    def registrar_sucesso(self, site_id: int):
        """Reseta contador de falhas apos verificacao bem-sucedida"""
        with self._lock:
            if site_id in self._agenda:
                self._agenda[site_id]["falhas_consecutivas"] = 0

    @property
    def sites_ativos(self) -> int:
        """Retorna quantos sites estao sendo monitorados agora"""
        return len(self._agenda)

    def start(self):
        """Inicia a thread do scheduler em background"""
        if self._rodando:
            logger.warning("Scheduler ja esta rodando")
            return

        self._rodando = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info("Scheduler iniciado em thread separada")

    def stop(self):
        """Para o scheduler graciosamente"""
        self._rodando = False
        logger.info("Scheduler parando...")

    def _loop(self):
        """Loop principal — executa enquanto self._rodando for True"""
        logger.info("Loop do scheduler iniciado")
        while self._rodando:
            agora = time.time()
            sites_para_verificar = []

            with self._lock:
                for site_id, info in self._agenda.items():
                    if (agora - info["ultima_verificacao"]) >= info["intervalo"]:
                        sites_para_verificar.append((site_id, info["url"]))
                        # Atualiza o timestamp pra evitar re-verificar no mesmo ciclo
                        info["ultima_verificacao"] = agora

            # Executa as verificacoes fora do lock pra nao travar a agenda
            for site_id, url in sites_para_verificar:
                try:
                    if self._check_fn:
                        self._check_fn(site_id, url)
                except Exception as e:
                    logger.exception("Erro no scheduler ao verificar site %d: %s", site_id, e)

            # Dorme 30s entre ciclos — resolução fina o suficiente
            for _ in range(30):
                if not self._rodando:
                    break
                time.sleep(1)

        logger.info("Loop do scheduler encerrado")
