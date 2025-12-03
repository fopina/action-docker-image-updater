lint:
	ruff format
	ruff check --fix

lint-check:
	ruff format --diff
	ruff check

test:
	python -m pytest --cov

dry-sample:
	./entrypoint.py --dry --extra-fields '{"portainer_version": "portainer/portainer-ce:?-alpine", "portainer_agent_version": "portainer/agent:?-alpine"}' --file-match '**/*.y*ml'

sample:
	env 'INPUT_NUMBER-ONE=1' 'INPUT_NUMBER-TWO=2' ./entrypoint.py

sample2:
	./entrypoint.py