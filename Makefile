.PHONY: setup test lint format typecheck

setup:
	python -m pip install --upgrade pip
	python -m pip install -r requirements.txt -r requirements-dev.txt

lint:
	ruff check .
	black --check .
	isort --check-only .
	mypy .

format:
	black .
	isort .

typecheck:
	mypy .

test:
	PYTHONPATH=. pytest
