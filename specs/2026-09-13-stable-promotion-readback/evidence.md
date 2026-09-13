# EVIDENCE — P1-01

Estado: **VERIFICADO LOCALMENTE; AGUARDANDO REVISÃO INDEPENDENTE**.
HOSTED ACCEPTANCE = NOT RUN.

## Identidade
- Data: 13/09/2026 UTC (12/09 no fuso America/Sao_Paulo), execução por volta
  de 01:22–01:26 UTC.
- Base: main `466d5c94790370e4620cd00721adbcebdaaf2129`, igual a origin/main
  ao reconstruir o estado. Nenhum commit, push ou PR realizado.
- Ferramenta: Codex, implementador principal; sem auto-aprovação.
- Working tree preexistente: configuração de IA não commitada. Os 31 arquivos
  locais preexistentes foram comparados por SHA-256 antes/depois, sem alteração.
- Ambiente observado: macOS arm64, Python 3.9.6, actionlint 1.7.12.
- Checkout compartilhado local: `7a9b055a462eeb8552d3404c26538b44e8ccd83f`.

## Current state reconstruído

As conclusões abaixo usam código da main e consultas remotas somente leitura,
não a situação anterior descrita nos handoffs históricos.

- A main movia stable em `promote-stable.yml` e calculava `PROMOTED` somente
  por `steps.promote.outcome == 'success'`. P1-01 continuava aberto.
- `recover-stable.yml` já fazia DescribeImages por `imageTag=stable`, comparava
  com o destino e abortava antes da evidência em divergência. Seu comentário
  sobre existir read-back na promoção normal estava adiantado em relação ao código.
- `verify_publication.py` compara SHA-256 dos bytes remotos do índice com
  digest validado/copied/image_ref e valida ambos manifests. O publicador
  passa esse mesmo digest para assinatura Cosign e subject-digest de provenance.
  `verify_promotion.py` verifica a referência por esse digest e exige exatamente
  amd64/arm64 em um índice/list. Portanto a identidade comparada é o índice
  multiarch, nunca o manifest de uma arquitetura.
- [Run pós-merge 34727294191](https://github.com/alric-corp/alric-containers-image-base/actions/runs/34727294191):
  push em `466d5c9`, tentativa 1, 00:10:32Z–00:20:47Z em 13/09. Os 13 artifacts
  bloqueados foram consultados: todos têm somente CVE-2026-85091 em `zlib`,
  MEDIUM, `1.3.2-r5` → `1.3.3-r0`, nas duas arquiteturas, exit 1 sem erro
  operacional de scan. Exemplo: `build-scans-nodejs22-1`, artifact 10308087890,
  [job 103643612411](https://github.com/alric-corp/alric-containers-image-base/actions/runs/34727294191/job/103643612411).
- APKINDEX [x86_64](https://packages.wolfi.dev/os/x86_64/APKINDEX.tar.gz) e
  [aarch64](https://packages.wolfi.dev/os/aarch64/APKINDEX.tar.gz) consultados
  em ~01:16Z: maior versão de zlib listada `1.3.2-r5`; `1.3.3-r0` ausente.
  Classificação da cadeia investigada: **UPSTREAM_BLOCKER**; nenhum indício
  de PROJECT_BUG nessa cadeia. Isso não afirma ausência universal de bugs.
- No executor fixado em `7a9b055`, o upload `validated-oci-*` depende do scan
  bem-sucedido. O contrato de nodejs22 registra artifact ausente no
  [job 103644085161](https://github.com/alric-corp/alric-containers-image-base/actions/runs/34727294191/job/103644085161).
  `build-base-images.yml` exige artifact validado e contrato funcional antes de
  publicar. Essas falhas são consequências do scan fail-closed.
- P1-02 não participou desse run, pois `run_attempt=1`. Não foi implementado
  nem avaliado como parte desta entrega.
- O run publicou `go1-26` e `go1-26-dev` (artifacts `publication-go1-26-1`
  10309005185 e `publication-go1-26-dev-1` 10308044371); contrato go1-26 passou.
  Disponibilidade/elegibilidade atual no ECR **não consultada**.

## Implementação e arquivos desta entrega

| Arquivo | Mudança |
| --- | --- |
| `.github/workflows/promote-stable.yml` | Read-back após retag; recorder exige ambos passos bem-sucedidos, confirmed e igualdade; motivo da falha preservado |
| `scripts/pipeline/release/verify_stable.py` (novo) | DescribeImages por stable, validação de resposta única/tag/repo/índice/digest; persistência fail-closed |
| `scripts/pipeline/release/find_promotion_candidate.py` | Inicializa campos de evidência; seleção, soak e quarentena intactos |
| `tests/unit/pipeline/release/test_verify_stable.py` (novo) | 17 testes com subprocesso AWS simulado, recorder real do YAML e regressão de recovery |
| `tests/unit/pipeline/release/test_find_promotion_candidate.py` | Asserções de evidência inicial, sem alterar o contrato dos outputs |
| `README.md` | Fluxo de read-back, campos, significado da falha e limite temporal |
| Esta pasta, seis arquivos Markdown | Spec, plano, tasks, aceite, evidence e handoff |

Reutilizados `require_digest_reference`, `IMAGE_INDEX_TYPES` e `write_evidence`.
Não foi criada uma camada genérica de registry nem modificado recovery/publicação.
O helper nunca marca promoted=true; só o recorder o faz após sucesso da escrita,
sucesso do read-back, status confirmed e igualdade dos digests. Em consulta
iniciada, estado failed/promoted=false é gravado antes de executar AWS.

## Resultados dos aceites locais

| Critério | Resultado | Evidência |
| --- | --- | --- |
| A01 | PASS local | `test_success_uses_the_published_index_identity_and_records_both_digests`: publica/verifica fixture de índice e executa read-back + recorder, exit 0, promoted=true |
| A02 | PASS local | `test_digest_mismatch_fails_even_after_successful_tag_write` e `test_cli_process_exits_nonzero_on_digest_mismatch`: exit 1, mismatch, promoted=false |
| A03 | PASS local | Stable ausente por lista vazia ou ImageNotFoundException: exit 1, failed |
| A04 | PASS local | Erro AWS, timeout de 60s ou aws indisponível: exit 1, failed, sem digest observado |
| A05 | PASS local | JSON vazio/malformado/tipo incorreto, digest ausente/inválido, múltiplos resultados, chaves duplicadas, paginação incompleta, tag/repo incorretos e manifest individual rejeitados |
| A06 | PASS local | Recorder extraído do YAML executado em shell: estados confirmed/mismatch/failed/not_run, ambos digests preservados; escrita sozinha/skip/falha anterior não gera promoted=true |
| A07 | PASS local | Diff restrito, regressões de seleção/assinatura/provenance/publicação, ordem e guards do workflow e lints aprovados |
| A08 | PASS local | Shell real de read-back do recovery, com AWS simulado: sucesso, mismatch, vazio, None e erro AWS; workflow recovery e verificador comum sem diff |

## Verification results

| Comando | Exit | Resultado observado |
| --- | --- | --- |
| `make test-unit` | 0 | 251 testes OK, incluindo 17 novos; 4,706s |
| `make test-integration` (sandbox) | 2 | 24 testes, 1 erro: PermissionError ao abrir socket TLS; limitação do sandbox |
| `make test-integration` (fora do sandbox, autorizado) | 0 | 24 testes OK; 11,700s |
| `make lint-local` | 0 | Hardening, 49 pins em 47 arquivos; lote 17 no catálogo/1 excluído/3 jobs |
| `make lint-shared` | 0 | SHA/inputs/hardening; retenção/agendamento em 11 workflows |
| `make lint-workflows` | 0 | YAML locais e executores compartilhados no pin exigido |
| `actionlint .github/workflows/promote-stable.yml .github/workflows/recover-stable.yml` | 0 | Sem diagnósticos |
| `python3 -B tools/check_ai_context.py` | 0 | Arquivos/imports/links locais OK |
| `git diff --check` | 0 | Sem erros de whitespace |
| Conferência de invariantes contra HEAD (YAML/AST/diff) | 0 | Gates anteriores ao retag, permissões, concorrência, resumo e funções de seleção intactos; recovery/publicação/scans/políticas/imagens sem diff |
| Whitespace dos oito arquivos novos + SHA-256 do trabalho preexistente | 0 | Nenhum diagnóstico de whitespace; 31 arquivos preexistentes idênticos |
| Negativos A02 executados explicitamente (comando abaixo) | 0 | 2 testes OK; cada um exige exit 1 da implementação |

Comando negativo explícito:

```sh
python3 -B -m unittest \
  tests.unit.pipeline.release.test_verify_stable.StableReadBackTests.test_digest_mismatch_fails_even_after_successful_tag_write \
  tests.unit.pipeline.release.test_verify_stable.StableReadBackTests.test_cli_process_exits_nonzero_on_digest_mismatch -v
```

Logs locais: `/private/tmp/p1-01-test-unit.log`,
`/private/tmp/p1-01-test-integration.log`,
`/private/tmp/p1-01-test-integration-unsandboxed.log`,
`/private/tmp/p1-01-lint-local.log`, `/private/tmp/p1-01-lint-shared.log`,
`/private/tmp/p1-01-lint-workflows.log`, `/private/tmp/p1-01-negative-mismatch.log`.
Esses logs são temporários; comandos e resultados necessários estão registrados
aqui e os testes versionáveis reproduzem os cenários.

## Evidence observada em execução local

Saídas geradas pelo helper e recorder reais com ECR simulado. Os digests abaixo
são fixtures locais, **não imagens hospedadas**. Captura adicional em
`/private/tmp/p1-01-readback-results.json`.

Sucesso (CLI exit 0):

```json
{
  "candidate_digest": "sha256:90e3a1c8cae02399a221f9b35c0d15f5724eb32890996a0634ebafab95a0a4e6",
  "stable_digest_observed": "sha256:90e3a1c8cae02399a221f9b35c0d15f5724eb32890996a0634ebafab95a0a4e6",
  "read_back_status": "confirmed",
  "promoted": true
}
```

Mismatch (CLI exit 1):

```json
{
  "candidate_digest": "sha256:90e3a1c8cae02399a221f9b35c0d15f5724eb32890996a0634ebafab95a0a4e6",
  "stable_digest_observed": "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
  "read_back_status": "mismatch",
  "promoted": false
}
```

Ausência, erro de registry e resposta vazia: CLI exit 1, observed=null,
status=failed, promoted=false. Sem seleção/read-back: ambos digests null,
status=not_run, promoted=false.

## Revisão
Revisão independente **NOT RUN**; será realizada depois por outro modelo.
Conferência técnica do próprio diff e execução de testes são trabalho do
implementador, não auto-aprovação. Um subagente foi usado somente para leitura
do estado anterior e evidências de zlib, sem editar nem revisar a implementação.

## Known limitations / hosted acceptance / scope

- HOSTED ACCEPTANCE = **NOT RUN**. Nenhuma tag ECR foi movida nesta sessão.
  Unit tests simulam exclusivamente AWS; executar o recorder e shell do recovery
  localmente não comprova a orquestração completa do GitHub Actions/ECR.
- Após merge, provar seleção → verificação → re-scan → escrita → read-back
  por stable → igualdade do índice → artifact final armazenado. Go só pode
  ser escolhido se ainda disponível e elegível; não presume bypass do soak.
- Leitura limitada a 60s, sem loop de retry na implementação; eventual atraso
  de visibilidade/erro falha fechado. A tag pode ter sido movida apesar da
  falha; não há rollback automático. Escritores externos podem mudar a tag
  depois da observação; concorrência existente foi preservada.
- Cancelamento abrupto pode impedir upload final, como já ocorria com os
  guards `!cancelled()`. Isso não autoriza declarar promoção bem-sucedida.
- Sem mudanças em Trivy/CVE, IAM/OIDC/Sigstore, recovery, publicação, políticas,
  catálogo, partial retry ou nos demais temas excluídos pelo pedido.
- Sem commit, push, PR ou aprovação desta entrega.
