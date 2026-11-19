lint:
	uv run ruff format
	uv run ruff check --fix

lint-check:
	uv run ruff format --diff
	uv run ruff check

test:
	uv run python -m pytest --cov

dry-sample:
	./entrypoint.py --dry --extra-fields '{"portainer_version": "portainer/portainer-ce:?-alpine", "portainer_agent_version": "portainer/agent:?-alpine"}' --file-match '**/*.y*ml'

dry-sample-jsonpath:
	./entrypoint.py --dry --file-match '**/values*.y*ml' --image-name-jsonpath '$.image.repository' --image-tag-jsonpath '$.image.tag'

sample:
	env 'INPUT_NUMBER-ONE=1' 'INPUT_NUMBER-TWO=2' ./entrypoint.py

sample2:
	./entrypoint.py
