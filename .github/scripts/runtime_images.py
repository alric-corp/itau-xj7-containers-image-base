#!/usr/bin/env python3
"""Run Node/Python contracts against both platforms of an existing OCI artifact."""
import argparse
import hashlib
from contextlib import contextmanager
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import socket
import ssl
import subprocess
import tarfile
import tempfile
import threading
import uuid

from oci_artifact import blob, load_index, verify
from readiness import wait_until_ready

ROOT = Path(__file__).resolve().parents[2]
SKOPEO = 'quay.io/skopeo/stable@sha256:b9ca6a549aa71990d50ab390a8bddf606a6689379026aa24e7f4f70b5a43fbcd'


def command(*args, timeout=180):
    result = subprocess.run(args, text=True, capture_output=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(f'{args[0]} failed ({result.returncode}): {result.stderr[-4000:]}')
    return result.stdout.strip()


def runtime(framework):
    if not (ROOT / 'frameworks' / f'{framework}.yaml').is_file():
        raise ValueError('framework must exist in the repository catalog')
    if re.fullmatch(r'nodejs\d+(?:-dev)?', framework):
        return '/usr/bin/node', 'probe.cjs'
    if re.fullmatch(r'python3-\d+', framework):
        return '/usr/bin/python3', 'probe.py'
    raise ValueError('runtime contracts currently support Node and Python only')


def execution_mode(daemon_arch, target_arch):
    aliases = {'x86_64': 'amd64', 'aarch64': 'arm64'}
    daemon_arch = aliases.get(daemon_arch, daemon_arch)
    if daemon_arch not in ('amd64', 'arm64'):
        raise ValueError(f'unsupported Docker daemon architecture: {daemon_arch}')
    return 'native' if daemon_arch == target_arch else 'emulated'


def validate_result(output):
    result = json.loads(output)
    if result.get('uid') != 10000 or result.get('gid') != 10000:
        raise ValueError('runtime did not confirm uid/gid 10000')
    for key in ('readonly', 'tmpfs', 'bundle_parse', 'tls_trusted', 'tls_untrusted_rejected'):
        if result.get(key) is not True:
            raise ValueError(f'runtime did not confirm {key}')
    return result


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'runtime-tls-ok\n')

    def log_message(self, *args):
        pass


@contextmanager
def tls_server(directory, name):
    cert, key = directory / f'{name}.pem', directory / f'{name}.key'
    command('openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1',
            '-keyout', str(key), '-out', str(cert), '-subj', '/CN=host.docker.internal',
            '-addext', 'subjectAltName=DNS:host.docker.internal',
            '-addext', 'basicConstraints=critical,CA:TRUE')
    server = ThreadingHTTPServer(('0.0.0.0', 0), Handler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert, key)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        # M08/M10/M14: bounded readiness check from the harness (this
        # process), not the container -- replaces the implicit assumption
        # that a bound socket is already reachable across the Docker
        # bridge by the time the container starts. A fast server pays no
        # wait; one that never comes up fails within the limit instead of
        # the container hanging on connection refused for its own timeout.
        wait_until_ready(
            lambda: socket.create_connection(('127.0.0.1', server.server_port), timeout=1).close(),
            interval=0.05, timeout=5.0, attempts=100)
        yield f'https://host.docker.internal:{server.server_port}/', cert
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def expected_config(layout, arch):
    _, index = load_index(layout)
    entry = next(item for item in index['manifests']
                 if item['platform']['architecture'] == arch)
    manifest = json.loads(blob(layout, entry).read_text())
    return manifest['config']['digest']


def archive_config(archive):
    with tarfile.open(archive) as source:
        manifests = json.load(source.extractfile('manifest.json'))
        if len(manifests) != 1:
            raise ValueError('Docker archive must contain exactly one image')
        config = source.extractfile(manifests[0]['Config']).read()
    return 'sha256:' + hashlib.sha256(config).hexdigest()


def run_platform(layout, framework, arch, directory, trusted_url, untrusted_url, ca):
    executable, probe = runtime(framework)
    version = framework.removeprefix('nodejs').removesuffix('-dev') if probe == 'probe.cjs' \
        else framework.removeprefix('python').replace('-', '.')
    tag = f'localhost/runtime-contract:{uuid.uuid4().hex}'
    name = f'runtime-contract-{uuid.uuid4().hex}'
    archive = directory / f'{arch}.tar'
    exported = directory / f'{arch}-loaded.tar'
    try:
        command('docker', 'run', '--rm', '-v', f'{layout}:/candidate:ro',
                '-v', f'{directory}:/output', SKOPEO, '--override-arch', arch,
                '--override-os', 'linux', 'copy', 'oci:/candidate:image',
                f'docker-archive:/output/{arch}.tar:{tag}')
        command('docker', 'load', '--input', str(archive))
        inspected = json.loads(command('docker', 'image', 'inspect', tag))[0]
        # Docker's containerd store may expose a manifest digest as Id. Re-export
        # the loaded image and hash its actual config instead of assuming Id's type.
        command('docker', 'image', 'save', '--output', str(exported), inspected['Id'])
        config_digest = archive_config(exported)
        if config_digest != expected_config(layout, arch):
            raise ValueError('loaded image config differs from the verified OCI candidate')
        if inspected['Architecture'] != arch or inspected['Os'] != 'linux':
            raise ValueError('loaded image platform differs from the requested platform')
        # No --user: the image must supply its own non-root default identity.
        args = ['docker', 'run', '--rm', '--name', name, '--platform', f'linux/{arch}',
                '--read-only', '--tmpfs', '/tmp:rw,nosuid,nodev,noexec,size=16m,mode=1777',
                '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
                '--add-host', 'host.docker.internal:host-gateway',
                '-v', f'{ROOT / "tests/runtime"}:/contract:ro',
                '-v', f'{ca}:/test-ca.pem:ro',
                '-e', 'SSL_CERT_FILE=/test-ca.pem', '-e', 'NODE_EXTRA_CA_CERTS=/test-ca.pem',
                '-e', 'PYTHONDONTWRITEBYTECODE=1',
                '-e', f'EXPECTED_RUNTIME_VERSION={version}',
                '-e', f'TLS_TRUSTED_URL={trusted_url}', '-e', f'TLS_UNTRUSTED_URL={untrusted_url}']
        output = command(*args, '--entrypoint', executable, inspected['Id'],
                         f'/contract/{probe}', timeout=60)
        result = validate_result(output)
        if framework.endswith('-dev'):
            command('docker', 'run', '--rm', '--name', name, '--platform', f'linux/{arch}',
                    '--network', 'none', '--read-only', '--cap-drop', 'ALL',
                    '--security-opt', 'no-new-privileges', '--entrypoint', '/bin/sh',
                    inspected['Id'], '-ec', 'test "$(id -u)" = 10000; test "$(id -g)" = 10000',
                    timeout=30)
            result['dev_shell'] = True
        return dict(result, config_digest=config_digest, docker_image_id=inspected['Id'])
    finally:
        # Only resources created by this invocation; never prune shared Docker state.
        subprocess.run(['docker', 'rm', '-f', name], capture_output=True, timeout=30)
        subprocess.run(['docker', 'image', 'rm', tag], capture_output=True, timeout=30)
        archive.unlink(missing_ok=True)
        exported.unlink(missing_ok=True)


def run(layout, framework, reports):
    runtime(framework)
    layout = Path(layout).resolve()
    reports = Path(reports)
    reports.mkdir(parents=True, exist_ok=True)
    failed = False
    # Overwrite both reports even when OCI verification or setup fails.
    evidence = {arch: {'framework': framework, 'platform': f'linux/{arch}',
                       'status': 'failed', 'started_at': datetime.now(timezone.utc).isoformat()}
                for arch in ('amd64', 'arm64')}
    try:
        verified = verify(layout)
        if verified != json.loads((layout / 'validated-index.json').read_text()):
            raise ValueError('OCI candidate differs from validated-index.json')
        daemon_arch = command('docker', 'info', '--format', '{{.Architecture}}')
        with tempfile.TemporaryDirectory(prefix='runtime-contract-') as temporary:
            directory = Path(temporary)
            with tls_server(directory, 'trusted') as (trusted_url, ca), \
                    tls_server(directory, 'untrusted') as (untrusted_url, _):
                for arch, report in evidence.items():
                    try:
                        report.update(index_digest=verified['digest'],
                                      manifest_digest=verified['platforms'][f'linux/{arch}'],
                                      execution=execution_mode(daemon_arch, arch))
                        report['checks'] = run_platform(layout, framework, arch, directory,
                                                        trusted_url, untrusted_url, ca)
                        report['status'] = 'passed'
                    except (OSError, ValueError, RuntimeError, KeyError, subprocess.SubprocessError) as error:
                        report['error'] = str(error)
                        failed = True
    except (OSError, ValueError, RuntimeError, KeyError, subprocess.SubprocessError) as error:
        failed = True
        for report in evidence.values():
            report['error'] = str(error)
    finally:
        for arch, report in evidence.items():
            (reports / f'runtime-{framework}-{arch}.json').write_text(json.dumps(report, indent=2) + '\n')
    return int(failed)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('layout')
    parser.add_argument('framework')
    parser.add_argument('--reports', default='reports')
    args = parser.parse_args()
    raise SystemExit(run(args.layout, args.framework, args.reports))
