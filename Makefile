.PHONY: setup test lint

setup:
python3 -m venv .venv
. .venv/bin/activate && pip install -r requirements.txt

lint:
. .venv/bin/activate && ruff check src tests
. .venv/bin/activate && black --check src tests

test:
. .venv/bin/activate && pytest
