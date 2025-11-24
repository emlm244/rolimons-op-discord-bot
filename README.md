# rolimons-op-discord-bot

Discord slash-command bot that calculates typical overpay (OP) ranges for Roblox limiteds using Rolimon’s data, with embeds and optional alerts.

## Features
- `/op item <item_id>` returns an embed with 30d typical OP range, thumbnail, and optional proof links.
- Optional DM of recent proofs (up to 6 months) with `send_dm` parameter.
- `/alert add <item_id> <min_op>` for staff-only alerting with per-guild rate limits and background polling.
- Configurable via environment variables; ready for Docker or systemd deployments.

## Configuration
Set the following environment variables (e.g., via `.env`):

- `DISCORD_TOKEN` (required): Bot token.
- `DISCORD_GUILD_ID` (optional): Restrict slash commands to a single guild for faster sync.
- `ROLIMONS_BASE_URL` (default `https://www.rolimons.com`): Base URL for Rolimon’s endpoints.
- `ROLIMONS_API_KEY` (optional): API key header if your data source requires it.
- `ROLIMONS_PROOFS_URL` (optional): Base URL for proof lookups.
- `STAFF_ROLE_IDS` (optional): Comma-separated staff role IDs that may manage alerts.
- `ALERT_RATE_LIMIT_SECONDS` (default `60`): Min seconds between alert creations per guild.
- `ALERT_POLL_SECONDS` (default `300`): Poll interval for alert checks.
- `ALERT_LOOKBACK_DAYS` (default `30`): Lookback window for alert calculations.
- `DM_PROOFS_LOOKBACK_MONTHS` (default `6`): Lookback window for DM proof fetches.

## Installation & Usage

```bash
make setup  # create venv and install dependencies
source .venv/bin/activate
make run    # start the bot
```

### Docker
Build and run with Docker:

```bash
docker build -t rolimons-op-bot .
docker run -e DISCORD_TOKEN=... --env-file .env rolimons-op-bot
```

### systemd
A sample service file is available at `deploy/rolimons-bot.service`. Update the paths and install with:

```bash
sudo cp deploy/rolimons-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now rolimons-bot
```

## Testing
Run the unit tests with:

```bash
make test
```
