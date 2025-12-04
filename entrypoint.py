#!/usr/bin/env -S python3 -u
import argparse
import hashlib
import json
import os
import re
import subprocess
from functools import cached_property, lru_cache
from pathlib import Path

import requests


# Set the output value by writing to the outputs in the Environment File, mimicking the behavior defined here:
# https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions#setting-an-output-parameter
def set_github_action_output(output_name, output_value):
    output_file = os.getenv('GITHUB_OUTPUT')
    line = f'{output_name}={output_value}\n'

    if output_file:
        with open(output_file, 'a') as f:
            f.write(line)
    else:
        # to be able to use from terminal
        print(line, end=None)


@lru_cache
def get_tags(repository):
    r = requests.get(
        'https://auth.docker.io/token',
        params={'service': 'registry.docker.io', 'scope': f'repository:{repository}:pull'},
    )
    r.raise_for_status()
    token = r.json()['token']
    r = requests.get(f'https://index.docker.io/v2/{repository}/tags/list', headers={'Authorization': f'Bearer {token}'})
    r.raise_for_status()
    return r.json()['tags']


class CLI:
    def __init__(self, token, repo, file_match, extra_fields, image_jsonpath, tag_jsonpath, repository_jsonpath):
        self._token = token
        self._repo = repo
        self._glob = file_match
        self._extra_fields: dict[str, tuple[re.Pattern, str]] = {
            k: (re.compile(rf"""\s*({k}\s*:\s*)(.*)"""), v) for k, v in (extra_fields or {}).items()
        }
        self._re_image = re.compile(r"""\s*image: (&[a-z\-]+ )?["']?(.+?):(.+)["']?""")
        self._re_tag = re.compile(r'(.*?)(\d+([\.-]\d+)*)(.*)')
        self._image_jsonpath = image_jsonpath
        self._tag_jsonpath = tag_jsonpath
        self._repository_jsonpath = repository_jsonpath
        # solve container issue
        if 'GITHUB_OUTPUT' in os.environ:
            subprocess.check_call(['git', 'config', '--global', '--add', 'safe.directory', '/github/workspace'])
        self._base_revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
        self.repo_dir = Path('.').absolute()

    def setup_git(self):
        subprocess.check_call('git config user.email updater@devnull.localhost', shell=True)
        subprocess.check_call('git config user.name Updater', shell=True)

    @cached_property
    def branches(self):
        subprocess.check_call(['git', 'fetch'])
        return subprocess.check_output(['git', 'branch', '-a'], text=True)

    def version_tuple(self, version_string):
        return tuple(map(int, version_string.replace('-', '.').split('.')))

    def _proc_stack_extra_fields(self, stack: Path):
        if not self._extra_fields:
            return []

        data = stack.read_text()
        r = []
        for _, (field_re, field_template) in self._extra_fields.items():
            for raw_field, m in field_re.findall(data):
                image = field_template.replace('?', m).split(':', 1)
                updates = self.check_image(stack, image[0], image[1])
                if updates is None:
                    continue
                # fix updates for this "custom field", strip template-added text to tag
                tag_template = field_template.split(':')[1].split('?', 1)
                p1, p2 = len(tag_template[0]), len(tag_template[1])
                filtered_updates = [(x1, x2[p1:-p2]) for x1, x2 in updates]
                r.append(((raw_field, m), filtered_updates))
        return r

    def _proc_stack_image(self, stack: Path):
        s = stack.read_text()
        r = []
        for image in self._re_image.findall(s):
            # trim anchor
            image = image[1:]

            disabled = re.findall(r'# autoupdater: disable\s+[^\n]*' + image[0], s, re.DOTALL)
            if disabled:
                print(f'::notice file={stack.relative_to(self.repo_dir)}::Image {image[0]} with autoupdate disabled')
                continue

            updates = self.check_image(stack, image[0], image[1])
            if updates is None:
                continue
            r.append((image, updates))
        return r

    def _proc_stack_jsonpath(self, stack: Path):
        if not self._image_jsonpath:
            return []
        r = []
        s = stack.read_text()
        for image in self._re_image.findall(s):
            # trim anchor
            image = image[1:]

            disabled = re.findall(r'# autoupdater: disable\s+[^\n]*' + image[0], s, re.DOTALL)
            if disabled:
                print(f'::notice file={stack.relative_to(self.repo_dir)}::Image {image[0]} with autoupdate disabled')
                continue

            updates = self.check_image(stack, image[0], image[1])
            if updates is None:
                continue
            r.append((image, updates))
        return r

    def proc_stack(self, stack: Path):
        """
        Processes a stack file (e.g., Docker Compose YAML) to identify Docker images
        with available updates.

        This method scans the specified file for Docker image references in standard
        "image:" fields and any configured extra fields. For each image found, it checks
        if there are newer versions available based on semantic versioning.

        Args:
            stack (Path): Path to the stack file to process (e.g., docker-compose.yml)

        Returns:
            list[tuple[tuple[str, str], list[tuple[tuple, str]]]]: A list of update tuples.
                Each tuple contains:
                - (original_image, current_tag): The original image name and tag found
                - newer_tags: List of (version_tuple, new_tag) tuples for available updates,
                  sorted by version. Empty if no updates available.

        Notes:
            - Images with "autoupdater: disable" comments are skipped
            - Only Docker Hub images are supported (non-hub registries are ignored)
            - Tags must follow semantic versioning format (MAJOR.MINOR.PATCH)
            - Returns an empty list if no images or no updates are found
        """
        r = self._proc_stack_extra_fields(stack)
        r.extend(self._proc_stack_image(stack))
        r.extend(self._proc_stack_jsonpath(stack))
        return r

    def check_image(self, stack, image, tag):
        # check if no explicit registry is specified and assume default is dockerhub (as it's the only supported)
        # same logic as in
        # https://github.com/moby/moby/blob/f0cec02a403496e2b1dd1aaf12b2530922e210db/registry/search.go#L144
        if image.count('/') > 1:
            part1 = image.split('/', 1)[0]
            # TODO: support non-hub registries
            if '.' in part1 or ':' in part1 or part1 == 'localhost':
                print(f'::notice file={stack.relative_to(self.repo_dir)}::Image {image} using non-supported registry')
                return

        m = self._re_tag.match(tag)
        if not m:
            print(f'::notice file={stack.relative_to(self.repo_dir)}::Image {image} with non-semver tag {tag}')
            return
        current_version = self.version_tuple(m.group(2))
        pattern = re.compile(rf'^{re.escape(m.group(1))}(\d+([\.-]\d+)*){re.escape(m.group(4))}$')
        repository = image
        if '/' not in image:
            repository = f'library/{repository}'
        tags = get_tags(repository)
        newer_tags = []
        for tag in tags:
            mp = pattern.match(tag)
            if mp:
                new_version = self.version_tuple(mp.group(1))
                if len(current_version) == len(new_version) and new_version > current_version:
                    newer_tags.append((new_version, tag))
        newer_tags.sort()
        return newer_tags

    def create_branch_and_mr(self, stack, branch, body=None):
        title = f'Update images in {stack.stem}'
        subprocess.check_call(['git', 'checkout', '-b', branch])
        subprocess.check_call(['git', 'commit', '-a', '-m', title])
        subprocess.check_call(['git', 'push', 'origin', branch])

        if body is None:
            body = 'Auto-generated pull request.'

        r = requests.post(
            f'https://api.github.com/repos/{self._repo}/pulls',
            headers={
                'Authorization': f'token {self._token}',
            },
            json={
                'title': title,
                'head': branch,
                'base': 'main',
                'body': body,
            },
        )
        r.raise_for_status()

    def update_stack(self, stack, data):
        s = stack.read_text()
        cksum = []
        for original, newer_tags in data:
            if not newer_tags:
                continue
            newest = newer_tags[-1]
            if ':' in original[0]:
                # because custom_fields brings the ":" already
                s = s.replace(f'{original[0]}{original[1]}', f'{original[0]}{newest[1]}')
            else:
                s = s.replace(f'{original[0]}:{original[1]}', f'{original[0]}:{newest[1]}')
            cksum.append(f'* bump {original[0]} from {original[1]} to {newest[1]}')
        if not cksum:
            return False, None
        cksumhex = hashlib.sha1(''.join(cksum).encode()).hexdigest()
        branch = f'autoupdater/{stack.stem}_{cksumhex}'
        if f'{branch}\n' in self.branches:
            print(f'Branch {branch} already exists, skipping')
            return False, branch
        stack.write_text(s)
        self.create_branch_and_mr(stack, branch, body='\n'.join(cksum))
        subprocess.check_call(['git', 'checkout', self._base_revision])
        return True, branch

    def cleanup_branches(self, stack, keep=[]):
        prefix = f'autoupdater/{stack.stem}_'
        elen = len(prefix) + 40
        for b in self.branches.splitlines():
            existing_branch = b.strip().split('/', 2)[-1]
            if existing_branch.startswith(prefix) and len(existing_branch) == elen:
                if existing_branch not in keep:
                    print(f'::warning file={stack.relative_to(self.repo_dir)}::cleaning up branch {existing_branch}')
                    subprocess.check_call(['git', 'push', 'origin', f':{existing_branch}'])

    def run(self):
        self.setup_git()
        for stack in self.repo_dir.glob(self._glob):
            r = self.proc_stack(stack)
            if r:
                updated, branch = self.update_stack(stack, r)
                if updated:
                    print(f'::warning file={stack.relative_to(self.repo_dir)}::Bumped')
                if branch:
                    self.cleanup_branches(stack, keep=[branch])

    def dry_run(self):
        plan = {}
        for stack in self.repo_dir.glob(self._glob):
            r = self.proc_stack(stack)
            done_header = False
            any_update = False
            for image, nt in r:
                if nt:
                    any_update = True
                    if not done_header:
                        print(f'== {stack.name}')
                        done_header = True
                    print(image, nt)
            if any_update:
                plan[str(stack.relative_to(self.repo_dir))] = r
        if plan:
            set_github_action_output('plan', json.dumps(plan))


def build_parser():
    p = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    p.add_argument('--token', help='Github token', default=os.getenv('INPUT_TOKEN'))
    p.add_argument(
        '--dry', action='store_true', help='Dry run to only check which images would be updated - for testing'
    )
    p.add_argument('--repo', type=str, default=os.getenv('GITHUB_REPOSITORY'), help='Github project being updated')
    p.add_argument(
        '--file-match',
        type=str,
        default=os.getenv('INPUT_FILE-MATCH', '**/docker-compose*.y*ml'),
        help='Glob to match compose files',
    )
    p.add_argument(
        '--extra-fields', type=str, default=os.getenv('INPUT_EXTRA-FIELDS'), help='Extra fields to be checked - mapping'
    )
    p.add_argument(
        '--image-name-jsonpath',
        type=str,
        help='JSONPath to image name. If this is specified and --image-tag-jsonpath is not, tag is expected in this field, format IMAGE:TAG. Same for --image-repository-jsonpath, if not specified it is assumed to be in this field, format REPOSITORY/IMAGE:TAG and the absence of it defaults to docker.io.',
        default=os.getenv('INPUT_IMAGE-NAME-JSONPATH'),
    )
    p.add_argument(
        '--image-repository-jsonpath',
        type=str,
        help='JSONPath to image repository hostname.',
        default=os.getenv('INPUT_IMAGE-REPOSITORY-JSONPATH'),
    )
    p.add_argument(
        '--image-tag-jsonpath', type=str, help='JSONPath to image tag', default=os.getenv('INPUT_IMAGE-TAG-JSONPATH')
    )
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    extra_fields = None if not args.extra_fields else json.loads(args.extra_fields)
    c = CLI(args.token, args.repo, args.file_match, extra_fields, args.image_name_jsonpath, args.image_tag_jsonpath, args.image_repository_jsonpath)
    if os.getenv('INPUT_DRY', 'false') == 'true':
        args.dry = True
    if args.dry:
        c.dry_run()
    else:
        c.run()


if __name__ == '__main__':
    main()
