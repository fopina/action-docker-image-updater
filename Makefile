lint:
	ruff format
	ruff check --fix

lint-check:
	ruff format --diff
	ruff check

test:
	python -m pytest --cov

sample:
	env 'INPUT_NUMBER-ONE=1' 'INPUT_NUMBER-TWO=2' ./entrypoint.py

sample2:
	./entrypoint.py