.PHONY: install test run-quick rebuild loop

install:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt

test:
	.venv/bin/python -m pytest tests/ -q

run-quick:
	.venv/bin/python -u crawler.py --rebuild --quick --limit 20

rebuild:
	.venv/bin/python -u crawler.py --rebuild --quick

loop:
	.venv/bin/python -u crawler.py --loop