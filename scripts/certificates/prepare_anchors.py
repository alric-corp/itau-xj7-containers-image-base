#!/usr/bin/env python3
"""Stage or verify individually pinned CA anchors for Melange/Apko.

Use ca_bundle_interna.crt emitted by certificados.sh after its SHA-256 gate.
The external bundle includes public roots already supplied by Wolfi.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import ssl
import subprocess
import time

PEM = re.compile(r'-----BEGIN CERTIFICATE-----\s+[A-Za-z0-9+/=\s]+-----END CERTIFICATE-----')


def inspect(pem, allow_test=False):
    der = ssl.PEM_cert_to_DER_cert(pem)
    canonical = ssl.DER_cert_to_PEM_cert(der)
    result = subprocess.run(['openssl', 'x509', '-noout', '-subject', '-text', '-startdate', '-checkend', '0'],
                            input=canonical, text=True, capture_output=True, check=True)
    if 'CA:TRUE' not in result.stdout:
        raise ValueError('certificate is not a CA anchor (basicConstraints CA:TRUE required)')
    start = re.search(r'(?m)^notBefore=(.+)$', result.stdout)
    if not start or ssl.cert_time_to_seconds(start.group(1)) > time.time():
        raise ValueError('CA is not yet valid')
    if 'X509v3 Key Usage:' in result.stdout:
        usage = result.stdout.split('X509v3 Key Usage:', 1)[1].splitlines()[1]
        if 'Certificate Sign' not in usage:
            raise ValueError('CA keyUsage does not permit certificate signing')
    subject = result.stdout.splitlines()[0]
    if re.search(r'MOCK|TEST[ -]?FIXTURE|runtime-test', subject, re.I) and not allow_test:
        raise ValueError('test/mock CA is forbidden in a release trust manifest')
    return canonical, {'sha256': hashlib.sha256(der).hexdigest(), 'subject': subject}


def stage(bundle, destination, allow_test=False):
    content = Path(bundle).read_text()
    certificates = PEM.findall(content)
    if not certificates or PEM.sub('', content).strip():
        raise ValueError('expected only PEM certificates; no keys or other payloads')
    parsed = dict(inspect(pem, allow_test) for pem in certificates)
    records = sorted(parsed.values(), key=lambda item: item['sha256'])
    # Prepare everything before writing: a rejected certificate leaves no partial trust update.
    destination = Path(destination)
    anchors = destination / 'anchors'
    anchors.mkdir(parents=True, exist_ok=True)
    for existing in anchors.glob('*.crt'):
        existing.unlink()
    for pem, record in parsed.items():
        (anchors / (record['sha256'] + '.crt')).write_text(pem)
    manifest = {'profile': 'test' if allow_test else 'corporate',
                'source_sha256': hashlib.sha256(Path(bundle).read_bytes()).hexdigest(),
                'certificates': records}
    (destination / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


def verify(directory, allow_test=False):
    directory = Path(directory)
    manifest = json.loads((directory / 'manifest.json').read_text())
    profile = manifest['profile']
    if profile not in {'public', 'corporate', 'test'} or (profile == 'test' and not allow_test):
        raise ValueError('unapproved CA profile for release')
    records = []
    for path in sorted((directory / 'anchors').iterdir()):
        if path.name == '.gitkeep':
            continue
        content = path.read_text()
        matches = PEM.findall(content)
        if path.is_symlink() or path.suffix != '.crt' or len(matches) != 1 or PEM.sub('', content).strip():
            raise ValueError('each regular .crt file must contain exactly one CA; Apko skips bundles')
        _, record = inspect(matches[0], allow_test)
        if path.name != record['sha256'] + '.crt':
            raise ValueError('anchor filename differs from its DER SHA-256')
        records.append(record)
    if records != manifest['certificates']:
        raise ValueError('anchors differ from reviewed manifest')
    if (profile == 'public') != (len(records) == 0):
        raise ValueError('public profile must be empty; corporate/test profiles need anchors')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['stage', 'verify'])
    parser.add_argument('--bundle', type=Path)
    parser.add_argument('--directory', type=Path, default=Path('melange/certificates'))
    parser.add_argument('--allow-test-ca', action='store_true', help='isolated test images only')
    args = parser.parse_args()
    if args.command == 'stage':
        if args.bundle is None:
            parser.error('stage requires --bundle ca_bundle_interna.crt')
        stage(args.bundle, args.directory, args.allow_test_ca)
    verify(args.directory, args.allow_test_ca)
