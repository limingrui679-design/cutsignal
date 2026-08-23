.PHONY: install install-ui format lint test cases verify score demo ui

install:
	python -m pip install -e '.[dev]'

install-ui:
	python -m pip install -e '.[ui]'

format:
	ruff format .

lint:
	ruff check .
	ruff format --check .
	mypy src/cutsignal

test:
	pytest --cov=cutsignal --cov-report=term-missing

cases:
	cutsignal cases verify --output artifacts/cases.json

verify:
	python scripts/verify_project.py

score:
	python scripts/score_project.py

demo:
	cutsignal demo --output artifacts/demo

ui:
	cutsignal ui
