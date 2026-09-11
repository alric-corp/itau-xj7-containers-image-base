import unittest
from scripts.pipeline.governance.lint_workflow_hardening import check

CHECKOUT = 'actions/checkout@' + '3' * 40
SAFE = {
    'permissions': {'contents': 'read'},
    'jobs': {'build': {'timeout-minutes': 5, 'steps': [
        {'name': 'Checkout', 'uses': CHECKOUT, 'with': {'persist-credentials': False}},
        {'name': 'Run', 'env': {'FRAMEWORK': '${{ matrix.framework }}'},
         'run': 'echo "$FRAMEWORK"'},
    ]}},
}


def with_job(job):
    return {'permissions': {'contents': 'read'}, 'jobs': {'build': job}}


class HardeningTests(unittest.TestCase):
    def test_hardened_workflow_passes(self):
        self.assertEqual(check('ok.yml', SAFE), [])

    def test_reusable_workflow_call_needs_no_steps_or_timeout(self):
        doc = with_job({'uses': './.github/workflows/validate-base-images.yml'})
        self.assertEqual(check('caller.yml', doc), [])

    def test_remote_reusable_workflow_requires_full_sha(self):
        workflow = 'owner/shared/.github/workflows/validate.yml@'
        for ref in ('main', 'v1', 'a' * 39):
            with self.subTest(ref=ref):
                self.assertIn('SHA completo', ' '.join(check(
                    'caller.yml', with_job({'uses': workflow + ref}))))
        self.assertEqual(check('caller.yml', with_job({'uses': workflow + 'a' * 40})), [])

    def test_corporate_reusable_workflow_also_requires_sha(self):
        uses = ('alric-corp/alric-containers-reusable-workflows/.github/workflows/'
                'validate-apko-images.yml@v1')
        self.assertIn('SHA completo', ' '.join(check('caller.yml', with_job({'uses': uses}))))

    def test_checkout_without_persist_credentials(self):
        for step in ({'uses': CHECKOUT},
                     {'uses': CHECKOUT, 'with': {'fetch-depth': 0}},
                     {'uses': CHECKOUT, 'with': {'persist-credentials': True}},
                     {'uses': CHECKOUT, 'with': {'persist-credentials': 'false'}}):
            with self.subTest(step=step):
                doc = with_job({'timeout-minutes': 5, 'steps': [step]})
                self.assertIn('persist-credentials', ' '.join(check('w.yml', doc)))

    def test_expression_inside_run_is_rejected(self):
        doc = with_job({'timeout-minutes': 5, 'steps': [
            {'name': 'Publish', 'run': 'echo "${{ inputs.soak-hours }}"'}]})
        self.assertIn('interpola', ' '.join(check('w.yml', doc)))

    def test_multiline_expression_inside_run_is_rejected(self):
        doc = with_job({'timeout-minutes': 5, 'steps': [
            {'name': 'Publish', 'run': 'echo "${{\n  inputs.frameworks\n}}"'}]})
        self.assertIn('interpola', ' '.join(check('w.yml', doc)))

    def test_expression_in_env_or_with_is_allowed(self):
        doc = with_job({'timeout-minutes': 5, 'steps': [
            {'name': 'Publish', 'env': {'F': '${{ inputs.frameworks }}'}, 'run': 'echo "$F"'}]})
        self.assertEqual(check('w.yml', doc), [])

    def test_missing_timeout_on_executor_job(self):
        doc = with_job({'steps': [{'name': 'Build', 'run': 'true'}]})
        self.assertIn('timeout-minutes', ' '.join(check('w.yml', doc)))

    def test_missing_top_level_permissions(self):
        doc = {'jobs': {'build': {'timeout-minutes': 5, 'steps': [{'run': 'true'}]}}}
        self.assertIn('permissions', ' '.join(check('w.yml', doc)))

    def test_action_not_pinned_to_a_full_sha(self):
        for uses in ('actions/checkout@v4', 'actions/checkout@main',
                     'actions/checkout@' + '3' * 39, 'actions/checkout@' + 'g' * 40):
            with self.subTest(uses=uses):
                doc = with_job({'timeout-minutes': 5, 'steps': [
                    {'uses': uses, 'with': {'persist-credentials': False}}]})
                self.assertIn('SHA completo', ' '.join(check('w.yml', doc)))

    def test_local_action_needs_no_sha(self):
        doc = with_job({'timeout-minutes': 5, 'steps': [{'uses': './.github/actions/setup-trivy'}]})
        self.assertEqual(check('w.yml', doc), [])
