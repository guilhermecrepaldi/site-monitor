# site-monitor 🔍

A web-based website change monitor that detects modifications in web pages, tracks diffs over time, and sends alerts via console, email, or webhook.

Perfect for monitoring prices, public notices (editais), competitor websites, documentation pages — any scenario where you need to know *when* something changed and *what* changed.

---

## Features

- **Automated page watching** — fetches URLs, extracts clean text, and compares via SHA-256 hash
- **Diff viewer** — highlights added (green) and removed (red) lines between page versions
- **Timeline** — full history of every detected change for each site
- **Scheduled scanning** — configurable interval per site (N minutes/hours)
- **Multi-channel alerts** — console output with emojis, optional SMTP email, optional webhook (Slack/Discord)
- **Dark Bootstrap 5 UI** — dashboard with live stats, site management, and inline diff view
- **SQLite backend** — zero-config database, portable

## Quick Start

```bash
# 1. Clone & enter
cd site-monitor

# 2. Create virtualenv
python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run
python main.py
```

Open **http://localhost:8000** in your browser.

## Configuration

Set environment variables before running:

| Variable | Default | Description |
|---|---|---|
| `SM_DB_PATH` | `data/site-monitor.db` | SQLite file path |
| `SM_SNAPSHOTS_DIR` | `data/snapshots` | Snapshot JSON storage |
| `SM_HOST` | `0.0.0.0` | Server bind address |
| `SM_PORT` | `8000` | Server port |
| `SM_EMAIL_ENABLED` | `false` | Enable email alerts |
| `SM_SMTP_HOST` | `smtp.gmail.com` | SMTP server |
| `SM_SMTP_PORT` | `587` | SMTP port |
| `SM_SMTP_USER` | — | SMTP username |
| `SM_SMTP_PASS` | — | SMTP password |
| `SM_FROM_ADDR` | — | Sender email |
| `SM_TO_ADDR` | — | Recipient email |
| `SM_WEBHOOK_ENABLED` | `false` | Enable webhook |
| `SM_WEBHOOK_URL` | — | Webhook URL |

## Screenshot

> *(Add your screenshot here)*

## Project Structure

```
site-monitor/
├── main.py              # FastAPI entry point
├── config.py            # Centralized configuration
├── monitor/
│   ├── watcher.py       # Fetch + hash comparison
│   ├── diff.py          # Line-by-line diff
│   ├── scheduler.py     # Periodic scanning thread
│   ├── notifier.py      # Console/email/webhook alerts
│   └── snapshot.py      # Version history in JSON
├── db/
│   ├── database.py      # SQLite CRUD
│   └── models.py        # Dataclasses
├── web/
│   ├── routes.py        # FastAPI routes + API
│   ├── templates/       # Jinja2 templates
│   └── static/          # CSS, JS
└── requirements.txt
```

## License

MIT
