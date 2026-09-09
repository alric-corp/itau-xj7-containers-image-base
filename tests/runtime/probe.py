"""Executable contract for Python candidate images; no external dependencies."""
import errno
import json
import os
from pathlib import Path
import ssl
import sys
import urllib.error
import urllib.request

assert os.getuid() == 10000 and os.getgid() == 10000, "unexpected identity"
assert f'{sys.version_info.major}.{sys.version_info.minor}' == os.environ['EXPECTED_RUNTIME_VERSION']
try:
    Path('/app/runtime-test-write').write_text('must fail')
except OSError as error:
    assert error.errno == errno.EROFS, f"expected read-only filesystem: {error}"
else:
    raise AssertionError('root filesystem is writable')
Path('/tmp/runtime-test-write').write_text('ok')
assert Path('/tmp/runtime-test-write').read_text() == 'ok'

# Check the image's existing bundle separately from the injected test CA.
bundle = ssl.create_default_context(cafile='/etc/ssl/certs/ca-certificates.crt')
assert bundle.cert_store_stats()['x509_ca'] > 0, 'empty image CA bundle'
context = ssl.create_default_context()
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}),
                                    urllib.request.HTTPSHandler(context=context))
for key in ('TLS_TRUSTED_URL', 'TLS_UNTRUSTED_URL'):
    try:
        with opener.open(os.environ[key], timeout=10) as response:
            assert response.status == 200 and response.read() == b'runtime-tls-ok\n'
    except urllib.error.URLError as error:
        assert key == 'TLS_UNTRUSTED_URL', str(error)
        assert isinstance(error.reason, ssl.SSLCertVerificationError), str(error)
    else:
        assert key == 'TLS_TRUSTED_URL', 'untrusted certificate accepted'
print(json.dumps({'version': sys.version.split()[0], 'uid': os.getuid(), 'gid': os.getgid(), 'readonly': True,
                  'tmpfs': True, 'bundle_parse': True, 'tls_trusted': True,
                  'tls_untrusted_rejected': True}))
