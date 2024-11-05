import json
import os
import unittest


class TestIntegration(unittest.TestCase):
    """
    This module does not start with test_ intentionally.
    This prevents simple `pytest` from picking it up as it should only run inside the test action
    """

    def test_nothing(self):
        # FIXME: do some test?
        json.loads(os.getenv('STEPS_CONTEXT'))
