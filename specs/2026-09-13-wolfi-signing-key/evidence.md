# EVIDENCE — P1-03 Wolfi signing-key defense-in-depth

Propriedade reformulada por decisão arquitetural independente comunicada pelo
usuário em 13/09/2026: **READY TO REFORMULATE AND IMPLEMENT**. A entrega preserva
chave explícita local, pin, preflight, rotação revisada e monitor detect-only.
Não declara exclusive independent trust anchor. Resultados da repetição
local estão separados da execução anterior abaixo.

Estado local: **IMPLEMENTED + VERIFIED LOCALLY + RESIDUAL TOOLING RISK
DOCUMENTED**. Entrega preparada para nova revisão independente, sem aprovação
de integração. A ressalva preexistente do actionlint amplo está registrada.

O resultado histórico **NOT READY / BLOCKED_TOOLING** referia-se à propriedade
original de exclusividade, reprovada por auto-discovery. Essa descoberta
permanece íntegra e relevante: **EXPECTED TOOLING LIMITATION REPRODUCED**.

## Identidade

- Data: 13/09/2026 UTC; macOS arm64 com Docker Desktop.
- Branch `main`, baseline limpo: `f792aecd4fbfa28bdb9fd44bf920c167f64c5653`.
- Sessão: Codex, implementação gpt-6-astra ULTRA; sem auto-aprovação.
- Escopo: diff local, sem commit/push/PR.
- P1-01 já está presente neste baseline: `promote-stable.yml` exige read-back
  confirmado e igualdade dos digests antes de `promoted=true`. Nenhum arquivo
  de promoção/recovery/release foi alterado nesta fatia.

## Fontes oficiais

Consulta em `2026-09-13T02:25:26Z`; downloads independentes reais:

| Fonte | Distribuição | SHA-256 dos 800 bytes PEM |
| --- | --- | --- |
| A | <https://packages.wolfi.dev/os/wolfi-signing.rsa.pub> | `f0031424cf46f7db780ce63a45f0fd6aa6f85f601e6bb3b7a91fe3d4d5b7d2cc` |
| B | <https://raw.githubusercontent.com/wolfi-dev/os/1d350667a46522847140ce4772bf306193b2f41a/wolfi-signing.rsa.pub> | `f0031424cf46f7db780ce63a45f0fd6aa6f85f601e6bb3b7a91fe3d4d5b7d2cc` |

Resultado: **MATCH**, byte a byte. B usa o commit oficial consultado em
GitHub; blob `d50ff93535cb19aa526243928681865fb540a991` confere com a árvore
oficial. Fingerprint SHA-256 do SPKI DER em ambas:
`6e95f867b00808f1798f57b0ee98558ae2b195b28a75dc2b7030f4ea90c5ce25`.
O pin executável usa os bytes PEM, não o DER. Downloads temporários não
serão versionados além da chave a ser revisada.

## Implementação preservada e resultados da execução anterior

Path canônico: `melange/keys/wolfi-signing.rsa.pub`; pin adjacente
`wolfi-signing-key.json`. Configs: `distroless/image-base.yaml` e
`melange/image-base-ca-certificates.yaml`.

O pin esperado reside somente no JSON executável adjacente; os hashes neste
documento são snapshots de evidência. Chave pública regular é a única exceção
adicionada ao ignore de `*.rsa.pub`. Preflight offline no Makefile, no
`build_image` antes de lock/replay e no job anterior aos dois caminhos CI;
fixture de CA copia os mesmos bytes. Inventory incorpora `local-key` com
manager `human-review`; nenhum manager atualiza a chave automaticamente.

As duas referências explícitas remotas do baseline foram removidas. Apko e
Melange usam caminhos relativos ao CWD, respectivamente raiz do checkout e
`/work` montando somente `melange/`. A01/R4 foi exercido com esses mesmos paths.

| Comando/check | Resultado observado |
| --- | --- |
| `make test-unit` | exit 0; 268 testes PASS |
| `make test-integration` | exit 0; 24 testes PASS, 10,972s; socket TLS exigiu execução autorizada fora do sandbox |
| `make lint-local` | exit 0; 51 pins em 48 arquivos, hardening e lote padrão preservados |
| `make lint-shared` | exit 0; SHA/inputs/hardening, retenção/cron conferidos |
| `make lint-workflows` | exit 0; actionlint sobre workflows locais não gerados e os dois reusables fixados |
| `actionlint .github/workflows/validate-base-images.yml .github/workflows/pipeline-health.yml` | exit 0; execução isolada dos workflows modificados |
| `python3 -B tools/check_ai_context.py` | exit 0 |
| `git diff --check` | exit 0 |
| `python3 -B -m scripts.pipeline.governance.pin_inventory trust` | exit 0; expected_sha256 == actual_sha256, sem acesso remoto |

17 testes Wolfi novos; 33 direcionados incluindo inventory/layout passaram.
Cobrem chave correta, alteração PEM válida sem repin, ausência, fingerprint
errado, policy ausente, formato inválido mesmo com hash atualizado, segundo
RSA válido, symlink, falta da chave antes de qualquer comando de build/replay,
URL remota nos dois consumidores e em receita nova/inline/nested, keyring
extra/ausente, monitor same/divergent/unavailable sem escrita, CLI offline e
dependência do gate CI. Os novos testes não tratam auto-discovery como PASS.

### Mínimos reais

Ferramentas realmente executadas via Docker, nos digests inalterados do
Makefile: Apko `v1.2.43+dirty`, commit
`eb2d36fedabb189e013e715a638f51fc8162c0d5`; Melange `v0.59.5+dirty`, commit
`93b6e111db504997870489e06ecbe978e6b3239b`. O `go.mod` Melange fixa Apko v1.2.39.

Fixture em `/private/tmp/p1-03-real-wolfi/`, com cópia da chave local; Apko
configurou `https://packages.wolfi.dev/os`, package `busybox`, arquitetura
`aarch64`. Melange usou cópia da receita atual e perfil de certificados atual.
Não houve scan/lote completo neste mínimo nem alteração de CVE/gates.

| Operação | Exit | Tempo | Observação |
| --- | --- | --- | --- |
| `apko lock apko.yaml --arch aarch64 --output apko.lock.json` | 0 | 2,93s | Resolução com chave local |
| `apko build apko.yaml localhost/wolfi-trust-probe image.oci --arch aarch64 --lockfile apko.lock.json --build-date 2026-09-13T00:00:00Z` | 0 | 0,62s | Build normal, sem desabilitar assinatura |
| Mesmo lock, chave RSA errada somente na fixture | 1 | 2,65s | `crypto/rsa: verification error`, nenhuma chave fornecida verificou o índice Wolfi |
| Mesmo lock, chave ausente somente na fixture | 1 | 0,14s | `no such file or directory` no path esperado |
| `melange build image-base-ca-certificates.yaml --arch aarch64 --signing-key local-signing.rsa --build-date 2026-09-13T00:00:00Z` | 0 | 3,40s | Build real, mount `melange/` em `/work`, assinatura própria descartável |

Resumo e logs locais: `/private/tmp/p1-03-real-wolfi/results.json` e arquivos
`apko-*.log`, `melange-build-local-key.log` no mesmo diretório. Saídas de
build e private keys de fixtures não foram versionadas.

### Monitor real

Consulta real da fonte A após retry autorizado da falha de DNS do sandbox:
`remote_status=same`, `available=true`; expected/local/remote SHA-256 iguais
ao valor da tabela de fontes. Saída local em
`/private/tmp/p1-03-key-monitor.json`. Essa comparação só observa; não
escreveu chave/pin. Testes simulados de mismatch e indisponibilidade
comprovaram falha operacional e preservação dos bytes locais.

## Known Tooling Limitation — blocker original preservado

`contents.keyring` **≠ exclusive trust set**. A chave explícita e as chaves
descobertas compõem o mesmo conjunto de verificação. Comprometimento de
repository/CDN/TLS que permita servir discovery/JWKS e index/packages
assinados por outra chave pode introduzir confiança adicional. Pin e
monitor locais não impedem esse caminho.

O código oficial do [Apko executado](https://github.com/chainguard-dev/apko/blob/eb2d36fedabb189e013e715a638f51fc8162c0d5/pkg/apk/apk/implementation.go)
faz `InitDB → fetchChainguardKeys → DiscoverKeys` e escreve as chaves
descobertas em `/etc/apk/keys`. A [inicialização do build](https://github.com/chainguard-dev/apko/blob/eb2d36fedabb189e013e715a638f51fc8162c0d5/pkg/build/apk.go)
executa isso antes de `InitKeyring` com a chave explícita. O [comando lock](https://github.com/chainguard-dev/apko/blob/eb2d36fedabb189e013e715a638f51fc8162c0d5/internal/cli/lock.go)
também acrescenta `discoverKeysForLock`. Apko aceita arquivo local por
`os.ReadFile`, mas isso não elimina as outras chaves.

Consulta do source/CLI das versões fixadas não encontrou opção suportada
de disable seletivo; Apko oficial v1.3.0 consultado mantém esse caminho.
Não foram alterados pins de ferramentas. Melange usa a biblioteca Apko
para criar seu guest; uma verificação somente depois do lock seria tardia.

O experimento isolado já executado usou Apko fixado, HTTP fixture local,
config com **somente a chave Wolfi local**, package mínimo `trust-probe` e
APKINDEX assinado por outra RSA descartável. A chave real e os repositories
do working tree permaneceram intactos.

| Resposta da origem de fixture | `apko lock` | Resultado de segurança |
| --- | --- | --- |
| `/apk-configuration` ausente (404) | exit 1 | Índice rejeitado: `no signature with known key (one of: [wolfi-signing.rsa.pub])` |
| `/apk-configuration` + JWKS fornecem a RSA da fixture | exit 0 | Índice aceito e `trust-probe` registrado no lock; **FAIL da exclusividade original** |

O `with.lock.json` observado contém `contents.keyring` com
`keys/wolfi-signing.rsa.pub` **e** a chave `attacker.rsa.pub` descoberta da
origem. O resumo inicial do harness leu incorretamente `keyrings` no plural;
a confirmação das duas entradas vem do lock efetivo, cujo campo é singular.
Requests confirmaram consulta a `/with/os/apk-configuration`, `/with/keys.json`
e ao APKINDEX antes de obter o package mínimo. Não alegamos execução de
payload, assinatura do APK mínimo ou exploit hospedado: a prova observada
é aceitação de outra trust anchor para o índice e a resolução do lock.

Evidência local existente: `/private/tmp/p1-03-discovery-probe.py`,
`/private/tmp/p1-03-discovery-probe/{without.log,with.log,with.lock.json,results.json}`.
Nenhum script de reprodução adicional foi mantido no repositório; nenhum
cenário adicional de discovery foi executado. Logs/resultados foram resumidos aqui sem
private keys. Classificação nesta spec reformulada:
**EXPECTED TOOLING LIMITATION REPRODUCED**. O teste não foi reexecutado nesta
continuação; os resultados acima são a observação original preservada.
Não é `security control passed` nem expectedFailure na suíte. O antigo
BLOCKED_TOOLING continua explicando a impossibilidade de exclusividade local,
independentemente do incidente zlib; não é regressão do novo requisito.

## Estado operacional Wolfi atual

Consulta externa real em **2026-09-13T03:07:44Z** a
<https://packages.wolfi.dev/os/apk-configuration>: **HTTP 404**, curl exit 0
(consulta de status, sem `--fail`). Repetição autorizada após falha de DNS
do sandbox. Discovery dessa origem é no-op no estado observado; junto dos
mínimos reais com verificação normal, isso é compatível com uso efetivo da
chave explícita local. Não inferimos garantia futura ou invariant de segurança.
Nenhum gate exige esse 404. Corpo temporário em
`/private/tmp/p1-03-reformulation-apk-configuration.body`.

## Verificação repetida após reformulação — 13/09/2026 UTC

Mesma HEAD `f792aecd4fbfa28bdb9fd44bf920c167f64c5653`, diff local de P1-03
preservado. Nesta continuação foram reformulados os seis Markdown, runbook,
README/índice de docs, docstring do helper e frase do resumo do monitor.
Nenhuma lógica de verificação, teste, chave, pin, configuração ou gate foi
removido ou enfraquecido.

| Comando/check | Resultado desta continuação |
| --- | --- |
| `make test-unit` | exit 0; 268 testes, 5,255s |
| `make test-integration` | exit 0; 24 testes, 12,433s, após repetição autorizada para socket TLS local |
| `make lint-local` | exit 0; 51 pins em 48 arquivos; hardening e catálogo preservados |
| `make lint-shared` | exit 0; SHA/inputs/hardening e políticas operacionais |
| `make lint-workflows` | exit 0; seleção canônica existente de workflows locais e reusables fixados |
| `actionlint` | exit 1; 3 diagnósticos preexistentes somente em `cve-triage.lock.yml`, detalhados abaixo |
| `actionlint .github/workflows/validate-base-images.yml .github/workflows/pipeline-health.yml` | exit 0 |
| `python3 -B -m unittest tests.unit.pipeline.governance.test_wolfi_trust -v` | exit 0; os mesmos 17 testes, 0,334s |
| `python3 -B -m scripts.pipeline.governance.pin_inventory trust` | exit 0; SHA esperado/real iguais e ambos keyrings locais; preflight offline |
| `python3 -B tools/check_ai_context.py` | exit 0; arquivos, imports e links locais |
| `git diff --check` | exit 0; arquivos novos da spec também conferidos |

Logs em `/private/tmp/p1-03-reformulation-{unit,integration-authorized,lint-local,lint-shared,lint-workflows,actionlint,actionlint-changed,negative}.log`;
saída do preflight em `/private/tmp/p1-03-reformulation-trust.json`.
A primeira integração no sandbox falhou somente no bind do servidor TLS
com `Operation not permitted`; a repetição autorizada passou.

### Ressalva preexistente do actionlint amplo

Actionlint local `1.7.12` aponta `concurrency.queue` nas linhas 414 e 1147 e
ShellCheck SC2016 na linha 913 do workflow **gerado** `cve-triage.lock.yml`.
O arquivo está byte a byte idêntico à HEAD; SHA-256
`87fdeb694fb21e5bd1bc4d0cab8bcce06a753a2bae75ae1aa91c99fda9f64380`.
Extrair esse blob da HEAD e executar actionlint nele reproduziu exatamente
os três diagnósticos após normalizar os caminhos no output.

O Makefile já excluía `*.lock.yml` do lint manual antes desta fatia, pois
esses workflows são gerados pelo compilador. A seleção não foi alterada.
Não declaramos PASS do `actionlint` amplo nem modificamos a triagem para
obter verde. Log da reprodução: `p1-03-reformulation-actionlint-baseline.log`
em `/private/tmp/`. O lint canônico e os workflows modificados passaram.

### Hash, preflight e drift

SHA-256 real permanece `f0031424cf46f7db780ce63a45f0fd6aa6f85f601e6bb3b7a91fe3d4d5b7d2cc`.
Config Apko: `melange/keys/wolfi-signing.rsa.pub`; config Melange:
`keys/wolfi-signing.rsa.pub`. Lint varre os keyrings e rejeita URLs remotas.
Os repositories dos dois configs foram comparados com a HEAD e são iguais.
Os negativos preservados rejeitam alteração, ausência, pin errado, outra
RSA e formato inválido. A ausência na entrada `build_image` falha antes de
qualquer comando de lock/replay; os demais casos usam o mesmo preflight.

Monitor real em **2026-09-13T03:10:16Z**: `same`, `available=true`, SHA remoto
igual ao local/esperado. Comparação dos bytes antes/depois confirmou
`local_key_and_pin_unchanged=true`; registro em
`/private/tmp/p1-03-reformulation-monitor.json`. Testes de divergência e
indisponibilidade preservam chave/pin e permitem a decisão offline seguinte.
O monitor é **DETECTION ONLY**, não controle de confiança do Apko.

### Lock/build mínimo repetido

Fixture nova em `/private/tmp/p1-03-reformulation-build/`, copiando chave,
pin, receita Melange e certificados atuais; `require_key` passou antes das
ferramentas. Docker Desktop 29.7.2; digests Apko/Melange do Makefile inalterados.
Execução aarch64, sem publicação ou lote de scans, mantendo assinatura normal.

| Operação | Resultado |
| --- | --- |
| `apko lock apko.yaml --arch aarch64 --output apko.lock.json` | exit 0; log de 03:11:44Z registra `Discovered 0 auto-discovered keys` |
| `apko build apko.yaml localhost/wolfi-trust-reformulation image.oci --arch aarch64 --lockfile apko.lock.json --build-date 2026-09-13T00:00:00Z` | exit 0; OCI construído às 03:12:57Z |
| `melange keygen local-signing.rsa` | exit 0; chave descartável somente para o pacote próprio da fixture |
| `melange build image-base-ca-certificates.yaml --arch aarch64 --signing-key local-signing.rsa --build-date 2026-09-13T00:00:00Z` | exit 0; pacote próprio e índice assinados às 03:13:04Z |

Logs `apko-lock.log`, `apko-build.log`, `melange-keygen.log` e
`melange-build.log` nessa fixture. Docker exigiu execução autorizada após
bloqueio de socket no sandbox. Private keys e saídas temporárias não são
parte do diff. A reprodução adversarial original permanece na seção de
limitação; não foi substituída por esses positivos nem reexecutada aqui.
O lock efetivo registra somente `melange/keys/wolfi-signing.rsa.pub` em
`contents.keyring`; chave da fixture, chave atual e os dois downloads oficiais
originais permanecem byte a byte iguais.

## Arquivos do diff local

- Keyrings/chave: `distroless/image-base.yaml`,
  `melange/image-base-ca-certificates.yaml`, `melange/keys/wolfi-signing.rsa.pub`,
  `melange/keys/wolfi-signing-key.json`, `.gitignore`.
- Preflight/monitor: `Makefile`, `scripts/pipeline/artifacts/build_image.py`,
  `scripts/pipeline/governance/wolfi_trust.py`,
  `scripts/pipeline/governance/pin_inventory.py`,
  `.github/workflows/validate-base-images.yml`, `.github/workflows/pipeline-health.yml`,
  `tests/runtime/certificate_contract.py`.
- Testes: `tests/unit/pipeline/governance/test_wolfi_trust.py`,
  `test_pin_inventory.py` e `test_repository_layout.py` no mesmo diretório.
- Docs: `README.md`, `CONTRIBUTING.md`, `docs/README.md`,
  `docs/wolfi-signing-key.md`, `docs/m11-m04-operational-health.md`,
  `docs/repository-architecture.md` e os seis Markdown desta spec.

## Revisão, limites e hosted acceptance

Revisão arquitetural independente: concluída, conforme decisão trazida pelo
usuário; relatório separado não foi anexado ao repositório. Nova revisão da
entrega reformulada: **NOT RUN**. Hosted acceptance: **NOT RUN**.
Nenhuma publicação, promoção, alteração remota ou workaround zlib autorizado
ou executado. Evidência local não equivale a aceite hospedado.

Checks existentes preservados: Trivy, vulnerability policy, Cosign,
provenance, SBOM, promoção/stable read-back, OIDC/IAM, repositories e pins
das ferramentas não foram alterados. Nenhum workaround zlib, retry parcial,
mirror, serviço ou item proibido implementado.

Exclusividade foi retirada explicitamente do aceite local por decisão do
usuário, preservando a limitação e os controles existentes. P0-03 recebe o
requisito futuro de mirror/proxy controlado sem discovery e egress restrito
se a corporação exigir independência da origem; ver [handoff.md](handoff.md).
Nenhuma tecnologia ou infraestrutura corporativa foi implementada.
Não houve auto-aprovação; a nova revisão independente permanece pendente.
