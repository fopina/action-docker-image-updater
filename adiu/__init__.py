"""Implementation package for the action's command line entrypoint."""

from .arguments import build_parser, main
from .cli import CLI, ImageReference, _default_json_serializer
from .constants import MAX_PR_BODY_LENGTH, MAX_RELEASE_NOTE_LINES_PER_IMAGE, REGISTRY_TIMESTAMP_FIELDS
from .output import set_github_action_output
from .registry import get_tags

__all__ = [
    'CLI', 'ImageReference', 'MAX_PR_BODY_LENGTH', 'MAX_RELEASE_NOTE_LINES_PER_IMAGE',
    'REGISTRY_TIMESTAMP_FIELDS', 'build_parser', 'get_tags', 'main',
    'set_github_action_output',
]
