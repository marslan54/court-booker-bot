.PHONY: setup run test test-allure allure-serve lint ci docker-build docker-run

setup:
	python -m venv .venv
	. .venv/bin/activate && pip install -r requirements.txt && playwright install chromium

run:
	python main.py

test:
	python -m pytest

test-allure:
	python -m pytest --clean-alluredir --alluredir=allure-results --junitxml=test-results.xml

allure-serve:
	allure serve allure-results

lint:
	python -m flake8 .

ci: lint test-allure

docker-build:
	docker build -t courtbooker-bot .

docker-run:
	docker compose up --build
