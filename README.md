[![Test](https://github.com/fopina/action-docker-image-updater/actions/workflows/test.yml/badge.svg)](https://github.com/fopina/action-docker-image-updater/actions/workflows/test.yml)
[![Test](https://github.com/fopina/action-docker-image-updater/actions/workflows/publish-image.yml/badge.svg)](https://github.com/fopina/action-docker-image-updater/actions/workflows/publish-image.yml)

# action-docker-image-updater

This action takes 2 integers as input and returns the sum of those in the output variable `sum`.

It also adds a joke to output `joke` to brighten your day.

> **Note**  
> [renovatebot](https://github.com/renovatebot/github-action) looks like the best option to do this, I recommend it over this action.  
> I only keep it as I did before finding out about it and it has some specific behavior I need.

# What's new

Please refer to the [release page](https://github.com/fopina/action-docker-image-updater/releases/latest) for the latest release notes.

# Usage

See [action.yml](action.yml)

# Scenarios

- [Check for image updates](#check-for-image-updates)
- [Dry run](#dry-run)

## Check for image updates

```yaml
# also need to enable `Allow GitHub Actions to create and approve pull requests`
# in `Settings` -> `Actions` -> `General` (on top of these permissions)
permissions:
  contents: write
  pull-requests: write

- uses: fopina/action-docker-image-updater@v1
  with:
    token: "${{ github.token }}"
```

## Dry run

```yaml
# also need to enable `Allow GitHub Actions to create and approve pull requests`
# in `Settings` -> `Actions` -> `General` (on top of these permissions)
permissions:
  contents: write
  pull-requests: write

- uses: fopina/action-docker-image-updater@v1
  with:
    token: "${{ github.token }}"
    dry: 'true'
```
