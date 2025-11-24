# rolimons-op-discord-bot

Discord slash-command bot that calculates typical overpay (OP) ranges for Roblox limiteds using Rolimon’s data, with embeds and optional alerts.

## Getting started

```bash
make setup
```

This installs runtime and development dependencies pinned in `requirements.txt` and `requirements-dev.txt`.

## Commands

- `make test` – run the sample unit tests (command parsing, Rolimon’s adapter, OP calculations).
- `make lint` – run Ruff, Black, isort, and mypy in check mode.
- `make format` – auto-format with Black and isort.
- `make typecheck` – type-check with mypy.

## Testing strategy

The code is structured for headless, deterministic testing:

- `rolimons_op_bot.commands.parse_op_command` parses slash-command text into structured arguments with validation.
- `rolimons_op_bot.rolimons.RolimonsClient` accepts an injectable HTTP client, so tests mock network calls without real API requests.
- `rolimons_op_bot.op_range.calculate_op_range` computes OP bands with configurable tolerance.

Pytest fixtures in `tests/` demonstrate how to mock the adapter and validate calculations. CI runs the full suite on every push/PR.
