# rolimons-op-discord-bot

Discord slash-command bot that calculates typical overpay (OP) ranges for Roblox limiteds using
Rolimon’s data, with embeds and optional alerts.

## Prerequisites
- Python 3.11+
- A Discord application with a bot token
- Access to Rolimon's item details endpoint

## Environment variables
- `DISCORD_BOT_TOKEN` (**required**): Bot token from your Discord application.
- `ROLIMONS_ITEM_ENDPOINT` (optional): Fully qualified URL for item detail data. Defaults to
  `https://www.rolimons.com/itemapi/itemdetails`.

Set these in your shell or in an `.env` file before starting the bot. Do not commit secrets.

## Setup
```bash
python -m venv .venv
make setup
```

## Running checks
```bash
make lint
make test
```

## Running the bot
This repository currently ships utility modules and tests. Wire them into your Discord bot by
fetching item data and formatting responses:
```python
from rolimons_bot import fetch_item_details, format_op_response

item = await fetch_item_details(123456)
message = format_op_response(item)
```

Use your preferred Discord framework to send the `message` as part of a slash-command response.
