import json
import os
import unittest
from unittest import mock


class TestIntegration(unittest.TestCase):
    """
    This module does not start with test_ intentionally.
    This prevents simple `pytest` from picking it up as it should only run inside the test action
    """

    def load_plan(self, step_id):
        data = os.getenv('STEPS_CONTEXT')
        self.assertIsNotNone(data)
        data = json.loads(data)
        self.assertIn(step_id, data)
        if 'plan' not in data[step_id].get('outputs', {}):
            return None
        return json.loads(data[step_id]['outputs']['plan'])

    def test_it1(self):
        plan = self.load_plan('it1')
        self.assertEqual(
            plan,
            {
                'tests/files/docker-compose.yml': [[['nginx', '1.19'], mock.ANY]],
            },
        )

    def test_it2(self):
        plan = self.load_plan('it2')
        self.assertEqual(
            plan,
            {
                'tests/files/docker-compose.yml': [[['nginx', '1.19'], mock.ANY]],
                'tests/files/other.yml': [[['nginx', '1.19'], mock.ANY]],
            },
        )
