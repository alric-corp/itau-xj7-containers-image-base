from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

from scripts.pipeline.governance import pin_inventory as inventory

RENOVATE = {'customManagers': [{
    'customType': 'regex',
    'managerFilePatterns': ['/^\\.github/workflows/build\\.yml$/', '/^Makefile$/'],
    'matchStrings': ['(?<depName>quay\\.io/skopeo/stable)@(?<currentDigest>sha256:[a-f0-9]{64})'],
    'datasourceTemplate': 'docker',
}, {
    'customType': 'regex',
    'managerFilePatterns': ['/^\\.github/workflows/build\\.yml$/'],
    'matchStrings': ['TRIVY_VERSION: (?<currentValue>v\\d+\\.\\d+\\.\\d+)'],
    'depNameTemplate': 'aquasecurity/trivy',
    'datasourceTemplate': 'github-releases',
}]}


class ParsingTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        root = Path(self.directory.name)
        (root / '.github/workflows').mkdir(parents=True)
        (root / '.github/workflows/build.yml').write_text(
            'jobs:\n  a:\n    steps:\n'
            '      - uses: actions/checkout@' + '1' * 40 + ' # v7\n'
            '      - uses: sloppy/action@v4\n'
            '      - uses: alric-corp/alric-containers-reusable-workflows/.github/workflows/validate-apko-images.yml@v1\n'
            'env:\n'
            '  SKOPEO: quay.io/skopeo/stable@sha256:' + 'b' * 64 + '\n'
            '  TRIVY_VERSION: v0.72.0\n')
        (root / 'Makefile').write_text(
            'RUN := docker run quay.io/skopeo/stable@sha256:' + 'c' * 64 + '\n')
        self.root = root
        self.patcher = patch.object(inventory, 'ROOT', root)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self.directory.cleanup()

    def paths(self):
        return [self.root / '.github/workflows/build.yml', self.root / 'Makefile']

    def test_actions_images_and_tool_versions_are_all_inventoried(self):
        entries = inventory.pins(self.paths())
        kinds = {(entry['kind'], entry['name']) for entry in entries}
        self.assertIn(('action', 'actions/checkout'), kinds)
        self.assertIn(('image', 'quay.io/skopeo/stable'), kinds)
        self.assertIn(('tool', 'TRIVY_VERSION'), kinds)
        loose = [entry for entry in entries if not entry['pinned']]
        self.assertEqual([entry['name'] for entry in loose], [
            'sloppy/action',
            'alric-corp/alric-containers-reusable-workflows/.github/workflows/validate-apko-images.yml'])

    def test_the_same_input_with_two_digests_is_reported_as_divergence(self):
        divergences = inventory.consistency(inventory.pins(self.paths()))
        self.assertEqual(len(divergences), 1)
        self.assertEqual(divergences[0]['name'], 'quay.io/skopeo/stable')
        self.assertEqual(len(divergences[0]['values']), 2)

    def test_coverage_maps_each_pin_to_who_proposes_its_update(self):
        entries = inventory.coverage(
            inventory.pins(self.paths()),
            inventory.renovate_matches(RENOVATE, self.paths()),
            {'github-actions'})
        managers = {(entry['name'], entry['file']): entry['managers'] for entry in entries}
        self.assertEqual(managers[('actions/checkout', '.github/workflows/build.yml')],
                         ['dependabot'])
        self.assertEqual(managers[('quay.io/skopeo/stable', 'Makefile')], ['renovate'])
        trivy = next(entry for entry in entries if entry['name'] == 'TRIVY_VERSION')
        self.assertEqual(trivy['managers'], ['renovate'])
        # Origem declarada no manager: é ela que a disponibilidade consulta,
        # em vez de um mapa hard-coded no script.
        self.assertEqual(trivy['source'], 'aquasecurity/trivy')

    def test_lint_reports_loose_pins_uncovered_pins_and_divergence(self):
        entries = inventory.coverage(inventory.pins(self.paths()),
                                     inventory.renovate_matches(RENOVATE, self.paths()),
                                     set())
        problems = inventory.lint(entries)
        self.assertTrue(any('sloppy/action' in problem and 'SHA completo' in problem
                            for problem in problems))
        self.assertTrue(any('actions/checkout' in problem and 'gerenciador' in problem
                            for problem in problems))
        self.assertTrue(any('valores diferentes' in problem for problem in problems))

    def test_floating_reusable_is_managed_but_still_rejected(self):
        entries = inventory.coverage(inventory.pins(self.paths()), {}, {'github-actions'})
        release = next(entry for entry in entries if entry['kind'] == 'reusable-workflow')
        self.assertEqual(release['current'], 'v1')
        self.assertFalse(release['pinned'])
        self.assertEqual(release['managers'], ['dependabot'])
        self.assertTrue(any('SHA completo' in problem for problem in inventory.lint([release])))


class RepositoryTests(unittest.TestCase):
    def test_this_repository_has_no_uncovered_or_divergent_pin(self):
        paths = inventory.scanned_files()
        entries = inventory.coverage(
            inventory.pins(paths),
            inventory.renovate_matches(
                json.loads((inventory.ROOT / 'renovate.json').read_text()), paths),
            inventory.dependabot_ecosystems(inventory.load_dependabot()))
        self.assertEqual(inventory.lint(entries), [])
        self.assertTrue(entries)
        key = inventory.wolfi_trust.local_pin()
        self.assertEqual(inventory.lint([key]), [])
        self.assertEqual(key['name'], 'wolfi-signing-key')


class AvailabilityTests(unittest.TestCase):
    def test_reusable_workflow_commit_is_checked_at_its_origin(self):
        def run(argv, **kwargs):
            self.assertEqual(argv[2], 'repos/alric-corp/alric-containers-reusable-workflows/commits/' + 'a' * 40)
            return subprocess.CompletedProcess(
                argv, 0, json.dumps({'sha': 'a' * 40}), '')
        entry = {'kind': 'reusable-workflow',
                 'name': 'alric-corp/alric-containers-reusable-workflows/.github/workflows/validate.yml',
                 'current': 'a' * 40, 'file': 'workflow.yml'}
        self.assertTrue(inventory.availability([entry], run)[0]['available'])

    def test_a_missing_action_sha_or_registry_digest_is_reported(self):
        def run(argv, **kwargs):
            if argv[0] == 'gh':
                body = json.dumps({'sha': 'a' * 40}) if 'aaa' in argv[2] else ''
                return subprocess.CompletedProcess(argv, 0 if body else 1, body, '')
            return subprocess.CompletedProcess(argv, 1, '', 'manifest unknown')
        entries = inventory.availability([
            {'kind': 'action', 'name': 'owner/repo', 'current': 'a' * 40, 'file': 'w.yml'},
            {'kind': 'action', 'name': 'owner/other', 'current': 'd' * 40, 'file': 'w.yml'},
            {'kind': 'image', 'name': 'quay.io/x', 'current': 'sha256:' + 'e' * 64,
             'file': 'w.yml'},
            {'kind': 'tool', 'name': 'TRIVY_VERSION', 'current': 'v1.0.0', 'file': 'w.yml'},
        ], run)
        self.assertEqual([entry['available'] for entry in entries], [True, False, False, None])

    def test_update_prs_only_count_the_update_bots_and_flag_the_stale_ones(self):
        now = datetime(2026, 9, 10, tzinfo=timezone.utc)
        pulls = [{'number': 1, 'title': 'bump', 'created_at': '2026-09-09T00:00:00Z',
                  'user': {'login': 'dependabot[bot]'}},
                 {'number': 2, 'title': 'digest', 'created_at': '2026-08-01T00:00:00Z',
                  'user': {'login': 'renovate[bot]'}},
                 {'number': 3, 'title': 'feature', 'created_at': '2026-01-01T00:00:00Z',
                  'user': {'login': 'someone'}}]
        entries = inventory.update_prs(pulls, now, stale_days=7)
        self.assertEqual([entry['number'] for entry in entries], [2, 1])
        self.assertTrue(entries[0]['stale'])
        self.assertFalse(entries[1]['stale'])

    def test_render_marks_unavailable_pins_and_missing_managers(self):
        markdown = inventory.render([
            {'kind': 'image', 'name': 'quay.io/x', 'current': 'sha256:' + 'e' * 64,
             'file': 'w.yml', 'managers': [], 'available': False}], [], stale_days=7)
        self.assertIn('**não**', markdown)
        self.assertIn('**nenhum**', markdown)


if __name__ == '__main__':
    unittest.main()
