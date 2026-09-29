[![Test](https://github.com/fopina/action-docker-image-updater/actions/workflows/test.yml/badge.svg)](https://github.com/fopina/action-docker-image-updater/actions/workflows/test.yml)
[![Test](https://github.com/fopina/action-docker-image-updater/actions/workflows/publish-image.yml/badge.svg)](https://github.com/fopina/action-docker-image-updater/actions/workflows/publish-image.yml)

# action-docker-image-updater

This action updates Docker image versions inside docker-compose and other YAML files by checking for newer versions available in container registries.

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
- [Check Helm values or other YAML files with JSONPath](#check-helm-values-or-other-yaml-files-with-jsonpath)
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

## Check Helm values or other YAML files with JSONPath

This will look for files matching the pattern and use JSONPath expressions to find image names and tags in YAML files.  
This is particularly useful for Helm values files where the image information isn't in the standard `image: imagename:tag` format.

For example, to check a Helm values.yaml file with this structure:
```yaml
# some path like: mytraefik-chart/values.yaml
image:
  repository: traefik
  tag: v3.5.3
```

For each stack found having updates, a PR is created.

```yaml
permissions:
  contents: write
  pull-requests: write

- uses: fopina/action-docker-image-updater@v1
  with:
    token: "${{ github.token }}"
    file-match: '**/values*.y*ml'
    image-name-jsonpath: 'image.repository'
    image-tag-jsonpath: 'image.tag'
```

## Restrict an image's tags with a regexp

Place a `# autoupdater: tag-regex=...` comment immediately above the field containing
its tag, at the same indentation. For example, to exclude old calendar-versioned
Transmission tags such as `2021.11.18` while allowing updates from `4.1.1`:

```yaml
deployment:
  image:
    repository: linuxserver/transmission
    # autoupdater: tag-regex=\d\.\d+\.\d+
    tag: 4.1.1
```

Use `image-name-jsonpath: deployment.image.repository` and
`image-tag-jsonpath: deployment.image.tag` for this layout. The comment belongs above
`tag`, not `repository` or the parent `image` mapping.

For standard image declarations (or a combined image/tag selected by JSONPath):

```yaml
services:
  transmission:
    # autoupdater: tag-regex=\d\.\d+\.\d+
    image: linuxserver/transmission:4.1.1
```

For mapped `extra-fields`, put the comment above the mapped field. The expression
matches the **complete registry tag**, including any prefix/suffix added by the
mapping. With `"app_version": "example/app:v?-alpine"`:

```yaml
# autoupdater: tag-regex=v\d\.\d+\.\d+-alpine
app_version: 4.1.1
```

Expressions use Python regexp syntax and must match the entire tag; anchors are
optional. Escape literal dots as `\.`. Do not wrap the expression in quotes or
`/` delimiters. The one-digit major pattern above also excludes future majors
`10` and above; use `4\.\d+\.\d+` if you want to stay specifically on major 4.

The regexp is an additional filter, not a version parser. Existing version
extraction and ordering still apply: the first numeric run (components separated
by dots or hyphens) is compared as a tuple of integers. Candidates must retain the
current tag's prefix, suffix, and number of version components. Thus
`v4.1.10-python3.12` sorts after `v4.1.2-python3.12`, while the `python3.12` suffix
stays fixed. Date tags such as `2024-01-01` keep their numeric ordering; tags with
no numeric version remain skipped. Capture groups do not affect extraction.

Comments apply only to the next declaration. A contiguous comment block is
supported; a blank line, another field, or different indentation ends its scope.
Use separate lines for declarations; inline pragma comments and pragmas on parent
mappings are not supported. Comments are preserved during updates. Without a
regexp, tag selection is unchanged.

Invalid expressions, duplicate regexp directives, and a current tag that doesn't
match cause an error and skip the file, with a nonzero exit status (including dry
runs). `# autoupdater: disable` in the same comment block takes precedence. The
legacy `# autoupdater: disable IMAGE_NAME` form continues to disable that image
throughout the file.

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
