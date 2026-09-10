#!/usr/bin/env python3
"""Compare the scanned index, Skopeo's result and the index read back from ECR."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

from scripts.pipeline.artifacts.image_reference import require_digest_reference
from scripts.pipeline.artifacts.oci_artifact import INDEX


def verify_publication(expected, copied_digest, remote_bytes, image_ref):
    require_digest_reference(image_ref)
    remote_digest = 'sha256:' + hashlib.sha256(remote_bytes).hexdigest()
    if not (expected['digest'] == copied_digest == remote_digest == image_ref.rsplit('@', 1)[1]):
        raise ValueError('published index differs from the scanned index')
    remote = json.loads(remote_bytes)
    if remote['mediaType'] != INDEX or remote['schemaVersion'] != 2:
        raise ValueError('published manifest is not an OCI v2 index')
    platforms = {}
    for entry in remote['manifests']:
        platform = entry['platform']
        name = f"{platform['os']}/{platform['architecture']}"
        if name in platforms:
            raise ValueError('duplicate platform in published index')
        platforms[name] = entry['digest']
    if set(platforms) != {'linux/amd64', 'linux/arm64'} or platforms != expected['platforms']:
        raise ValueError('published platform manifests differ from the scanned manifests')
    return {'image_ref': image_ref, 'validated_digest': expected['digest'],
            'copied_digest': copied_digest, 'remote_digest': remote_digest,
            'platforms': platforms}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('expected', type=Path)
    parser.add_argument('copied_digest', type=Path)
    parser.add_argument('remote_index', type=Path)
    parser.add_argument('image_ref')
    args = parser.parse_args()
    try:
        result = verify_publication(json.loads(args.expected.read_text()),
                                    args.copied_digest.read_text().strip(),
                                    args.remote_index.read_bytes(), args.image_ref)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        print(f'publication verification failed: {error}', file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
