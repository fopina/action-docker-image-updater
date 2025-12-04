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

    def test_bad_yaml(self):
        self.req_mock.get.return_value.json.return_value = {'token': '123', 'tags': ['v3.99.0-alpine', 'v3.99.0']}
        ret = entrypoint.main(
            ['--dry', '--file-match', '**/some-helm*.y*ml', '--image-name-jsonpath', 'image.repository']
        )
        self.assertEqual(ret, 1)
        plan = self.load_plan()
        self.assertIsNone(plan)
