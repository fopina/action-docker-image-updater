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

    def test_default_no_update(self):
        self.req_mock.get.return_value.json.return_value = {'token': '123', 'tags': ['1.19']}
        entrypoint.main(['--token', 'xxx'])
        output = self.out_file.read_text().strip()
        self.assertEqual(output, '')

    def test_default_update(self):
        self.req_mock.get.return_value.json.return_value = {'token': '123', 'tags': ['1.19', '1.20']}
        entrypoint.main(['--token', 'xxx'])
        output = self.out_file.read_text().strip()
        self.assertEqual(output, """tests/files/docker-compose.yml=[[["nginx", "1.19"], [[[1, 20], "1.20"]]]]""")

    def test_file_match(self):
        self.req_mock.get.return_value.json.return_value = {'token': '123', 'tags': ['1.19', '1.20']}
        entrypoint.main(['--token', 'xxx', '--file-match', '**/*.yml'])
        output = self.out_file.read_text().strip()
        self.assertEqual(
            output,
            """\
tests/files/other.yml=[[["nginx", "1.19"], [[[1, 20], "1.20"]]]]
tests/files/docker-compose.yml=[[["nginx", "1.19"], [[[1, 20], "1.20"]]]]""",
        )
