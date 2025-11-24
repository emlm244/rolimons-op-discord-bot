.PHONY: setup lint mypy test run

setup:
	python -m venv .venv
	. .venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt

lint:
	. .venv/bin/activate && ruff check src tests

mypy:
	. .venv/bin/activate && mypy src

test:
	. .venv/bin/activate && PYTHONPATH=src pytest

run:
	. .venv/bin/activate && PYTHONPATH=src python -m rolimons_bot.bot
