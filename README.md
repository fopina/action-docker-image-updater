# action-python-template

A template repository for GitHub Actions implemented in Python.

## Content

* `pytest` for tests: `make test`
* `ruff` for linting/formatting: `make lint` (replaces both `black` and `isort`)
* `.github` with actions ready to be used
    * ...
* `action.yml` and `entrypoint.py` to serve as placeholders with a valid dummy action
* Template README.md below

## New project checklist

* [ ] Replace `action.yml` with your action details
* [ ] Replace `entrypoint.py` with your code
* [ ] Replace `LICENSE` if MIT does not apply
* [ ] Search the project for `# TODO` to find the (minimum list of) places that need to be changed

---
---
---


[![Test](https://github.com/fopina/action-python-template/actions/workflows/test.yml/badge.svg)](https://github.com/fopina/action-python-template/actions/workflows/test.yml)
[![Test](https://github.com/fopina/action-python-template/actions/workflows/publish-image.yml/badge.svg)](https://github.com/fopina/action-python-template/actions/workflows/publish-image.yml)

# action-python-template

This action takes 2 integers as input and returns the sum of those in the output variable `sum`.

It also adds a joke to output `joke` to brighten your day.

# What's new

Please refer to the [release page](https://github.com/fopina/action-python-template/releases/latest) for the latest release notes.

# Usage

See [action.yml](action.yml)

# Scenarios

- [Sum two numbers](#sum-two-numbers)
- [Easter egg](#easter-egg)

## Sum two numbers

```yaml
- uses: fopina/action-python-template@v1
  id: sumit
  with:
    number-one: 3
    number-two: 5

- run: |
    echo ${{ steps.sumit.outputs.sum }}      
```

## Easter egg

```yaml
- uses: fopina/action-python-template@v1
  id: sumit

# use heredocs as this output might have special characters
- run: |
    cat <<'EOF'
    ${{ steps.sumit.outputs.sum }}
    EOF
```
