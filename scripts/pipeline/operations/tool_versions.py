"""Record only allowlisted version commands; never dump environment/credentials.

M09: além dos digests fixados, o que rodou de fato. As versões efetivas das
ferramentas e do runner ficam junto das evidências da etapa, porque um digest
fixado não diz qual versão do `aws`/`gh`/`python3` da imagem do runner
participou da publicação ou da promoção — essas mudam sem passar por nenhum
pin deste repositório.

Só comandos de versão em allowlist e um punhado de campos do runner. Nada de
`printenv`, `toJSON(github)` ou dump de ambiente: uma coleta de diagnóstico
não pode virar vazamento de segredo.
"""
import argparse
import json
import os
import re
from pathlib import Path
import subprocess

# Ferramentas do runner presentes em toda etapa: a versão delas muda com a
# imagem do runner, sem passar por nenhum pin deste repositório.
RUNNER = {'python3': ['python3', '--version'], 'git': ['git', '--version']}

COMMANDS = {
    'validation': dict(RUNNER, apko=['./apko', 'version'], trivy=['trivy', '--version']),
    'publication': dict(RUNNER, cosign=['cosign', 'version'], aws=['aws', '--version'],
                        docker=['docker', '--version']),
    'promotion': dict(RUNNER, cosign=['cosign', 'version'], trivy=['trivy', '--version'],
                      aws=['aws', '--version'], gh=['gh', '--version'],
                      buildx=['docker', 'buildx', 'version']),
}

# Identificação da imagem do runner hospedado, exposta pelo próprio runner.
RUNNER_FIELDS = ('RUNNER_OS', 'RUNNER_ARCH', 'RUNNER_NAME', 'ImageOS', 'ImageVersion')


def parse_version(output):
    # Chainguard and cosign print ASCII art before their GitVersion field.
    field = re.search(r'(?m)^\s*GitVersion:\s*(\S+)', output)
    if field:
        return field.group(1)
    version = re.search(r'(?i)(?:version[: /]+|aws-cli/|buildx\s+)(v?\d+(?:\.\d+)*(?:[+~.-][\w.-]+)?)', output)
    if version:
        return version.group(1)
    python = re.search(r'^Python\s+(\S+)', output)
    if python:
        return python.group(1)
    raise ValueError('version command produced no recognizable version')


def collect(stage, run=subprocess.run, environment=None):
    environment = os.environ if environment is None else environment
    versions = {}
    raw_versions = {}
    for name, argv in COMMANDS[stage].items():
        result = run(argv, check=True, capture_output=True, text=True, timeout=30)
        raw_versions[name] = (result.stdout + result.stderr).strip()
        versions[name] = parse_version(raw_versions[name])
    if stage == 'validation':
        raw_versions['melange'] = Path('melange-repo/melange-version.txt').read_text().strip()
        versions['melange'] = parse_version(raw_versions['melange'])
    # A imagem do Skopeo é fixada por digest no workflow que a usa; registrar
    # o digest efetivo aqui mantém a evidência da etapa completa sem repetir
    # o pin em outro lugar.
    skopeo = environment.get('SKOPEO_IMAGE')
    return {'stage': stage, 'commit': environment.get('GITHUB_SHA'),
            'run_id': environment.get('GITHUB_RUN_ID'),
            'run_attempt': environment.get('GITHUB_RUN_ATTEMPT'),
            'runner': {field: environment[field] for field in RUNNER_FIELDS
                       if field in environment},
            'pinned_images': {'skopeo': skopeo} if skopeo else {},
            'versions': versions, 'version_output': raw_versions}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=COMMANDS)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    record = collect(args.stage)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2) + '\n')
