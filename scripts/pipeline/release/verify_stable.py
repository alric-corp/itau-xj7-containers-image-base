"""Confirm the promoted index by querying ECR again using the stable tag."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

from scripts.pipeline.artifacts.image_reference import require_digest_reference
from scripts.pipeline.release.find_promotion_candidate import IMAGE_INDEX_TYPES, write_evidence


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('resposta ECR ambígua: chave JSON duplicada')
        result[key] = value
    return result


def verify_stable(image, candidate_digest, evidence_path):
    evidence = json.loads(Path(evidence_path).read_text())
    evidence.update(candidate_digest=candidate_digest, stable_digest_observed=None,
                    read_back_status='failed', promoted=False)
    evidence.pop('read_back_error', None)
    # Persist fail-closed state before invoking the registry, including on timeout.
    write_evidence(evidence_path, evidence)
    try:
        require_digest_reference(f'{image}@{candidate_digest}')
        repository = evidence['repository']
        if (evidence['digest'] != candidate_digest or evidence['image'] != image
                or image.split('/', 1)[-1] != repository):
            raise ValueError('read-back não corresponde ao candidato selecionado')
        raw = subprocess.run(
            ['aws', 'ecr', 'describe-images', '--repository-name', repository,
             '--image-ids', 'imageTag=stable', '--output', 'json', '--no-cli-pager'],
            check=True, capture_output=True, text=True, timeout=60).stdout
        response = json.loads(raw, object_pairs_hook=unique_object)
        details = response['imageDetails']
        if response.get('nextToken') or not isinstance(details, list) or len(details) != 1:
            raise ValueError('stable ausente ou resposta ECR ambígua: esperado um único índice')
        detail = details[0]
        tags = detail.get('imageTags')
        if (detail.get('repositoryName') != repository or not isinstance(tags, list)
                or not all(isinstance(tag, str) for tag in tags) or tags.count('stable') != 1):
            raise ValueError('resposta ECR não identifica stable no repositório do candidato')
        if detail.get('imageManifestMediaType') not in IMAGE_INDEX_TYPES:
            raise ValueError('stable não é um índice multi-arquitetura')
        observed = detail['imageDigest']
        require_digest_reference(f'{image}@{observed}')
        evidence['stable_digest_observed'] = observed
        if observed != candidate_digest:
            evidence['read_back_status'] = 'mismatch'
            raise ValueError(f'leitura de volta não bate: stable={observed}, esperado={candidate_digest}')
        evidence['read_back_status'] = 'confirmed'
        # The workflow recorder also requires successful write/read-back steps.
        return evidence
    except (OSError, ValueError, KeyError, TypeError, AttributeError, subprocess.SubprocessError) as error:
        evidence['read_back_error'] = str(error)
        raise
    finally:
        write_evidence(evidence_path, evidence)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image')
    parser.add_argument('candidate_digest')
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    try:
        evidence = verify_stable(args.image, args.candidate_digest, args.evidence)
    except (OSError, ValueError, KeyError, TypeError, AttributeError, subprocess.SubprocessError) as error:
        print(f'verificação de stable falhou: {error}', file=sys.stderr)
        return 1
    print(f"confirmado: {args.image}:stable = {evidence['stable_digest_observed']}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
