# Notas do desenvolvedor — site-monitor

## Author: Guilherme Crepaldi

## Ideias / TODOs

- [ ] Adicionar suporte a JavaScript com Selenium (pra SPAs que renderizam client-side)
- [ ] Modo headless + screenshots das mudancas
- [ ] Agregar notificacoes em batch (nao mandar 1 email por mudanca)
- [ ] Exportar relatorio CSV de mudancas
- [ ] Suporte a autenticacao basica em sites protegidos
- [ ] Webhook com template customizavel
- [ ] Testes unitarios com pytest

## Observacoes

- As vezes o site muda o layout sem mudar o conteudo, entao extraio texto puro.
- O hash SHA256 ignora whitespace extra pra evitar falsos positivos.
- O scheduler roda em thread separada pra nao bloquear a web UI.

## Dependencias

- fastapi + uvicorn: servidor async
- beautifulsoup4: extracao de texto de HTML
- aiohttp: fetch async (futuro, pra watcher async)
- requests: fetch sincrono (usado no watcher atual)
