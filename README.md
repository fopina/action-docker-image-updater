[![Test](https://github.com/fopina/action-docker-image-updater/actions/workflows/test.yml/badge.svg)](https://github.com/fopina/action-docker-image-updater/actions/workflows/test.yml)
[![Test](https://github.com/fopina/action-docker-image-updater/actions/workflows/publish-image.yml/badge.svg)](https://github.com/fopina/action-docker-image-updater/actions/workflows/publish-image.yml)

# action-python-template

This action takes 2 integers as input and returns the sum of those in the output variable `sum`.

It also adds a joke to output `joke` to brighten your day.

# What's new

Please refer to the [release page](https://github.com/fopina/action-docker-image-updater/releases/latest) for the latest release notes.

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
