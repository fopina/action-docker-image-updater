import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import entrypoint


class Test(unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        # backup environment
        self._env = {**os.environ}
        self.out_file = Path(tempfile.NamedTemporaryFile(delete=False).name)
        os.environ.update(
            {
                'GITHUB_OUTPUT': str(self.out_file),
                'INPUT_TOKEN': 'xxx',
                'INPUT_DRY': 'true',
            }
        )
        self._req_patch = mock.patch('entrypoint.requests')
        self.req_mock = self._req_patch.start()
        entrypoint.get_tags.cache_clear()

    def tearDown(self) -> None:
        os.environ = self._env
        self.out_file.unlink()
        self._req_patch.stop()

    def load_plan(self):
        data = self.out_file.read_text().strip()
        if not data:
            return None
        self.assertEqual(data[:5], 'plan=')
        return json.loads(data[5:])

    def test_default_no_update(self):
        self.req_mock.get.return_value.json.return_value = {'token': '123', 'tags': ['1.19']}
        entrypoint.main(['--token', 'xxx'])
        plan = self.load_plan()
        self.assertIsNone(plan)

    def test_default_update(self):
        self.req_mock.get.return_value.json.return_value = {'token': '123', 'tags': ['1.19', '1.20', '1.21-alpine']}
        entrypoint.main(['--token', 'xxx'])
        plan = self.load_plan()
        self.assertEqual(plan, {'tests/files/docker-compose.yml': [[['nginx', '1.19'], [[[1, 20], '1.20']]]]})

    def test_file_match(self):
        self.req_mock.get.return_value.json.return_value = {'token': '123', 'tags': ['1.19', '1.20', '1.20-alpine']}
        entrypoint.main(['--token', 'xxx', '--file-match', '**/*.yml'])
        plan = self.load_plan()
        self.assertEqual(
            plan,
            {
                'tests/files/other.yml': [[['nginx', '1.19-alpine'], [[[1, 20], '1.20-alpine']]]],
                'tests/files/docker-compose.yml': [[['nginx', '1.19'], [[[1, 20], '1.20']]]],
            },
        )

    def test_custom_field(self):
        self.req_mock.get.return_value.json.return_value = {'token': '123', 'tags': ['2.24.0-alpine', '2.25.0']}
        extra = {
            'portainer_version': 'portainer/portainer-ce:?-alpine',
            'portainer_agent_version': 'portainer/agent:?-alpine',
        }
        entrypoint.main(['--token', 'xxx', '--file-match', '**/*book.yml', '--extra', json.dumps(extra)])
        plan = self.load_plan()
        self.assertEqual(
            plan,
            {
                'tests/files/ansible_playbook.yml': [
                    ['portainer/portainer-ce', [[[2, 24, 0], '2.24.0-alpine']]],
                    ['portainer/agent', [[[2, 24, 0], '2.24.0-alpine']]],
                ]
            },
        )
