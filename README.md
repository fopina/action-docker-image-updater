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

- [Check docker-compose for image updates](#check-docker-compose-for-image-updates)
- [Check any yaml file for image updates](#check-any-yaml-file-for-image-updates)
- [Check any yaml file for image updates](#check-custom-fields-for-mapped-image-updates)
- [Dry run](#dry-run)

## Check docker-compose for image updates

This will look for `docker-compose.ya?ml` files in the repository and check any `image:` lines for updates.  
For each stack found having updates, a PR is created.

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

## Check any yaml file for image updates

This will look for any `*.yml` files in the repository and check any `image:` lines for updates.  
For each stack found having updates, a PR is created.

```yaml
# also need to enable `Allow GitHub Actions to create and approve pull requests`
# in `Settings` -> `Actions` -> `General` (on top of these permissions)
permissions:
  contents: write
  pull-requests: write

- uses: fopina/action-docker-image-updater@v1
  with:
    token: "${{ github.token }}"
    file-match: '**/*.y*ml'
```

## Check custom fields for mapped image updates

This will look for any `*.y*ml` files in the repository and check `image:` lines for updates.  
On top of that, it will also look for lines with `portainer_version:` and `portainer_agent_version:` and use the values of those attributes as the version of the mapped version. Then it checks for updates of that computed image name.

For this example, `portainer_version: 2.21.0` in a matched YAML file will check for updates against `portainer/portainer-ce:2.21.0-alpine` (`?` is replaced with the version value).

For each stack found having updates, a PR is created.

```yaml
# also need to enable `Allow GitHub Actions to create and approve pull requests`
# in `Settings` -> `Actions` -> `General` (on top of these permissions)
permissions:
  contents: write
  pull-requests: write

- uses: fopina/action-docker-image-updater@v1
  with:
    token: "${{ github.token }}"
    file-match: '**/*.y*ml'
    extra-fields: >
      {
        "portainer_version": "portainer/portainer-ce:?-alpine",
        "portainer_agent_version": "portainer/agent:?-alpine"
      }
```

## Dry run

Capture the plan without actually creating any branch or pull request

```yaml
- uses: fopina/action-docker-image-updater@v1
  id: updater
  with:
    token: "${{ github.token }}"
    dry: 'true'

- name: print out plan
  env:
    PLAN: ${{ steps.updater.outputs.plan }}
  run:
    echo "$PLAN"
```
