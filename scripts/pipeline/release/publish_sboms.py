"""Sign the original validated SPDX documents, each against its own OCI digest."""
import argparse
import json
from pathlib import Path
import subprocess

from scripts.pipeline.artifacts.oci_artifact import verify
from scripts.pipeline.artifacts.image_reference import require_digest_reference


def publish(layout, image_ref, output, run=subprocess.run):
    require_digest_reference(image_ref)
    layout = Path(layout)
    evidence = verify(layout, require_sbom=True)
    if evidence != json.loads((layout / 'validated-index.json').read_text()):
        raise ValueError('SBOM or OCI changed after validation')
    repository, digest = image_ref.rsplit('@', 1)
    if digest != evidence['digest']:
        raise ValueError('publication digest differs from SBOM index subject')
    records = []
    for sbom in evidence['sboms']:
        subject = repository + '@' + sbom['subject']
        run(['cosign', 'attest', '--yes', '--type', 'spdxjson', '--predicate',
             str(layout / sbom['path']), subject], check=True, timeout=180)
        records.append(dict(sbom, image_ref=subject, attested=True))
    Path(output).write_text(json.dumps(records, indent=2) + '\n')
    return records


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('layout')
    parser.add_argument('image_ref')
    parser.add_argument('--output', default='sbom-publication.json')
    publish(**vars(parser.parse_args()))
