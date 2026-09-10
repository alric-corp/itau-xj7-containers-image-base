"""Real TLS/readiness integration; requires OpenSSL and a loopback socket."""
from pathlib import Path
import re
import ssl
import tempfile
import unittest
import urllib.request

from scripts.pipeline.runtime import runtime_images as runtime


class TlsServerTests(unittest.TestCase):
    def test_tls_server_is_actually_reachable_after_the_readiness_check(self):
        # M08/M10/M14: no mocking here -- proves the real server, real
        # certificate and the bounded readiness check all work together,
        # not just that tls_server() doesn't raise.
        with tempfile.TemporaryDirectory() as temporary:
            with runtime.tls_server(Path(temporary), 'trusted') as (url, cert):
                port = re.search(r':(\d+)/', url).group(1)
                # host.docker.internal is a Docker-bridge alias, not
                # resolvable from this bare test process -- use loopback,
                # same as the readiness check itself does. The cert's SAN
                # is host.docker.internal, so hostname matching is off
                # here on purpose; chain validation (the actual TLS trust
                # test) still runs.
                loopback_url = f'https://127.0.0.1:{port}/'
                context = ssl.create_default_context(cafile=str(cert))
                context.check_hostname = False
                with urllib.request.urlopen(loopback_url, context=context, timeout=2) as response:
                    self.assertEqual(response.status, 200)
                    self.assertEqual(response.read(), b'runtime-tls-ok\n')
