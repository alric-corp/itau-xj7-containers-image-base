'use strict';
// Contrato funcional M08/M10 das imagens Node: executado com o próprio
// interpretador da imagem candidata, sem dependência externa. Mesmo
// contrato de ambiente/saída dos projetos compilados em projects/.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const https = require('node:https');
const { X509Certificate } = require('node:crypto');

function env(name) {
  const value = process.env[name];
  assert.ok(value, `variável de ambiente ${name} ausente`);
  return value;
}

assert.equal(process.getuid(), 10000);
assert.equal(process.getgid(), 10000);
assert.equal(process.versions.node.split('.')[0], env('EXPECTED_RUNTIME_VERSION'));

// /app pertence ao mesmo uid/gid do processo: a rejeição só pode vir do
// mount somente leitura, não de permissão.
assert.throws(() => fs.writeFileSync(env('READONLY_PATH'), 'must fail'),
  error => error.code === 'EROFS');

const writableDirs = env('WRITABLE_DIRS').split(',');
assert.ok(writableDirs.includes('/tmp'), 'WRITABLE_DIRS precisa incluir /tmp');
for (const directory of writableDirs) {
  const target = path.join(directory, 'runtime-test-write');
  fs.writeFileSync(target, 'ok');
  assert.equal(fs.readFileSync(target, 'utf8'), 'ok');
  fs.unlinkSync(target);
}

// Parsing do bundle que a imagem já traz, separado da CA de teste injetada.
const bundle = fs.readFileSync(env('IMAGE_CA_BUNDLE'), 'utf8');
const certificates = bundle.match(/-----BEGIN CERTIFICATE-----[\s\S]*?-----END CERTIFICATE-----/g);
assert.ok(certificates?.length > 0, 'empty image CA bundle');
for (const pem of certificates) new X509Certificate(pem);

const zonedHour = value => new Intl.DateTimeFormat('en-GB', {
  timeZone: 'America/Sao_Paulo', hour: '2-digit', hourCycle: 'h23'
}).format(new Date(value));
assert.equal(zonedHour('2026-01-15T12:00:00Z'), '09');
assert.equal(zonedHour('2018-01-15T12:00:00Z'), '10');

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
  assert.deepEqual(await request(env('TLS_TRUSTED_URL')),
    { status: 200, body: 'runtime-tls-ok\n' });
  // Erro de conexão ou timeout não aprova o negativo: o código do erro
  // precisa ser de verificação de certificado.
  await assert.rejects(request(env('TLS_UNTRUSTED_URL')),
    error => ['DEPTH_ZERO_SELF_SIGNED_CERT', 'SELF_SIGNED_CERT_IN_CHAIN',
      'UNABLE_TO_VERIFY_LEAF_SIGNATURE', 'UNABLE_TO_GET_ISSUER_CERT_LOCALLY'].includes(error.code));
  console.log(JSON.stringify({ version: process.versions.node, uid: process.getuid(),
    gid: process.getgid(), readonly: true, tmpfs: true, writable_dirs: true,
    timezone: true, bundle_parse: true, tls_trusted: true, tls_untrusted_rejected: true }));
})().catch(error => { console.error(error); process.exitCode = 1; });
