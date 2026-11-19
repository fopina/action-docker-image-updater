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
        # Docker Hub's nginx tag does not have a readable OCI creation time,
        # so the default cooldown skips it.
        self.assertIsNone(plan)

    def test_it2(self):
        plan = self.load_plan('it2')
        self.assertEqual(
            plan,
            {
                'tests/files/on-ghcr.yml': [[['ghcr.io/gethomepage/homepage', 'v1.6.1'], mock.ANY]],
            },
        )

    def test_it3(self):
        plan = self.load_plan('it3')
        # The Portainer image tags do not have a readable OCI creation time.
        self.assertNotIn('tests/files/ansible_playbook.yml', plan)
        self.assertIn('tests/files/on-ghcr.yml', plan)
