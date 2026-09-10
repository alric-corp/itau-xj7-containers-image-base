from datetime import datetime, timezone
import unittest

from scripts.pipeline.operations import operational_health as health


class ReleaseRunHealthTests(unittest.TestCase):
    def test_prs_and_non_main_dispatches_do_not_exhaust_release_query_budget(self):
        now = datetime(2026, 9, 10, tzinfo=timezone.utc)
        runs = [dict(id=n, created_at='2026-09-10T00:00:00Z', event=event,
                     head_branch=branch) for n, event, branch in (
                         (1, 'pull_request', 'main'),
                         (2, 'workflow_dispatch', 'feature'),
                         (3, 'push', 'main'))]
        seen = []

        def jobs(identifier):
            seen.append(identifier)
            return [{'name': 'build-base-images / Build & push nodejs22',
                     'conclusion': 'success', 'completed_at': '2026-09-10T00:00:00Z'}]

        result = health.framework_health(jobs, runs, ['nodejs22'], now, max_queries=1)
        self.assertEqual(seen, [3])
        self.assertFalse(result['truncated'])
        self.assertEqual(result['frameworks']['nodejs22']['publication_run'], 3)
