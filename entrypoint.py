#!/usr/bin/env -S python3 -u
"""Compatibility entrypoint retained for GitHub Actions and existing imports."""

import json
import os
import subprocess

import requests

from adiu import (
    CLI,
    ImageReference,
    MAX_PR_BODY_LENGTH,
    MAX_RELEASE_NOTE_LINES_PER_IMAGE,
    REGISTRY_TIMESTAMP_FIELDS,
    build_parser,
    get_tags,
    main,
    set_github_action_output,
)
from adiu.cli import _default_json_serializer

if __name__ == '__main__':
    exit(main() or 0)
