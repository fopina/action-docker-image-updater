#!/usr/bin/env -S python3 -u
import argparse
import hashlib
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


REPO = 'fopina/home-services'


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
    def __init__(self, token):
        self._token = token
        self._re_image = re.compile(r"""\s*image: (&[a-z\-]+ )?["']?(.+?):(.+)["']?""")
        self._re_tag = re.compile(r'(.*?)(\d+([\.-]\d+)*)(.*)')
        self._base_revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
        self.repo_dir = Path(__file__).absolute().parent.parent

    def setup_git(self):
        subprocess.check_call('git config user.email updater@devnull.localhost', shell=True)
        subprocess.check_call('git config user.name Updater', shell=True)

    @cached_property
    def branches(self):
        subprocess.check_call(['git', 'fetch'])
        return subprocess.check_output(['git', 'branch', '-a'], text=True)

    def version_tuple(self, version_string):
        return tuple(map(int, version_string.replace('-', '.').split('.')))

    def proc_stack(self, stack):
        s = stack.read_text()
        r = []
        for image in self._re_image.findall(s):
            # trim anchor
            image = image[1:]
            if image[0].count('/') > 1:
                # TODO: support non-hub registries
                continue

            disabled = re.findall(r'# autoupdater: disable\s+[^\n]*' + image[0], s, re.DOTALL)
            if disabled:
                print(f'::notice file={stack.relative_to(self.repo_dir)}::Image {image[0]} with autoupdate disabled')
                continue

            m = self._re_tag.match(image[1])
            if not m:
                print(
                    f'::notice file={stack.relative_to(self.repo_dir)}::Image {image[0]} with non-semver tag {image[1]}'
                )
                continue
            current_version = self.version_tuple(m.group(2))
            pattern = re.compile(rf'^{re.escape(m.group(1))}(\d+([\.-]\d+)*){re.escape(m.group(4))}$')
            repository = image[0]
            if '/' not in image[0]:
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
            r.append((image, newer_tags))
        return r

    def create_branch_and_mr(self, stack, branch, body=None):
        title = f'Update images in {stack.stem}'
        subprocess.check_call(['git', 'checkout', '-b', branch])
        subprocess.check_call(['git', 'commit', '-a', '-m', title])
        subprocess.check_call(['git', 'push', 'origin', branch])

        if body is None:
            body = 'Auto-generated pull request.'

        r = requests.post(
            f'https://api.github.com/repos/{REPO}/pulls',
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
        for stack in self.repo_dir.glob('*.yml'):
            r = self.proc_stack(stack)
            if r:
                updated, branch = self.update_stack(stack, r)
                if updated:
                    print(f'::warning file={stack.relative_to(self.repo_dir)}::Bumped')
                if branch:
                    self.cleanup_branches(stack, keep=[branch])

    def dry_run(self):
        for stack in self.repo_dir.glob('*.yml'):
            r = self.proc_stack(stack)
            done_header = False
            for image, nt in r:
                if nt:
                    if not done_header:
                        print(f'== {stack.name}')
                        done_header = True
                    print(image, nt)


def build_parser():
    p = argparse.ArgumentParser()
    p.add_argument('token', help='Github token', dfault=os.getenv('INPUT_TOKEN'))
    p.add_argument(
        '--dry', action='store_true', help='Dry run to only check which images would be updated - for testing'
    )
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    c = CLI(args.token)
    if os.getenv('INPUT_DRY', 'false') == 'true':
        args.dry = True
    if args.dry:
        c.dry_run()
    else:
        c.run()


if __name__ == '__main__':
    main()
