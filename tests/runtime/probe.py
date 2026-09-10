"""Contrato funcional M08/M10 das imagens Python; sem dependência externa.

Executado com o próprio interpretador da imagem candidata. Mesmo contrato de
ambiente e de saída dos projetos compilados em `projects/`.
"""
import errno
import json
import os
from pathlib import Path
import ssl
import sys
import urllib.error
import urllib.request


def env(name):
    value = os.environ.get(name)
    assert value, f'variável de ambiente {name} ausente'
    return value


assert os.getuid() == 10000 and os.getgid() == 10000, "unexpected identity"
assert f'{sys.version_info.major}.{sys.version_info.minor}' == env('EXPECTED_RUNTIME_VERSION')

# /app pertence ao mesmo uid/gid do processo: a rejeição só pode vir do mount
# somente leitura, não de permissão.
try:
    Path(env('READONLY_PATH')).write_text('must fail')
except OSError as error:
    assert error.errno == errno.EROFS, f"expected read-only filesystem: {error}"
else:
    raise AssertionError('root filesystem is writable')

writable_dirs = env('WRITABLE_DIRS').split(',')
assert '/tmp' in writable_dirs, 'WRITABLE_DIRS precisa incluir /tmp'
for directory in writable_dirs:
    target = Path(directory) / 'runtime-test-write'
    target.write_text('ok')
    assert target.read_text() == 'ok'
    target.unlink()

# Check the image's existing bundle separately from the injected test CA.
bundle = ssl.create_default_context(cafile=env('IMAGE_CA_BUNDLE'))
assert bundle.cert_store_stats()['x509_ca'] > 0, 'empty image CA bundle'
context = ssl.create_default_context()
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}),
                                    urllib.request.HTTPSHandler(context=context))
for key in ('TLS_TRUSTED_URL', 'TLS_UNTRUSTED_URL'):
    try:
        with opener.open(env(key), timeout=10) as response:
            assert response.status == 200 and response.read() == b'runtime-tls-ok\n'
    except urllib.error.URLError as error:
        # Erro de conexão ou timeout não aprova o negativo.
        assert key == 'TLS_UNTRUSTED_URL', str(error)
        assert isinstance(error.reason, ssl.SSLCertVerificationError), str(error)
    else:
        assert key == 'TLS_TRUSTED_URL', 'untrusted certificate accepted'
print(json.dumps({'version': sys.version.split()[0], 'uid': os.getuid(), 'gid': os.getgid(),
                  'readonly': True, 'tmpfs': True, 'writable_dirs': True,
                  'bundle_parse': True, 'tls_trusted': True,
                  'tls_untrusted_rejected': True}))
