# Rolimon's OP Discord Bot

Discord slash-command bot that calculates typical overpay (OP) ranges for Roblox limiteds using Rolimon’s data, with embeds and optional alerts.

## Features

- `/op <item>` returns value, RAP, demand, typical OP (30d average), OP ranges, and a thumbnail embed.
- Button to DM recent OP proofs (up to 6 months) without cluttering the channel.
- `/alert <item> <min_op>` saves DM alerts for staff (Manage Server) to monitor minimum OP thresholds.
- Simple file-based persistence scoped per server and background polling for alert triggers.
- Rate limiting, permission checks, and friendly error handling for 24/7 readiness.

## Project layout

```
src/
  bot/
    config.py       # Environment-driven settings
    data.py         # Rolimon's client, OP computations
    main.py         # Discord bot entrypoint + commands
    rate_limiter.py # Sliding-window rate limiter
    storage.py      # File-based alert persistence
```

## Setup

1. Create a virtual environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Configure environment variables (use a `.env` file locally):

- `DISCORD_TOKEN` (required): Bot token.
- `GUILD_IDS` (comma-separated, optional): Guild IDs for faster slash-command sync.
- `ROLIMONS_ITEMS_URL` (optional): URL returning Rolimon's item details JSON (default: `https://www.rolimons.com/itemapi/itemdetails`).
- `ROLIMONS_PROOFS_URL` (optional): Base URL for proof history JSON (default assumes `<base>/<item_id>.json`).
- `DATA_DIR` (optional): Directory for persistence (defaults to `./data`).
- `ALERT_POLL_SECONDS` (optional): Alert polling cadence (defaults to `1800`).

Example `.env`:

```
DISCORD_TOKEN=your_token_here
GUILD_IDS=1234567890,2345678901
```

## Running the bot

```bash
export $(cat .env | xargs)  # or rely on pydantic loading .env automatically
PYTHONPATH=src python -m bot.main
```

Run the process under a supervisor (systemd, Docker, or a process manager) for 24/7 hosting and keep the `.env` secret.

## Alerts and proofs

- `/op <item>`: responds in-channel with a rich embed and a button to DM proofs (up to 10 entries from the last 6 months).
- `/alert <item> <min_op>`: staff-only (requires Manage Server). Stores alerts per guild and DMs when a new proof meets/exceeds `min_op`.

## Testing and linting

```bash
make setup
make test
make lint
```

## Make targets

- `make setup`: install dependencies into `.venv`.
- `make test`: run pytest suite.
- `make lint`: run ruff and black checks.

## Notes

- Secrets are never hardcoded; configuration is pulled from environment variables.
- Network calls include basic timeouts, and the bot defers responses while fetching Rolimon data.
