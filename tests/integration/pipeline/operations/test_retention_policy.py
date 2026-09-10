import json
import unittest

from scripts.pipeline.operations import operational_health as health


class RetentionPolicyTests(unittest.TestCase):
    def test_repository_workflows_match_the_versioned_policy(self):
        policy = json.loads((health.ROOT / 'policies/operations/health.json').read_text())
        self.assertEqual(
            health.retention_drift(health.upload_retentions(health.workflow_files()), policy), [])
