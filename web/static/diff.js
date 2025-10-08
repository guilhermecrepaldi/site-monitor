// Author: Guilherme Crepaldi
// diff.js - Destaque de linhas adicionadas/removidas com animacao suave

(function () {
    "use strict";

    /**
     * Aplica highlight visual nas linhas do diff viewer.
     * As linhas ja vêm marcadas pelas classes CSS .diff-add e .diff-remove
     * do template, mas este script adiciona interatividade.
     */

    // ─── Expandir/recolher linhas de contexto ───────────────

    function setupContextToggle() {
        const diffViewers = document.querySelectorAll(".diff-viewer");

        diffViewers.forEach((viewer) => {
            const lines = viewer.querySelectorAll("span");
            let contextGroups = [];
            let currentGroup = null;

            // Agrupa linhas consecutivas de contexto
            lines.forEach((span, idx) => {
                if (
                    !span.classList.contains("diff-add") &&
                    !span.classList.contains("diff-remove")
                ) {
                    if (!currentGroup) {
                        currentGroup = { start: idx, lines: [] };
                        contextGroups.push(currentGroup);
                    }
                    currentGroup.lines.push(span);
                } else {
                    currentGroup = null;
                }
            });

            // Opcional: esconde grupos grandes de contexto (>5 linhas)
            // com um botao "Mostrar mais"
            contextGroups.forEach((group) => {
                if (group.lines.length > 5) {
                    const toggleBtn = document.createElement("button");
                    toggleBtn.className = "btn btn-sm btn-outline-secondary mb-1 mt-1";
                    toggleBtn.textContent = `⋯ Mostrar ${group.lines.length - 2} linhas de contexto`;

                    const hiddenLines = group.lines.slice(1, -1);
                    hiddenLines.forEach((el) => (el.style.display = "none"));

                    toggleBtn.addEventListener("click", function () {
                        const isHidden = hiddenLines[0].style.display === "none";
                        hiddenLines.forEach((el) => {
                            el.style.display = isHidden ? "block" : "none";
                        });
                        this.textContent = isHidden
                            ? "⋯ Esconder linhas"
                            : `⋯ Mostrar ${group.lines.length - 2} linhas de contexto`;
                    });

                    group.lines[0].before(toggleBtn);
                }
            });
        });
    }

    // ─── Copiar diff com cores para clipboard ───────────────

    function setupCopyButton() {
        const copyBtn = document.getElementById("copy-diff-btn");
        if (!copyBtn) return;

        copyBtn.addEventListener("click", function () {
            const diffViewer = document.querySelector(".diff-viewer");
            if (!diffViewer) return;

            const lines = diffViewer.querySelectorAll("span");
            let text = "";
            lines.forEach((span) => {
                const prefix = span.classList.contains("diff-add")
                    ? "+ "
                    : span.classList.contains("diff-remove")
                    ? "- "
                    : "  ";
                text += prefix + span.textContent + "\n";
            });

            navigator.clipboard.writeText(text).then(() => {
                const original = this.textContent;
                this.textContent = "✓ Copiado!";
                setTimeout(() => {
                    this.textContent = original;
                }, 2000);
            });
        });
    }

    // ─── Scroll suave ate o diff ───────────────────────────

    function setupDiffLinks() {
        document.querySelectorAll("[data-diff-target]").forEach((link) => {
            link.addEventListener("click", function (e) {
                e.preventDefault();
                const targetId = this.getAttribute("data-diff-target");
                const target = document.getElementById(targetId);
                if (target) {
                    target.scrollIntoView({ behavior: "smooth", block: "start" });
                }
            });
        });
    }

    // ─── Inicializar quando o DOM estiver pronto ───────────

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", () => {
            setupContextToggle();
            setupCopyButton();
            setupDiffLinks();
        });
    } else {
        setupContextToggle();
        setupCopyButton();
        setupDiffLinks();
    }
})();
