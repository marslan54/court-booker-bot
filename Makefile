.PHONY: setup run test lint ci docker-build docker-run

setup:
	python -m venv .venv
	. .venv/bin/activate && pip install -r requirements.txt && playwright install chromium

run:
	python main.py

test:
	python -m pytest

lint:
	python -m flake8 .

ci: lint test

docker-build:
	docker build -t courtbooker-bot .

docker-run:
	docker compose up --build
