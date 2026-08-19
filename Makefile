.PHONY: install format lint test verify score demo ui

install:
	python -m pip install -e '.[dev]'

format:
	ruff format .

lint:
	ruff check .
	ruff format --check .
	mypy src/cutsignal

test:
	pytest --cov=cutsignal --cov-report=term-missing

verify:
	python scripts/verify_project.py

score:
	python scripts/score_project.py

demo:
	cutsignal demo --output artifacts/demo

ui:
	cutsignal ui
