import json
import os
import tempfile
import unittest
from contextlib import contextmanager
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
            }
        )
        self._req_patch = mock.patch('entrypoint.requests')
        self.req_mock = self._req_patch.start()
        self._process_patch = mock.patch('entrypoint.subprocess')
        self.sp_mock = self._process_patch.start()
        entrypoint.get_tags.cache_clear()

    def tearDown(self) -> None:
        os.environ = self._env
        self.out_file.unlink()
        self._req_patch.stop()
        self._process_patch.stop()

    def load_plan(self):
        data = self.out_file.read_text().strip()
        if not data:
            return None
        self.assertEqual(data[:5], 'plan=')
        return json.loads(data[5:])

    def test_default_no_update(self):
        self.req_mock.get.return_value.json.return_value = {'token': '123', 'tags': ['1.19']}
        entrypoint.main(['--dry'])
        plan = self.load_plan()
        self.assertIsNone(plan)

    def test_default_update(self):
        self.req_mock.get.return_value.json.return_value = {'token': '123', 'tags': ['1.19', '1.20', '1.21-alpine']}
        entrypoint.main(['--dry'])
        plan = self.load_plan()
        self.assertEqual(plan, {'tests/files/docker-compose.yml': [[['nginx', '1.19'], [[[1, 20], '1.20']]]]})

    def test_file_match(self):
        self.req_mock.get.return_value.json.return_value = {'token': '123', 'tags': ['1.19', '1.20', '1.20-alpine']}
        entrypoint.main(['--dry', '--file-match', '**/*.yml'])
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
        entrypoint.main(['--dry', '--file-match', '**/*book.yml', '--extra', json.dumps(extra)])
        plan = self.load_plan()
        self.assertEqual(
            plan,
            {
                'tests/files/ansible_playbook.yml': [
                    [['portainer_version: ', '2.21.0'], [[[2, 24, 0], '2.24.0']]],
                    [['portainer_agent_version: ', '2.21.0'], [[[2, 24, 0], '2.24.0']]],
                ]
            },
        )

    @contextmanager
    def copy_from(self, filename):
        original = Path(__file__).parent / 'files' / filename
        with tempfile.TemporaryDirectory(dir=original.parent.parent, prefix='temp') as tmpdir:
            dest = Path(tmpdir) / original.name
            dest.write_text(original.read_text())
            yield dest

    def test_default_update_non_dry(self):
        with self.copy_from('docker-compose.yml') as dest:
            self.req_mock.get.return_value.json.return_value = {'token': '123', 'tags': ['1.19', '1.20', '1.21-alpine']}
            self.assertNotIn('image: nginx:1.20', dest.read_text())
            entrypoint.main(['--file-match', 'tests/temp*/**/*.yml'])
            self.assertIn('image: nginx:1.20', dest.read_text())

    def test_custom_field_non_dry(self):
        self.req_mock.get.return_value.json.return_value = {'token': '123', 'tags': ['2.24.0-alpine', '2.25.0']}
        extra = {
            'portainer_version': 'portainer/portainer-ce:?-alpine',
            'portainer_agent_version': 'portainer/agent:?-alpine',
        }
        with self.copy_from('ansible_playbook.yml') as dest:
            entrypoint.main(['--file-match', 'tests/temp*/**/*book.yml', '--extra', json.dumps(extra)])
            self.assertRegexpMatches(dest.read_text(), r'\s+portainer_version: 2\.24\.0\b')
