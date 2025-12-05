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

    def test_get_tags_need_auth(self):
        # Test the case where get_tags handles 401 and authentication
        responses = [
            mock.Mock(
                status_code=401,
                headers={
                    'WWW-Authenticate': 'Bearer realm="https://auth.example.com/token",service="registry.example.com",scope="repository:test:image:pull"'
                },
            ),
            mock.Mock(status_code=200, json=mock.Mock(return_value={'token': 'auth_token'})),
            mock.Mock(
                status_code=200,
                headers={'Link': 'rel="next" </v2/whatever/tags/list?n=x>'},
                json=mock.Mock(return_value={'tags': ['1.19']}),
            ),
            mock.Mock(status_code=200, headers={}, json=mock.Mock(return_value={'tags': ['1.20']})),
        ]
        self.req_mock.get.side_effect = responses

        tags = entrypoint.get_tags('ghcr.io', 'test/image')
        self.assertEqual(tags, ['1.19', '1.20'])
        self.assertEqual(self.req_mock.get.call_count, 4)
        self.req_mock.get.assert_has_calls(
            [
                mock.call('https://ghcr.io/v2/test/image/tags/list'),
                mock.call(
                    'https://auth.example.com/token',
                    params={'service': 'registry.example.com', 'scope': 'repository:test:image:pull'},
                ),
                mock.call('https://ghcr.io/v2/test/image/tags/list', headers={'Authorization': 'Bearer auth_token'}),
                mock.call('https://ghcr.io/v2/whatever/tags/list?n=x', headers={'Authorization': 'Bearer auth_token'}),
            ]
        )

    def test_default_no_update(self):
        self.req_mock.get.return_value.json.return_value = {'tags': ['1.19']}
        entrypoint.main(['--dry'])
        plan = self.load_plan()
        self.assertIsNone(plan)
        self.assertEqual(self.req_mock.get.call_count, 1)
        self.req_mock.get.assert_called_once_with('https://index.docker.io/v2/library/nginx/tags/list')

    def test_default_update(self):
        self.req_mock.get.return_value.json.return_value = {'tags': ['1.19', '1.20', '1.21-alpine']}
        entrypoint.main(['--dry'])
        plan = self.load_plan()
        self.assertEqual(plan, {'tests/files/docker-compose.yml': [[['nginx', '1.19'], [[[1, 20], '1.20']]]]})
        self.req_mock.get.assert_called_once()
        self.req_mock.get.assert_called_once_with('https://index.docker.io/v2/library/nginx/tags/list')

    def test_file_match(self):
        self.req_mock.get.return_value.json.return_value = {'tags': ['1.19', '1.20', '1.20-alpine']}
        entrypoint.main(['--dry', '--file-match', '**/*.yml'])
        plan = self.load_plan()
        self.assertEqual(
            plan,
            {
                'tests/files/other.yml': [[['nginx', '1.19-alpine'], [[[1, 20], '1.20-alpine']]]],
                'tests/files/docker-compose.yml': [[['nginx', '1.19'], [[[1, 20], '1.20']]]],
            },
        )
        self.assertEqual(self.req_mock.get.call_count, 3)
        self.req_mock.get.assert_has_calls(
            [
                # this comes from action.yaml :facepalm: - fix somehow? better "tag" regular expressions when matching `image:` ?
                mock.call('https://index.docker.io/v2/library/docker/tags/list'),
                mock.call('https://index.docker.io/v2/library/nginx/tags/list'),
                mock.call('https://ghcr.io/v2/gethomepage/homepage/tags/list'),
            ],
            any_order=True,
        )

    def test_custom_field(self):
        self.req_mock.get.return_value.json.return_value = {'tags': ['2.24.0-alpine', '2.25.0']}
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
        self.assertEqual(self.req_mock.get.call_count, 2)
        self.req_mock.get.assert_has_calls(
            [
                mock.call('https://index.docker.io/v2/portainer/agent/tags/list'),
                mock.call('https://index.docker.io/v2/portainer/portainer-ce/tags/list'),
            ],
            any_order=True,
        )

    def test_jsonpath(self):
        self.req_mock.get.return_value.json.return_value = {'tags': ['v3.99.0-alpine', 'v3.99.0']}
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
                ],
                'tests/files/otherchart/values-other.yaml': [
                    [['gethomepage/homepage', 'v1.6.1'], [[[3, 99, 0], 'v3.99.0']]],
                ],
            },
        )
        self.assertEqual(self.req_mock.get.call_count, 2)
        self.req_mock.get.assert_has_calls(
            [
                mock.call('https://index.docker.io/v2/library/traefik/tags/list'),
                mock.call('https://index.docker.io/v2/gethomepage/homepage/tags/list'),
            ],
            any_order=True,
        )

    def test_jsonpath_registry(self):
        self.req_mock.get.return_value.json.return_value = {'tags': ['v3.99.0-alpine', 'v3.99.0']}
        entrypoint.main(
            [
                '--dry',
                '--file-match',
                '**/values*.y*ml',
                '--image-name-jsonpath',
                'image.repository',
                '--image-tag-jsonpath',
                'image.tag',
                '--image-registry-jsonpath',
                'image.registry',
            ]
        )
        plan = self.load_plan()
        self.assertEqual(
            plan,
            {
                'tests/files/somechart/values.yaml': [
                    [['traefik', 'v3.5.3'], [[[3, 99, 0], 'v3.99.0']]],
                ],
                'tests/files/otherchart/values-other.yaml': [
                    [['gethomepage/homepage', 'v1.6.1'], [[[3, 99, 0], 'v3.99.0']]],
                ],
            },
        )
        self.assertEqual(self.req_mock.get.call_count, 2)
        self.req_mock.get.assert_has_calls(
            [
                mock.call('https://index.docker.io/v2/library/traefik/tags/list'),
                mock.call('https://ghcr.io/v2/gethomepage/homepage/tags/list'),
            ],
            any_order=True,
        )

    def test_jsonpath_tagged_image_name(self):
        self.req_mock.get.return_value.json.return_value = {'tags': ['v3.99.0-alpine', 'v3.99.0']}
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
        self.assertEqual(self.req_mock.get.call_count, 1)
        self.req_mock.get.assert_has_calls(
            [
                mock.call('https://index.docker.io/v2/library/traefik/tags/list'),
            ],
            any_order=True,
        )

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
            self.req_mock.get.return_value.json.return_value = {'tags': ['1.19', '1.20', '1.21-alpine']}
            self.assertNotIn('image: nginx:1.20', dest.read_text())
            entrypoint.main(['--file-match', 'tests/temp*/**/*.yml'])
            self.assertIn('image: nginx:1.20', dest.read_text())
            self.assertEqual(self.req_mock.get.call_count, 1)
            self.req_mock.get.assert_has_calls(
                [
                    mock.call('https://index.docker.io/v2/library/nginx/tags/list'),
                ],
                any_order=True,
            )

    def test_default_update_non_dockerio_non_dry(self):
        with self.copy_from('on-ghcr.yml') as dest:
            self.req_mock.get.return_value.json.return_value = {'tags': ['v1.7.0']}
            self.assertNotIn('image: ghcr.io/gethomepage/homepage:v1.7.0', dest.read_text())
            entrypoint.main(['--file-match', 'tests/temp*/**/*.yml'])
            self.assertIn('image: ghcr.io/gethomepage/homepage:v1.7.0', dest.read_text())
            self.assertEqual(self.req_mock.get.call_count, 1)
            self.req_mock.get.assert_has_calls(
                [
                    mock.call('https://ghcr.io/v2/gethomepage/homepage/tags/list'),
                ],
                any_order=True,
            )

    def test_custom_field_non_dry(self):
        self.req_mock.get.return_value.json.return_value = {'tags': ['2.24.0-alpine', '2.25.0']}
        extra = {
            'portainer_version': 'portainer/portainer-ce:?-alpine',
            'portainer_agent_version': 'portainer/agent:?-alpine',
        }
        with self.copy_from('ansible_playbook.yml') as dest:
            entrypoint.main(['--file-match', 'tests/temp*/**/*book.yml', '--extra', json.dumps(extra), '--repo', 'x/x'])
            self.assertRegex(dest.read_text(), r'\s+portainer_version: 2\.24\.0\b')
            self.assertEqual(self.req_mock.get.call_count, 2)
            self.req_mock.get.assert_has_calls(
                [
                    mock.call('https://index.docker.io/v2/portainer/portainer-ce/tags/list'),
                    mock.call('https://index.docker.io/v2/portainer/agent/tags/list'),
                ],
                any_order=True,
            )
            self.assertEqual(self.req_mock.post.call_count, 1)
            _p = dest.parent.name
            self.req_mock.post.assert_has_calls(
                [
                    mock.call(
                        'https://api.github.com/repos/x/x/pulls',
                        headers={'Authorization': 'token xxx'},
                        json={
                            'title': f'Update images in ansible_playbook ({_p})',
                            'head': f'autoupdater/{_p}_ansible_playbook_dadcecb51d162952c57c4a696f8c1a2e6c3e1189',
                            'base': 'main',
                            'body': '* bump portainer_version:  from 2.21.0 to 2.24.0\n* bump portainer_agent_version:  from 2.21.0 to 2.24.0',
                        },
                    ),
                ],
                any_order=True,
            )

    def test_jsonpath_non_dry(self):
        self.req_mock.get.return_value.json.return_value = {'tags': ['v3.99.0-alpine', 'v3.99.0']}
        with self.copy_from('somechart') as dest:
            entrypoint.main(
                [
                    '--repo',
                    'x/x',
                    '--file-match',
                    'tests/temp*/**/values*.y*ml',
                    '--image-name-jsonpath',
                    'image.repository',
                    '--image-tag-jsonpath',
                    'image.tag',
                ]
            )
            self.assertRegex((dest / 'values.yaml').read_text(), r'\s+tag: v3\.99\.0\b')
            self.assertEqual(self.req_mock.get.call_count, 2)
            self.req_mock.get.assert_has_calls(
                [
                    mock.call('https://index.docker.io/v2/gethomepage/homepage/tags/list'),
                    mock.call('https://index.docker.io/v2/library/traefik/tags/list'),
                ],
                any_order=True,
            )
            self.assertEqual(self.req_mock.post.call_count, 1)
            self.req_mock.post.assert_has_calls(
                [
                    mock.call(
                        'https://api.github.com/repos/x/x/pulls',
                        headers={'Authorization': 'token xxx'},
                        json={
                            'title': 'Update images in values (somechart)',
                            'head': 'autoupdater/somechart_values_60f121a82820c68761a5af8d681e38d0c1fe5a38',
                            'base': 'main',
                            'body': '* bump traefik from v3.5.3 to v3.99.0',
                        },
                    ),
                ],
                any_order=True,
            )

    def test_jsonpath_tagged_image_name_non_dry(self):
        self.req_mock.get.return_value.json.return_value = {'tags': ['v3.99.0-alpine', 'v3.99.0']}
        with self.copy_from('otherchart') as dest:
            entrypoint.main(
                [
                    '--repo',
                    'x/x',
                    '--file-match',
                    'tests/temp*/**/values*.y*ml',
                    '--image-name-jsonpath',
                    'deployment.repository',
                ]
            )
            self.assertRegex((dest / 'values.yaml').read_text(), r'\s+repository: traefik:v3\.99\.0\b')
            self.assertEqual(self.req_mock.get.call_count, 1)
            self.req_mock.get.assert_has_calls(
                [
                    mock.call('https://index.docker.io/v2/library/traefik/tags/list'),
                ],
                any_order=True,
            )
            self.assertEqual(self.req_mock.post.call_count, 1)
            self.req_mock.post.assert_has_calls(
                [
                    mock.call(
                        'https://api.github.com/repos/x/x/pulls',
                        headers={'Authorization': 'token xxx'},
                        json={
                            'title': 'Update images in values (otherchart)',
                            'head': 'autoupdater/otherchart_values_34bedd1929b2c08780876d3ac0098c99cf13b9e8',
                            'base': 'main',
                            'body': '* bump traefik:v3.5.3 from v3.5.3 to v3.99.0',
                        },
                    ),
                ],
                any_order=True,
            )
