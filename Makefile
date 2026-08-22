.PHONY: install test test-unit test-integration

install:
	pip install -r requirements.txt

test: test-unit test-integration

test-unit:
	python -m pytest tests/unit -q

test-integration:
	python -m pytest tests/integration -q
