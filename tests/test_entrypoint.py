import json
import os
import shutil
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
        # Still makes API calls to check available tags, even when no updates are found
        self.assertEqual(self.req_mock.get.call_count, 2)  # auth + tags
        self.req_mock.get.assert_has_calls(
            [
                mock.call(
                    'https://auth.docker.io/token',
                    params={'service': 'registry.docker.io', 'scope': 'repository:library/nginx:pull'},
                ),
                mock.call(
                    'https://index.docker.io/v2/library/nginx/tags/list', headers={'Authorization': 'Bearer 123'}
                ),
            ],
            any_order=True,
        )

    def test_default_update(self):
        self.req_mock.get.return_value.json.return_value = {'token': '123', 'tags': ['1.19', '1.20', '1.21-alpine']}
        entrypoint.main(['--dry'])
        plan = self.load_plan()
        self.assertEqual(plan, {'tests/files/docker-compose.yml': [[['nginx', '1.19'], [[[1, 20], '1.20']]]]})
        # Should make API calls to check nginx tags
        self.req_mock.get.assert_called()
        self.assertEqual(self.req_mock.get.call_count, 2)  # auth + tags

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
        # Should make API calls to check nginx tags
        self.req_mock.get.assert_called()
        self.assertEqual(self.req_mock.get.call_count, 4)  # auth + tags for 2 files

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
        # Should make API calls to check portainer tags
        self.req_mock.get.assert_called()
        self.assertEqual(self.req_mock.get.call_count, 4)  # auth + tags for 2 files

    def test_jsonpath(self):
        self.req_mock.get.return_value.json.return_value = {'token': '123', 'tags': ['v3.99.0-alpine', 'v3.99.0']}
        entrypoint.main(
            [
                '--dry',
                '--file-match',
                '**/values*.y*ml',
                '--image-name-jsonpath',
                'image.repository',
                '--image-tag-jsonpath',
                'image.tag',
            ]
        )
        plan = self.load_plan()
        self.assertEqual(
            plan,
            {
                'tests/files/somechart/values.yaml': [
                    [['traefik', 'v3.5.3'], [[[3, 99, 0], 'v3.99.0']]],
                ]
            },
        )
        # Should make API calls to check traefik tags
        self.req_mock.get.assert_called()
        self.assertEqual(self.req_mock.get.call_count, 2)  # auth + tags

    def test_jsonpath_tagged_image_name(self):
        self.req_mock.get.return_value.json.return_value = {'token': '123', 'tags': ['v3.99.0-alpine', 'v3.99.0']}
        entrypoint.main(
            [
                '--dry',
                '--file-match',
                '**/values*.y*ml',
                '--image-name-jsonpath',
                'deployment.repository',
            ]
        )
        plan = self.load_plan()
        self.assertEqual(
            plan,
            {
                'tests/files/otherchart/values.yaml': [
                    [['traefik:v3.5.3', 'v3.5.3'], [[[3, 99, 0], 'v3.99.0']]],
                ]
            },
        )
        # Should make API calls to check traefik tags
        self.req_mock.get.assert_called()
        self.assertEqual(self.req_mock.get.call_count, 2)  # auth + tags

    @contextmanager
    def copy_from(self, path):
        original = Path(__file__).parent / 'files' / path
        with tempfile.TemporaryDirectory(dir=original.parent.parent, prefix='temp') as tmpdir:
            dest = Path(tmpdir) / original.name
            if original.is_file():
                shutil.copy2(original, dest)
            elif original.is_dir():
                shutil.copytree(original, dest)
            else:
                raise ValueError(f'Path {original} is neither a file nor directory')
            yield dest

    def test_default_update_non_dry(self):
        with self.copy_from('docker-compose.yml') as dest:
            self.req_mock.get.return_value.json.return_value = {'token': '123', 'tags': ['1.19', '1.20', '1.21-alpine']}
            self.assertNotIn('image: nginx:1.20', dest.read_text())
            entrypoint.main(['--file-match', 'tests/temp*/**/*.yml'])
            self.assertIn('image: nginx:1.20', dest.read_text())
            # Should make API calls to check nginx tags during update
            self.req_mock.get.assert_called()
            self.assertGreaterEqual(self.req_mock.get.call_count, 2)  # auth + tags

    def test_custom_field_non_dry(self):
        self.req_mock.get.return_value.json.return_value = {'token': '123', 'tags': ['2.24.0-alpine', '2.25.0']}
        extra = {
            'portainer_version': 'portainer/portainer-ce:?-alpine',
            'portainer_agent_version': 'portainer/agent:?-alpine',
        }
        with self.copy_from('ansible_playbook.yml') as dest:
            entrypoint.main(['--file-match', 'tests/temp*/**/*book.yml', '--extra', json.dumps(extra)])
            self.assertRegex(dest.read_text(), r'\s+portainer_version: 2\.24\.0\b')
            # Should make API calls to check portainer tags during update
            self.req_mock.get.assert_called()
            self.assertGreaterEqual(self.req_mock.get.call_count, 2)  # auth + tags

    def test_jsonpath_non_dry(self):
        self.req_mock.get.return_value.json.return_value = {'token': '123', 'tags': ['v3.99.0-alpine', 'v3.99.0']}
        with self.copy_from('somechart') as dest:
            entrypoint.main(
                [
                    '--file-match',
                    'tests/temp*/**/values*.y*ml',
                    '--image-name-jsonpath',
                    'image.repository',
                    '--image-tag-jsonpath',
                    'image.tag',
                ]
            )
            self.assertRegex((dest / 'values.yaml').read_text(), r'\s+tag: v3\.99\.0\b')
            # Should make API calls to check traefik tags during update
            self.req_mock.get.assert_called()
            self.assertGreaterEqual(self.req_mock.get.call_count, 2)  # auth + tags

    def test_jsonpath_tagged_image_name_non_dry(self):
        self.req_mock.get.return_value.json.return_value = {'token': '123', 'tags': ['v3.99.0-alpine', 'v3.99.0']}
        with self.copy_from('otherchart') as dest:
            entrypoint.main(
                [
                    '--file-match',
                    'tests/temp*/**/values*.y*ml',
                    '--image-name-jsonpath',
                    'deployment.repository',
                ]
            )
            self.assertRegex((dest / 'values.yaml').read_text(), r'\s+repository: traefik:v3\.99\.0\b')
            # Should make API calls to check traefik tags during update
            self.req_mock.get.assert_called()
            self.assertGreaterEqual(self.req_mock.get.call_count, 2)  # auth + tags
