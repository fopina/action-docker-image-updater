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

    def tearDown(self) -> None:
        os.environ = self._env
        self.out_file.unlink()

    def test_sum(self):
        os.environ.update(
            {
                'GITHUB_OUTPUT': str(self.out_file),
                'INPUT_NUMBER-ONE': '1',
                'INPUT_NUMBER-TWO': '10',
            }
        )
        entrypoint.main()
        output = self.out_file.read_text().strip()
        self.assertEqual(output, 'sum=11')

    @mock.patch('entrypoint.requests')
    def test_joke(self, req_mock):
        req_mock.get.return_value.json.return_value = {'joke': 'haha'}
        os.environ.update(
            {
                'GITHUB_OUTPUT': str(self.out_file),
            }
        )
        entrypoint.main()
        output = self.out_file.read_text().strip()
        self.assertEqual(output, 'sum=haha')
