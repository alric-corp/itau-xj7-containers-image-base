"""Record only allowlisted version commands; never dump environment/credentials."""
import argparse
import json
import os
from pathlib import Path
import subprocess

COMMANDS = {
    'validation': {'apko': ['./apko', 'version'], 'trivy': ['trivy', '--version']},
    'publication': {'cosign': ['cosign', 'version'], 'aws': ['aws', '--version'],
                    'docker': ['docker', '--version']},
    'promotion': {'cosign': ['cosign', 'version'], 'trivy': ['trivy', '--version'],
                  'aws': ['aws', '--version'], 'gh': ['gh', '--version'],
                  'buildx': ['docker', 'buildx', 'version']},
}


def collect(stage, run=subprocess.run):
    versions = {}
    for name, argv in COMMANDS[stage].items():
        result = run(argv, check=True, capture_output=True, text=True, timeout=30)
        versions[name] = (result.stdout + result.stderr).strip()
    return {'stage': stage, 'commit': os.environ.get('GITHUB_SHA'),
            'run_id': os.environ.get('GITHUB_RUN_ID'),
            'run_attempt': os.environ.get('GITHUB_RUN_ATTEMPT'), 'versions': versions}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=COMMANDS)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    record = collect(args.stage)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2) + '\n')
