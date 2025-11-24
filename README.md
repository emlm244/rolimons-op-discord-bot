# Rolimon's OP Discord Bot

Discord slash-command bot that calculates typical overpay (OP) ranges for Roblox limited items using Rolimon's data and returns them in a rich embed.

## Features
- `/op` slash command that fetches a Rolimon's item page, parses history data, and computes 25/50/75 percentile OP ranges for the past 30 days.
- Clean error handling when items are missing or Rolimon's is unavailable.
- Type-hinted code with linting (ruff) and type-checking (mypy).
- Unit tests for parsing and percentile logic.

## Setup
1. Create and activate a virtual environment, then install dependencies:
   ```bash
   make setup
   ```

2. Export your Discord bot token:
   ```bash
   export DISCORD_TOKEN="your-bot-token"
   ```

## Running the bot
Start the bot after activating the virtual environment:
```bash
make run
```
The bot registers the `/op` command; supply a Roblox limited `item_id` (e.g., `/op item_id:1029025`).

## Testing and linting
Run the automated checks:
```bash
make lint
make mypy
make test
```

## Notes
- The bot parses Rolimon's public item page HTML directly using a user-agent header to avoid 403 responses.
- OP bands are derived from `(best_price - rap)` deltas over the last 30 days of history data; if no recent points exist, all available history is used.
