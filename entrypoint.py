#!/usr/bin/env -S python3 -u
"""Compatibility entrypoint retained for GitHub Actions and existing imports."""

import json
import os
import subprocess

import requests

from adiu import (
    CLI,
    MAX_PR_BODY_LENGTH,
    MAX_RELEASE_NOTE_LINES_PER_IMAGE,
    REGISTRY_TIMESTAMP_FIELDS,
    ImageReference,
    build_parser,
    get_tags,
    main,
    set_github_action_output,
)
from adiu.cli import _default_json_serializer

__all__ = [
    'CLI',
    'ImageReference',
    'MAX_PR_BODY_LENGTH',
    'MAX_RELEASE_NOTE_LINES_PER_IMAGE',
    'REGISTRY_TIMESTAMP_FIELDS',
    '_default_json_serializer',
    'build_parser',
    'get_tags',
    'json',
    'main',
    'os',
    'requests',
    'set_github_action_output',
    'subprocess',
]

if __name__ == '__main__':
    exit(main() or 0)
