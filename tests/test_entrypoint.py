import os
import tempfile
import unittest
from pathlib import Path

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

    def test_dry(self):
        # FIXME: useless test, no assertions
        os.environ.update(
            {
                'GITHUB_OUTPUT': str(self.out_file),
                'INPUT_TOKEN': 'xxx',
                'INPUT_DRY': 'true',
            }
        )
        entrypoint.main(['--token', 'xxx'])
        output = self.out_file.read_text().strip()
        self.assertEqual(output, '')
