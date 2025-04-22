# Author: Guilherme Crepaldi
# watcher.py - Busca pagina, extrai texto puro, gera hash SHA256, compara com ultimo estado

import hashlib
import logging
from typing import Optional, Tuple

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Config default — timeout razoavel pra evitar travar
REQUEST_TIMEOUT = 30  # segundos
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def extrair_texto_puro(html: str) -> str:
    """
    Extrai texto visivel do HTML, ignorando scripts, estilos e whitespace extra.
    As vezes o site muda o layout sem mudar o conteudo, entao extraio texto puro.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Remove tags que nao carregam conteudo visivel
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()

    texto = soup.get_text(separator="\n")
    # Limpa linhas em branco excessivas mas preserva estrutura
    linhas = [linha.strip() for linha in texto.split("\n")]
    linhas = [l for l in linhas if len(l) > 0]
    return "\n".join(linhas)


def calcular_hash(texto: str) -> str:
    """Gera SHA256 do texto extraido. Ignora variacao de whitespace."""
    # Normaliza whitespace antes de hashear
    normalizado = "\n".join(linha.strip() for linha in texto.split("\n"))
    return hashlib.sha256(normalizado.encode("utf-8")).hexdigest()


def buscar_pagina(url: str) -> Optional[str]:
    """
    Faz request HTTP GET na URL e retorna o HTML bruto.
    Retorna None se der erro.
    """
    try:
        resp = requests.get(
            url,
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": USER_AGENT},
        )
        resp.raise_for_status()
        # Detecta encoding — sites brasileiros as vezes usam ISO-8859-1
        resp.encoding = resp.apparent_encoding or "utf-8"
        return resp.text
    except requests.RequestException as e:
        logger.error("Erro ao buscar %s: %s", url, e)
        return None


def verificar_mudanca(url: str, conteudo_anterior: Optional[str] = None) -> Tuple[str, Optional[str], bool]:
    """
    Pipeline completo:
    1. Busca pagina
    2. Extrai texto puro
    3. Calcula hash
    4. Compara com hash anterior

    Retorna: (texto_atual, hash_atual, mudou)
    Se conteudo_anterior for None, assume que eh a primeira verificacao -> mudou=False
    """
    html = buscar_pagina(url)
    if html is None:
        return "", None, False

    texto = extrair_texto_puro(html)
    hash_atual = calcular_hash(texto)

    if conteudo_anterior is None:
        # TODO: primeira vez, nao tem base de comparacao
        return texto, hash_atual, False

    mudou = hash_atual != conteudo_anterior
    return texto, hash_atual, mudou
