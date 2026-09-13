.PHONY: install test lint format-check run-quick rebuild loop

install:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements-dev.txt

test:
	.venv/bin/python -m pytest tests/ -q

lint:
	.venv/bin/ruff check .

format-check:
	.venv/bin/ruff format --check .

check:
	.venv/bin/ruff check .
	.venv/bin/ruff format --check .
	.venv/bin/python -m pytest tests/ -q

run-quick:
	.venv/bin/python -u crawler.py --rebuild --quick --limit 20

rebuild:
	.venv/bin/python -u crawler.py --rebuild --quick

loop:
	.venv/bin/python -u crawler.py --loop