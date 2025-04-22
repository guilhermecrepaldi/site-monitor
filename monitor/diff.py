# Author: Guilherme Crepaldi
# diff.py - Mostra diferencas entre versoes (linha a linha) usando difflib

import difflib
from typing import List, Tuple


DiffLine = Tuple[str, str]  # (tipo, conteudo) — tipo: ' ', '+', '-', '?'


def gerar_diff(texto_antigo: str, texto_novo: str, contexto: int = 3) -> List[DiffLine]:
    """
    Compara duas versoes de texto e retorna linhas com marcacao.
    Usa unified_diff internamente mas retorna formato simpler.

    Args:
        texto_antigo: versao anterior do texto
        texto_novo: versao atual do texto
        contexto: linhas de contexto antes/depois (default 3)

    Returns:
        Lista de (tipo, conteudo):
        - (' ', linha) — contexto, igual
        - ('+', linha) — adicionada
        - ('-', linha) — removida
    """
    # as vezes o texto pode vir com quebras de linha no final diferentes
    linhas_antigas = texto_antigo.splitlines()
    linhas_novas = texto_novo.splitlines()

    diff = difflib.unified_diff(
        linhas_antigas,
        linhas_novas,
        fromfile="versao_anterior",
        tofile="versao_atual",
        n=contexto,
        lineterm="",
    )

    resultado: List[DiffLine] = []
    for linha in diff:
        # Pula cabecalhos do unified diff (--- / +++ / @@)
        if linha.startswith("---") or linha.startswith("+++"):
            continue
        if linha.startswith("@@"):
            continue

        if linha.startswith("+"):
            resultado.append(("+", linha[1:]))
        elif linha.startswith("-"):
            resultado.append(("-", linha[1:]))
        else:
            resultado.append((" ", linha))

    return resultado


def html_diff(texto_antigo: str, texto_novo: str, contexto: int = 3) -> str:
    """
    Gera HTML com highlight inline para exibir no navegador.
    Linhas adicionadas em verde, removidas em vermelho.
    """
    linhas = gerar_diff(texto_antigo, texto_novo, contexto)
    partes = ['<pre class="diff-viewer">']
    for tipo, conteudo in linhas:
        if tipo == "+":
            partes.append(f'<span class="diff-add">{conteudo}</span>\n')
        elif tipo == "-":
            partes.append(f'<span class="diff-remove">{conteudo}</span>\n')
        else:
            partes.append(f"<span>{conteudo}</span>\n")
    partes.append("</pre>")
    return "".join(partes)
