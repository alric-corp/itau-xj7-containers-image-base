import re
import unittest

from scripts.pipeline.governance.workflow_dependencies import (
    ROOT, shared_workflows, tooling_consistency, workflow_files)


class SharedWorkflowContractTests(unittest.TestCase):
    def test_real_callers_match_shared_api_and_tooling(self):
        tooling_consistency(workflow_files())

    def test_published_executors_have_all_required_caller_entry_points(self):
        scripts = set()
        for path in shared_workflows():
            scripts.update(re.findall(r'\.github/scripts/[a-z_]+\.py', path.read_text()))
        for script in scripts:
            self.assertTrue((ROOT / script).is_file(), f'Published executor requires {script}')
