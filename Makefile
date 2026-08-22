.PHONY: install test test-unit test-integration

install:
	pip install -r requirements.txt

test: test-unit test-integration

test-unit:
	pytest tests/unit -q

test-integration:
	pytest tests/integration -q
