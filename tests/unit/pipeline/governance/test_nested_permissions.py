import copy
import unittest

from scripts.pipeline.governance.lint_workflow_hardening import local_call_permissions


class NestedPermissionsTests(unittest.TestCase):
    def documents(self):
        return {
            'caller.yml': {'permissions': {'contents': 'read'}, 'jobs': {
                'build': {'uses': './.github/workflows/build.yml',
                          'permissions': {'contents': 'read'}}}},
            'build.yml': {'permissions': {'contents': 'read'}, 'jobs': {
                'contract': {'permissions': {'contents': 'read', 'actions': 'read'}}}},
        }

    def test_missing_caller_actions_permission_is_rejected(self):
        errors = local_call_permissions(self.documents())
        self.assertEqual(len(errors), 1)
        self.assertIn('actions: read exceeds caller permissions', errors[0])

    def test_job_override_can_exceed_its_own_workflow_default(self):
        docs = self.documents()
        docs['caller.yml']['jobs']['build']['permissions']['actions'] = 'read'
        self.assertEqual(local_call_permissions(docs), [])

    def test_each_nested_boundary_is_checked_and_cannot_elevate_read_to_write(self):
        docs = self.documents()
        docs['caller.yml']['jobs']['build']['permissions']['actions'] = 'read'
        docs['build.yml']['jobs']['contract']['uses'] = './.github/workflows/inner.yml'
        docs['inner.yml'] = copy.deepcopy(docs['build.yml'])
        docs['inner.yml']['jobs']['contract'] = {'permissions': {'actions': 'write'}}
        errors = local_call_permissions(docs)
        self.assertEqual(len(errors), 1)
        self.assertIn('build.yml/contract -> inner.yml/contract', errors[0])
