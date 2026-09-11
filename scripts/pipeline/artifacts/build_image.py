"""Build one OCI candidate with a recorded package lock and a fixed source date.

Fresh builds resolve current packages once. Replay uses the saved lock, source
revision, configuration and Melange repository; publication never rebuilds.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess


def command(args):
    return subprocess.check_output(args, text=True).strip()


def build(framework, output, engine='native', repository='melange-repo/packages',
          keyring='melange-repo/melange.rsa.pub', arch='x86_64,aarch64', lockfile=None):
    # This entry point is also used locally; reject paths and shell metacharacters.
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', framework):
        raise ValueError('invalid framework')
    config = Path('frameworks') / (framework + '.yaml')
    if not config.is_file():
        raise ValueError('unknown framework')
    revision = command(['git', 'rev-parse', 'HEAD'])
    epoch = int(command(['git', 'show', '-s', '--format=%ct', 'HEAD']))
    date = datetime.fromtimestamp(epoch, timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    source = os.environ.get('GITHUB_REPOSITORY')
    if not source:
        remote = command(['git', 'remote', 'get-url', 'origin'])
        source = re.sub(r'^.*github.com[:/]', '', remote).removesuffix('.git')
    if not re.fullmatch(r'[\w.-]+/[\w.-]+', source):
        raise ValueError('source must be a GitHub owner/repository')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    (output / 'sbom').mkdir(exist_ok=True)
    lock = output / 'apko.lock.json'
    apko = ['./apko']
    if engine == 'docker':
        # Native CI also runs Apko unprivileged. Keep bind-mount outputs owned
        # by the caller on Linux (Docker Desktop hides this ownership mismatch).
        apko = ['docker', 'run', '--rm', '--user', f'{os.getuid()}:{os.getgid()}',
                '-v', f'{Path.cwd()}:/work', '-w', '/work',
                os.environ['APKO_IMAGE']]
    common = ['--arch', arch, '--repository-append', repository, '--keyring-append', keyring]
    if engine == 'docker':
        common += ['--cache-dir', '/tmp/apko-cache']
    if lockfile:
        lock.write_bytes(Path(lockfile).read_bytes())
    else:
        subprocess.run(apko + ['lock', str(config), '--output', str(lock)] + common, check=True)
    annotations = {'source': f'https://github.com/{source}', 'revision': revision,
                   'version': f'{framework}-{revision[:12]}', 'vendor': source.split('/')[0],
                   # This repository has no declared distribution license. Package
                   # licenses remain individually recorded in SPDX; do not invent one.
                   'licenses': 'NOASSERTION'}
    annotation_args = []
    for name, value in annotations.items():
        annotation_args += ['--annotations', f'org.opencontainers.image.{name}:{value}']
    subprocess.run(apko + ['build', str(config), f'localhost/image-base-{framework}',
                           str(output), '--lockfile', str(lock), '--build-date', date,
                           '--vcs=false', '--sbom-path', str(output / 'sbom')]
                   + common + annotation_args, check=True)
    metadata = {'revision': revision, 'source_date_epoch': epoch, 'build_date': date,
                'annotations': annotations, 'lock_sha256': hashlib.sha256(lock.read_bytes()).hexdigest(),
                'config_sha256': hashlib.sha256(config.read_bytes()).hexdigest()}
    (output / 'build-inputs.json').write_text(json.dumps(metadata, indent=2) + '\n')
    return metadata


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('framework')
    parser.add_argument('output')
    parser.add_argument('--engine', choices=['native', 'docker'], default='native')
    parser.add_argument('--repository', default='melange-repo/packages')
    parser.add_argument('--keyring', default='melange-repo/melange.rsa.pub')
    parser.add_argument('--arch', default='x86_64,aarch64')
    parser.add_argument('--lockfile')
    args = parser.parse_args()
    build(**vars(args))
