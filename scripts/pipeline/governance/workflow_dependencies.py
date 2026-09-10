"""Validate the reviewed shared workflows for offline contract/retention checks.

CI checks out the release ref declared by the caller and records its resolved
commit. Local checks use the same checkout at .reusable-workflows, or
REUSABLE_WORKFLOWS_PATH. A missing checkout, floating ref, divergent
release or altered workflow fails instead of hiding a gate.
"""
import argparse
import os
from pathlib import Path
import re
import subprocess
import sys

import yaml

ROOT = Path(__file__).resolve().parents[3]
REPOSITORY = 'alric-corp/alric-containers-reusable-workflows'
REFERENCE = re.compile(
    re.escape(REPOSITORY) + r'/(\.github/workflows/[\w-]+\.yml)@([0-9a-f]{40})')
GENERATED = {'cve-triage.lock.yml'}


def local_workflows(root=ROOT):
    return [path for path in sorted((root / '.github/workflows').glob('*.yml'))
            if path.name not in GENERATED]


def dependencies(root=ROOT):
    found = []
    for path in local_workflows(root):
        document = yaml.safe_load(path.read_text())
        for job_id, job in (document.get('jobs') or {}).items():
            uses = job.get('uses', '')
            if not uses.startswith(REPOSITORY + '/'):
                continue
            match = REFERENCE.fullmatch(uses)
            if not match:
                raise ValueError(f'{path.name}/{job_id}: shared workflow requires a full SHA')
            found.append({'caller': path, 'job': job, 'path': match[1], 'ref': match[2]})
    if not found:
        raise ValueError('no shared workflow callers found')
    if len({entry['ref'] for entry in found}) != 1:
        raise ValueError('shared workflow callers must adopt one reviewed release together')
    return found


def shared_workflows(root=ROOT, checkout=None):
    entries = dependencies(root)
    checkout = Path(checkout or os.environ.get('REUSABLE_WORKFLOWS_PATH')
                    or root / '.reusable-workflows').resolve()
    if not (checkout / '.git').exists():
        raise ValueError('missing shared checkout; set REUSABLE_WORKFLOWS_PATH or check out '
                         f'{REPOSITORY}@{entries[0]["ref"]} into {checkout}')
    head = subprocess.run(['git', '-C', str(checkout), 'rev-parse', 'HEAD'], check=True,
                          capture_output=True, text=True).stdout.strip()
    if head != entries[0]['ref']:
        raise ValueError('shared checkout HEAD differs from the caller release')
    files = []
    for entry in entries:
        path = checkout / entry['path']
        expected = subprocess.run(['git', '-C', str(checkout), 'show',
                                   f'{head}:{entry["path"]}'], check=True,
                                  capture_output=True).stdout
        if not path.is_file() or path.read_bytes() != expected:
            raise ValueError(f'{entry["path"]}: shared workflow differs from its pinned commit')
        document = yaml.safe_load(path.read_text())
        events = document.get('on', document.get(True)) or {}
        if set(events) != {'workflow_call'}:
            raise ValueError(f'{path.name}: shared executor must accept workflow_call only')
        declared = (events['workflow_call'] or {}).get('inputs') or {}
        supplied = entry['job'].get('with') or {}
        missing = [name for name, definition in declared.items()
                   if definition.get('required') and name not in supplied]
        unknown = sorted(set(supplied) - set(declared))
        if missing or unknown:
            raise ValueError(f'{entry["caller"].name}: incompatible inputs; '
                             f'missing={missing}, unknown={unknown}')
        if path not in files:
            files.append(path)
    return files


def workflow_files(root=ROOT, checkout=None):
    return local_workflows(root) + shared_workflows(root, checkout)


def tooling_consistency(paths):
    """Validation, promotion and recovery must use the same Trivy definition."""
    refs = set()
    for path in paths:
        document = yaml.safe_load(path.read_text())
        for job in (document.get('jobs') or {}).values():
            for step in job.get('steps') or []:
                uses = step.get('uses', '')
                if uses.startswith(REPOSITORY + '/actions/setup-trivy@'):
                    refs.add(uses)
    if len(refs) != 1:
        raise ValueError('validation, promotion and recovery must use one Trivy setup SHA')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['checkout', 'lint'])
    args = parser.parse_args()
    try:
        if args.mode == 'checkout':
            ref = dependencies()[0]['ref']
            output = f'repository={REPOSITORY}\nref={ref}\n'
            if os.environ.get('GITHUB_OUTPUT'):
                with open(os.environ['GITHUB_OUTPUT'], 'a') as stream:
                    stream.write(output)
            else:
                print(output, end='')
        else:
            from scripts.pipeline.governance.lint_workflow_hardening import check
            problems = []
            paths = workflow_files()
            tooling_consistency(paths)
            for path in paths:
                problems += check(path.name, yaml.safe_load(path.read_text()))
            if problems:
                raise ValueError('; '.join(problems))
            print('Shared workflow SHA, inputs and hardening verified.')
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f'::error::{error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
