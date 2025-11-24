PYTHON ?= python
VENV ?= .venv
ACTIVATE = . $(VENV)/bin/activate

$(VENV)/bin/activate:
	$(PYTHON) -m venv $(VENV)
	$(ACTIVATE) && pip install --upgrade pip

setup: $(VENV)/bin/activate
	$(ACTIVATE) && pip install -e .[dev]

lint:
	$(ACTIVATE) && $(PYTHON) -m ruff check src tests
	$(ACTIVATE) && $(PYTHON) -m flake8 src tests

test:
	$(ACTIVATE) && $(PYTHON) -m pytest

.PHONY: setup lint test
