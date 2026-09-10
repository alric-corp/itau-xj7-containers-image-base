from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import yaml

from scripts.pipeline.governance.workflow_dependencies import (
    REPOSITORY, ROOT, dependencies, shared_workflows, tooling_consistency, workflow_files)


class DependencyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve() / 'caller'
        self.shared = Path(self.tmp.name).resolve() / 'shared'
        (self.root / '.github/workflows').mkdir(parents=True)
        (self.shared / '.github/workflows').mkdir(parents=True)
        self.remote = self.shared / '.github/workflows/validate.yml'
        self.remote.write_text('''on:
  workflow_call:
    inputs:
      frameworks:
        type: string
        required: true
permissions:
  contents: read
jobs:
  validate:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/upload-artifact@aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
        with:
          name: validated-oci-example
          retention-days: 3
''')
        self.git('init', '-q')
        self.git('add', '.')
        self.git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
                 '-c', 'commit.gpgsign=false', 'commit', '-qm', 'fixture')
        self.sha = self.git('rev-parse', 'HEAD').strip()
        self.caller = self.root / '.github/workflows/caller.yml'
        self.write_caller()

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.shared), *args], check=True,
                              capture_output=True, text=True).stdout

    def write_caller(self, ref=None, supplied=None):
        self.caller.write_text(yaml.safe_dump({
            'permissions': {'contents': 'read'}, 'jobs': {'validate': {
                'uses': REPOSITORY + '/.github/workflows/validate.yml@' + (ref or self.sha),
                'with': {'frameworks': '["example"]'} if supplied is None else supplied}}}))

    def test_reads_the_actual_pinned_uploader_for_retention(self):
        paths = workflow_files(self.root, self.shared)
        self.assertEqual(set(paths), {self.caller, self.remote})
        uploader = yaml.safe_load(self.remote.read_text())['jobs']['validate']['steps'][0]
        self.assertEqual(uploader['with']['retention-days'], 3)

    def test_unapproved_floating_refs_are_rejected(self):
        for ref in ('main', 'v1', 'a' * 39, 'a' * 40 + '/../../bad'):
            self.write_caller(ref)
            with self.subTest(ref=ref), self.assertRaises(ValueError):
                dependencies(self.root)

    def test_environment_cannot_override_the_reviewed_commit(self):
        self.write_caller('a' * 40)
        with patch.dict('os.environ', {'REUSABLE_WORKFLOWS_SHA': self.sha}):
            with self.assertRaisesRegex(ValueError, 'HEAD differs'):
                shared_workflows(self.root, self.shared)

    def test_missing_checkout_fails_instead_of_omitting_shared_artifacts(self):
        with self.assertRaisesRegex(ValueError, 'missing shared checkout'):
            shared_workflows(self.root, self.shared / 'missing')

    def test_different_checkout_commit_is_rejected(self):
        self.write_caller('a' * 40)
        with self.assertRaisesRegex(ValueError, 'HEAD differs'):
            shared_workflows(self.root, self.shared)

    def test_edited_workflow_cannot_mask_pinned_retention(self):
        self.remote.write_text(self.remote.read_text().replace('retention-days: 3', 'retention-days: 30'))
        with self.assertRaisesRegex(ValueError, 'differs from its pinned commit'):
            shared_workflows(self.root, self.shared)

    def test_missing_or_unknown_inputs_are_rejected(self):
        for supplied in ({}, {'frameworks': '[]', 'test-command': 'true'}):
            self.write_caller(supplied=supplied)
            with self.subTest(supplied=supplied), self.assertRaisesRegex(ValueError, 'incompatible inputs'):
                shared_workflows(self.root, self.shared)

    def test_mixed_shared_workflow_releases_are_rejected(self):
        original = self.caller.read_text()
        (self.caller.parent / 'second.yml').write_text(original.replace(self.sha, 'a' * 40))
        with self.assertRaisesRegex(ValueError, 'one reviewed release'):
            dependencies(self.root)

    def test_scan_tool_divergence_between_validation_and_promotion_is_rejected(self):
        paths = []
        for index, sha in enumerate(('a' * 40, 'b' * 40)):
            path = self.root / f'tool-{index}.yml'
            path.write_text(yaml.safe_dump({'jobs': {'scan': {'steps': [
                {'uses': REPOSITORY + '/actions/setup-trivy@' + sha}]}}}))
            paths.append(path)
        with self.assertRaisesRegex(ValueError, 'one Trivy setup SHA'):
            tooling_consistency(paths)


class ProductIdentityTests(unittest.TestCase):
    def test_signing_identity_stays_in_the_product(self):
        document = yaml.safe_load((ROOT / '.github/workflows/build-base-images.yml').read_text())
        publisher = document['jobs']['build-push']
        self.assertNotIn('uses', publisher)
        steps = publisher['steps']
        self.assertTrue(any('cosign sign' in step.get('run', '') for step in steps))
        self.assertTrue(any(step.get('uses', '').startswith('actions/attest-build-provenance@')
                            for step in steps))


if __name__ == '__main__':
    unittest.main()
