import json
import os
import unittest


class TestIntegration(unittest.TestCase):
    """
    This module does not start with test_ intentionally.
    This prevents simple `pytest` from picking it up as it should only run inside the test action
    """

    def test_sumit(self):
        """
        Assert integration run for:
            ...
            id: sumit
            with:
                number-one: 2
                number-two: 1
        """
        data = json.loads(os.getenv('STEPS_CONTEXT'))
        self.assertEqual(data['sumit']['outputs']['sum'], '3')
