'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const https = require('node:https');
const { X509Certificate } = require('node:crypto');

assert.equal(process.getuid(), 10000);
assert.equal(process.getgid(), 10000);
assert.equal(process.versions.node.split('.')[0], process.env.EXPECTED_RUNTIME_VERSION);
assert.throws(() => fs.writeFileSync('/app/runtime-test-write', 'must fail'),
  error => error.code === 'EROFS');
fs.writeFileSync('/tmp/runtime-test-write', 'ok');
assert.equal(fs.readFileSync('/tmp/runtime-test-write', 'utf8'), 'ok');
const bundle = fs.readFileSync('/etc/ssl/certs/ca-certificates.crt', 'utf8');
const certificates = bundle.match(/-----BEGIN CERTIFICATE-----[\s\S]*?-----END CERTIFICATE-----/g);
assert.ok(certificates?.length > 0, 'empty image CA bundle');
for (const pem of certificates) new X509Certificate(pem);

function request(url) {
  return new Promise((resolve, reject) => {
    const req = https.get(url, { timeout: 10000 }, response => {
      let body = '';
      response.setEncoding('utf8');
      response.on('data', part => body += part);
      response.on('end', () => resolve({ status: response.statusCode, body }));
      response.on('error', reject);
    });
    req.on('timeout', () => req.destroy(new Error('TLS request timed out')));
    req.on('error', reject);
  });
}
(async () => {
  assert.deepEqual(await request(process.env.TLS_TRUSTED_URL),
    { status: 200, body: 'runtime-tls-ok\n' });
  await assert.rejects(request(process.env.TLS_UNTRUSTED_URL),
    error => ['DEPTH_ZERO_SELF_SIGNED_CERT', 'SELF_SIGNED_CERT_IN_CHAIN',
      'UNABLE_TO_VERIFY_LEAF_SIGNATURE', 'UNABLE_TO_GET_ISSUER_CERT_LOCALLY'].includes(error.code));
  console.log(JSON.stringify({ version: process.versions.node, uid: process.getuid(), gid: process.getgid(), readonly: true,
    tmpfs: true, bundle_parse: true, tls_trusted: true, tls_untrusted_rejected: true }));
})().catch(error => { console.error(error); process.exitCode = 1; });
