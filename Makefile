.PHONY: setup test run

setup:
python -m venv .venv
. .venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt

test:
. .venv/bin/activate && pytest

run:
. .venv/bin/activate && python -m src.bot
