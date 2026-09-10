"""Enforce the M16 hardening rules on the hand-written workflows.

actionlint cobre sintaxe e shell; estas regras cobrem o que ele não checa e
que o M16 exige valer daqui pra frente, não só uma vez: checkout sem
credencial Git persistida, nenhum dado de entrada interpolado dentro de um
`run`, limite de duração em todo job executor, permissões declaradas e
Actions externas fixadas por SHA completo.

`cve-triage.lock.yml` é gerado por `gh aw compile` e fica de fora: o lock não
é editado à mão para satisfazer lint.
"""
import re
import sys
from pathlib import Path

import yaml

GENERATED = {'cve-triage.lock.yml'}
SHA = re.compile(r'[^@]+@[0-9a-f]{40}$')
EXPRESSION = re.compile(r'\$\{\{.*?\}\}', re.DOTALL)


def check(name, doc):
    """Devolve a lista de violações de um workflow já carregado."""
    problems = []
    if 'permissions' not in doc:
        problems.append(f'{name}: workflow sem `permissions` explícito no topo')
    for job_id, job in (doc.get('jobs') or {}).items():
        uses = job.get('uses')
        if uses and not uses.startswith('./') and not SHA.fullmatch(uses):
            problems.append(f'{name}: job `{job_id}` chama workflow sem SHA completo')
        steps = job.get('steps')
        if steps is None:
            continue  # chamada de workflow reutilizável: sem steps próprios
        if 'timeout-minutes' not in job:
            problems.append(f'{name}: job `{job_id}` sem `timeout-minutes`')
        for step in steps:
            label = step.get('name') or step.get('uses') or step.get('id') or '?'
            uses = step.get('uses')
            if uses and not uses.startswith('./') and not SHA.match(uses):
                problems.append(f'{name}: `{job_id}` / `{label}` usa Action sem SHA completo')
            if uses and uses.split('@')[0] == 'actions/checkout':
                if (step.get('with') or {}).get('persist-credentials') is not False:
                    problems.append(
                        f'{name}: `{job_id}` / `{label}` precisa de `persist-credentials: false`')
            found = EXPRESSION.search(step.get('run') or '')
            if found:
                problems.append(
                    f'{name}: `{job_id}` / `{label}` interpola {found.group()} dentro de `run` — '
                    'passe por `env:` e use a variável com aspas')
    return problems


def main(root=Path('.github/workflows')):
    problems = []
    for path in sorted(root.glob('*.yml')):
        if path.name in GENERATED:
            continue
        problems += check(path.name, yaml.safe_load(path.read_text()))
    for problem in problems:
        print(f'::error::{problem}', file=sys.stderr)
    return 1 if problems else 0


if __name__ == '__main__':
    raise SystemExit(main())
