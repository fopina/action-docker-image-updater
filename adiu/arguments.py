import argparse
import json
import os

from .cli import CLI


def build_parser():
    p = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    p.add_argument('--token', help='Github token', default=os.getenv('INPUT_TOKEN'))
    p.add_argument(
        '--dry', action='store_true', help='Dry run to only check which images would be updated - for testing'
    )
    p.add_argument('--repo', type=str, default=os.getenv('GITHUB_REPOSITORY'), help='Github project being updated')
    p.add_argument(
        '--cooldown',
        type=int,
        default=int(os.getenv('INPUT_COOLDOWN', '3')),
        help='Minimum age in days for image versions to be eligible (0 disables the cooldown)',
    )
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
        help='JSONPath to image name. If this is specified and --image-tag-jsonpath is not, tag is expected in this field, format IMAGE:TAG. Same for --image-registry-jsonpath, if not specified it is assumed to be in this field, format REPOSITORY/IMAGE:TAG and the absence of it defaults to docker.io.',
        default=os.getenv('INPUT_IMAGE-NAME-JSONPATH'),
    )
    p.add_argument(
        '--image-registry-jsonpath',
        type=str,
        help='JSONPath to image registry.',
        default=os.getenv('INPUT_IMAGE-REGISTRY-JSONPATH'),
    )
    p.add_argument(
        '--image-tag-jsonpath', type=str, help='JSONPath to image tag', default=os.getenv('INPUT_IMAGE-TAG-JSONPATH')
    )
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.cooldown < 0:
        raise ValueError('--cooldown must be zero or greater')
    extra_fields = None if not args.extra_fields else json.loads(args.extra_fields)
    c = CLI(
        args.token,
        args.repo,
        args.file_match,
        extra_fields,
        args.image_name_jsonpath,
        args.image_tag_jsonpath,
        args.image_registry_jsonpath,
        args.cooldown,
    )
    if os.getenv('INPUT_DRY', 'false') == 'true':
        args.dry = True
    if args.dry:
        return c.dry_run()
    else:
        return c.run()
