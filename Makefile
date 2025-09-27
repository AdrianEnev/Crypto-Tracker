# Makefile for the Crypto Tracker

.PHONY: install test run report tune lint

install:
	python3 -m venv .venv
	. .venv/bin/activate && pip install -r requirements.txt

test:
	. .venv/bin/activate && pytest -q

run:
	. .venv/bin/activate && python -m src.entry

report:
	. .venv/bin/activate && python scripts/reporting.py

tune:
	. .venv/bin/activate && python scripts/tune.py

lint:
	. .venv/bin/activate && flake8 src tests
