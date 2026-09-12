# EVIDENCE — 2026-09-12-dotnet8-fora-do-lote-padrao

Estado: **VERIFICADO LOCALMENTE** (rodada 3, após a 2ª revisão
independente); aceite hospedado **NOT RUN**.

## Identidade

- Data e ambiente: 12/09/2026; macOS arm64 (Darwin 25.6.0), Python 3.9.6,
  PyYAML 6.0.3, actionlint 1.7.12 (Homebrew), `gh` autenticado (leitura),
  checkout `.reusable-workflows` em `0459275b4a2ffbe6e8961041e7b93b41e88ba215`.
- Branch e commit base: `main` = `517d2bffab084bf7fe90881ef5f288db5cebcc3f`
  (igual a `origin/main` após `git fetch`).
- Diff implementado: working tree, sem commit/push. Arquivos desta spec:
  `.github/workflows/workflow.yml`, `Makefile`, `policies/operations/health.json`,
  `scripts/pipeline/catalog/default_batch.py` (novo),
  `tests/unit/pipeline/catalog/test_default_batch.py` (novo),
  `docs/adr/README.md` e `docs/adr/0001-dotnet8-fora-do-lote-padrao.md` (novos),
  `README.md`, `RFC-013-Image-Base-Completa-com-Mermaid.md`, `CONTRIBUTING.md`,
  `docs/README.md`, `docs/m11-m04-operational-health.md`,
  `docs/repository-architecture.md`, `docs/ai/PROJECT.md`, `policies/README.md`,
  `scripts/README.md`, e esta pasta de spec. O working tree também contém as
  alterações ainda não commitadas da spec `2026-09-11-ai-workflow`
  (`AGENTS.md`, `.gitignore`, `CLAUDE.md`, `docs/ai/`, `prompts/`, `playbooks/`,
  `tools/`, trechos de `CONTRIBUTING.md`/`docs/README.md`), preservadas e não
  pertencentes a esta entrega.
- Ferramenta/sessão: Claude Code (Opus 5), implementação e auto-revisão na
  mesma sessão.

## Estado de partida (pesquisa, somente leitura)

| Fonte | Observação |
| --- | --- |
| `gh run list --branch main` | Push `34555637518` (`517d2bf`): 14 validações, 9 contratos e 14 publicações `success`; únicos `failure`: `Validate dotnet8`, `Build & push dotnet8`. Diário `34574793032` (11/09): mesmo padrão, run `failure`. |
| `gh run download 34574793032 -n build-scans-dotnet8-1` | 28 achados por arquitetura em 7 pacotes (`dotnet-8`, `dotnet-8-runtime`, `dotnet-8-sdk`, `aspnet-8-runtime`, targeting packs), todos `8.0.127-r0 → 8.0.129-r1`. |
| `packages.wolfi.dev/os/x86_64/APKINDEX.tar.gz` (12/09/2026) | `dotnet-8-sdk` e `aspnet-8-runtime` publicados até `8.0.127-r0`; `8.0.129-r1` inexistente. |
| `gh run view 34586962957` (saúde de 11/09) | Único `alert`: lacuna histórica de 24,08h do cron horário (expira da janela de 7 dias); `dotnet8` como `known`. |
| Lint novo contra a árvore **antes** da mudança | exit 1 com 4 erros: ADR ainda inexistente e `dotnet8` nos três lotes (`validate-pr`, `build-base-images`, `promote-stable`) — negativo real de N02. |

## Resultados

| Critério | Resultado | Comando, exit code e evidência |
| --- | --- | --- |
| A01 | PASS | `python3 -B -m scripts.pipeline.catalog.default_batch lint` → exit 0, "15 framework(s) no catálogo, 1 excluído(s), 3 job(s)". `list` → `catalog` 15, `excluded ["dotnet8"]`, `default_batch` 14, cada job com 14 nomes, `problems []`. `frameworks/dotnet8.yaml` sem diff. |
| A02 | PASS | `health.json` → `exceptions.dotnet8` com `reason`, `owner`, `review_by: 2026-10-09`, `adr: docs/adr/0001-dotnet8-fora-do-lote-padrao.md` (arquivo existe); `policies/README.md` lista os dois consumidores. Teste `test_the_exclusion_is_a_reviewed_decision_with_a_valid_adr` (renomeado na rodada 2; confere também `adr_problem`). |
| A03 | PASS | `make lint-local` → exit 0: hardening, `pin_inventory lint` (43 pins em 41 arquivos), `default_batch lint`. `grep default_batch Makefile` → alvo `lint-local`. |
| A04 | PASS | `make test-unit` → `Ran 213 tests … OK` (198 anteriores + 15 novos), incluindo `EvaluateTests.test_documented_exception_is_known_not_a_new_alert` e `test_expired_exception_becomes_an_alert_of_its_own`. `make lint-shared` → exit 0 ("Retenção e agendamento conferidos em 10 workflow(s)"). `operational_health.py` sem diff. |
| A05 | PASS | ADR e índice criados; 102 links relativos conferidos nos 15 arquivos Markdown tocados, 0 quebrados (script ad hoc); `python3 -B tools/check_ai_context.py` → exit 0. README, `policies/README.md`, `docs/README.md`, `docs/m11-m04-operational-health.md`, `docs/repository-architecture.md`, `scripts/README.md`, `CONTRIBUTING.md`, `docs/ai/PROJECT.md` e RFC-013 (linha do catálogo e linha da decisão) referenciam o ADR. |
| A06 | PASS | `FRAMEWORKS='["dotnet8"]' python3 -B -m scripts.pipeline.catalog.validate_inputs` → exit 0; `["dotnet7"]` → exit 1. `git status --short frameworks/ validate-base-images.yml build-base-images.yml promote-stable.yml` vazio. |
| A07 | PASS | `actionlint .github/workflows/workflow.yml` → exit 0; `make lint-local` (hardening) → exit 0; `make test-unit` 213 OK; `git diff --check` limpo. Nomes dos required checks inalterados (`test-promotion.yml` sem diff). |
| A08 | PASS | Nenhum comando `aws` executado na sessão; `policies/aws/` e `policies/operations/ecr-lifecycle.json` sem diff. |
| N01 | PASS | `LintTests.test_missing_framework_in_one_job_names_job_and_framework` |
| N02 | PASS | `LintTests.test_excluded_framework_present_in_the_batches_is_one_problem_per_job` + `CliTests.test_lint_fails_on_a_tree_where_the_batch_diverges` (exit 1, 3 `::error::`) + execução real do lint contra a árvore antiga (acima) |
| N03 | PASS | `LintTests.test_unknown_and_duplicated_names_are_rejected`, `test_exclusion_outside_the_catalog_is_a_problem`, `test_unreadable_batch_is_reported_not_ignored` |
| N04 | PASS | `ExclusionFieldTests` (campo ausente/vazio, `review_by` inválido, ADR inexistente, entrada não-objeto/`$comment`) |
| N05 | PASS | `LintTests.test_without_exclusions_the_batch_is_the_whole_catalog` |
| N06 | PASS | `test_expired_exception_becomes_an_alert_of_its_own` (existente, inalterado) |
| Integração | PASS | `make test-integration` → `Ran 20 tests … OK` (certificados, TLS, adaptadores, contrato compartilhado) |
| Aceite hospedado | NOT RUN | Build diário `success` com 16 frameworks e `pipeline-health` sem alerta novo exigem merge na `main` e o run agendado seguinte. Nenhum run hospedado deste working tree existe. |

## Revisão

Auto-revisão (mesma sessão), diff versus spec e aceite, com os itens do
prompt de revisão independente:

- Aceite não atendido: apenas o hospedado (NOT RUN, declarado).
- Regressão de segurança: nenhuma — gate de CVE, permissões, pins,
  concorrência, retenção e contrato compartilhado inalterados; o lint novo só
  acrescenta um modo de falha (fail closed) ao required check.
- Hipóteses implícitas (rodada 1): o lote de `build-base-images` é o literal
  JSON dentro da expressão `${{ … || '[…]' }}` — hipótese **refutada** pela
  revisão independente (Finding 1, abaixo): extrair o trecho `[…]` aceitava
  qualquer expressão em volta. Lote ilegível ou job renomeado é reportado
  como problema, não ignorado (teste `test_unreadable_batch_is_reported_not_ignored`).
  `workflow_dispatch` não é validado contra a exclusão — decisão registrada no
  ADR e na spec.
- Acoplamento: `default_batch.py` e `operational_health.py` leem a mesma
  chave `exceptions`; o lint rejeita entradas não-objeto porque a saúde as
  itera como frameworks. Documentado em `policies/README.md`.
- Duplicação: a leitura do catálogo (`frameworks/*.yaml`) existe inline em
  três domínios que não podem se importar; aceito como uma linha cada.
- Determinismo: ordem dos problemas segue `BATCH_JOBS`; datas via
  `date.fromisoformat`; sem rede nos testes novos.
- Documentação × implementação: README ("quatro lints offline"), políticas,
  saúde, arquitetura, mapa de IA e RFC-013 atualizados; o inventário M12
  (histórico) permanece verdadeiro e o ADR explicita a distinção gate × lote.
- Escopo: nenhuma alteração fora da spec; RFC-013 recebeu só duas linhas
  factuais (catálogo e decisão). Nenhuma operação AWS, commit ou push.

Achado corrigido durante a revisão: a justificativa da alternativa
"runtime-only" no ADR estava sem evidência; substituída pela lista real de
pacotes do artifact `build-scans-dotnet8-1` (run `34574793032`).

Revisão independente em contexto separado **não** foi executada nesta
sessão; recomendada antes da integração por tocar `workflow.yml` e
`policies/` (caminhos do CODEOWNERS).

## Rodada 2 — revisão independente (CHANGES REQUIRED)

Revisão independente em contexto separado, recebida em 12/09/2026, com três
findings. Correções feitas nesta sessão (Claude Code, Opus 5), no mesmo
working tree, sem commit/push. Escopo desta rodada: somente os findings e o
que os sustenta; PR #50, biblioteca #4, Renovate, IAM, Trivy, catálogo e
demais workflows não foram tocados.

### Findings recebidos e correções

| Finding | Problema demonstrado pelo reviewer | Correção |
| --- | --- | --- |
| 1 — HIGH | O lint extraía o trecho entre `[` e `]` do valor de `frameworks`; `${{ vars.DEFAULT_FRAMEWORKS \|\| '<lote>' }}` passava, tornando `vars.*` segunda fonte de verdade (podia omitir frameworks, reincluir `dotnet8`, ignorar a exceção). Invalidava R1/R3 em parte. | `parse_batch` confere o valor **inteiro** (`re.fullmatch`) contra uma forma canônica **por job**: `validate-pr` e `promote-stable` aceitam só um array JSON literal de nomes na forma que `validate_inputs` aceita; `build-base-images` aceita só `${{ github.event_name == 'workflow_dispatch' && inputs.frameworks \|\| '[…]' }}` com o array como fallback (prefixo/sufixo exatos via `re.escape`). Qualquer outro valor — `vars`, `env`, `secrets`, `inputs` sem a guarda, `fromJSON`, `format`, concatenação, fallback extra, literal puro no job de dispatch ou expressão de dispatch nos outros jobs, valor não-string, espaço sobrando — falha com mensagem que cita o job, o valor (truncado), a forma esperada e a razão ("precisa ser estático … não pode depender de fonte externa"). Sem parser de expressões: duas regex ancoradas. `batches()` passou a devolver o valor bruto; `lint()` é o único dono dos problemas (fail closed também em chamada direta). |
| 2 — MEDIUM | `adr` só testava `is_file()`: `README.md` e `/etc/hosts` eram aceitos; nada garantia decisão versionada em `docs/adr/` nem impedia caminho externo. | `adr_problem(adr, root)`: o caminho é conferido **no texto**, antes de tocar o disco — exatamente três segmentos `docs/adr/<nome>`, nome `NNNN-titulo.md` (`\d{4}-[a-z0-9]+(?:-[a-z0-9]+)*\.md`), o que exclui `/` inicial, `..`, `.`, subdiretório, barra invertida e `README.md`; depois arquivo regular existente (link simbólico recusado) cuja primeira linha começa com `# ADR-NNNN ` com o mesmo número do nome. Convenção registrada em `docs/adr/README.md` (fonte da regra, princípio 2 da constituição). `exclusions()` ganhou `root=` para os testes. |
| 3 — LOW | ADR dizia que "dispatch sem input" usa o lote padrão; o default do input é `["go1-26"]`, então dispatch sem alterar o input builda `go1-26`. | Só documentação: ADR-0001 (decisão 1) e comentário de `default_batch.py` descrevem o comportamento real — dispatch usa `inputs.frameworks` (default `["go1-26"]`); só input esvaziado cai no lote padrão. Default do workflow **não** alterado (a spec não exige). |

Reprodução dos findings contra o lint da rodada 1 (antes da correção), com
`--workflow`/`--policy` apontando para cópias temporárias da árvore real:
`vars.DEFAULT_FRAMEWORKS || '<lote de 14>'` → exit 0; `adr: README.md` →
exit 0; `adr: /etc/hosts` → exit 0. Os três confirmam o relatado.

### Testes adicionados (`tests/unit/pipeline/catalog/test_default_batch.py`, 15 → 26)

- `BatchFormTests` (N07): forma canônica aceita por job, espaços internos
  tolerados, `[]` aceito; 10 expressões dinâmicas × 3 jobs recusadas com
  "fora da forma canônica", "precisa ser estático" e "fonte externa" —
  o exemplo do reviewer (`vars.X || '<lote>'`), `toJSON(fromJSON(vars.X))`,
  `env.X`, `secrets.X`, `inputs.frameworks` só, `inputs.frameworks || '[…]'`
  sem guarda, `format('{0}', '[…]')`, expressão canônica com `|| vars.X`
  extra, `'[…]' ${{ vars.EXTRA }}` (concatenação), `${{ '[…]' }}`, e a
  canônica com espaço sobrando; cada job recusa a forma do outro; valores
  não-string/não-lista/nome fora da forma do catálogo recusados; o problema
  de forma é reportado uma vez e os outros jobs continuam conferidos.
- `AdrTests` (N08): 13 caminhos fora da convenção recusados sem tocar o
  disco (`root=/nonexistent`), incluindo os quatro do reviewer; arquivo
  inexistente, link simbólico, sem título e com número divergente recusados
  em diretório temporário; ADR válido em diretório temporário e o ADR-0001
  real aceitos; `exclusions()` prefixa o problema com a exceção.
- `CliTests.test_lint_fails_when_a_variable_can_replace_the_batch`: árvore
  temporária com o lote correto dentro de `${{ vars.DEFAULT_FRAMEWORKS || … }}`
  → `returncode != 0`, um `::error::` citando job, forma estática e fonte
  externa.
- `CliTests.test_lint_fails_when_the_adr_is_outside_docs_adr`: `README.md`,
  `/etc/hosts`, `../algum-arquivo.md`, `docs/adr/../../README.md` →
  `returncode != 0` cada um, um `::error::` por execução.
- Ajustados ao contrato novo: `RealTreeTests` (usa `parse_batch`/`adr_problem`),
  `test_unreadable_batch_is_reported_not_ignored` (mensagens novas),
  `test_adr_must_exist_in_the_repository` (mensagem nova); helper `run_cli`.

### Comandos executados e resultados

| Comando | Resultado |
| --- | --- |
| `make test-unit` | exit 0 — `Ran 224 tests … OK` (213 + 11) |
| `make test-integration` | exit 0 — `Ran 20 tests … OK` |
| `make lint-local` | exit 0 — hardening, `pin_inventory lint` (43 pins/41 arquivos), `default_batch lint` ("15 no catálogo, 1 excluído, 3 jobs") |
| `make lint-shared` | exit 0 — dependências e "Retenção e agendamento conferidos em 10 workflow(s)" |
| `make lint-workflows` | exit 0 — actionlint nos 8 workflows locais + 2 compartilhados |
| `actionlint .github/workflows/workflow.yml` | exit 0 |
| `python3 -B tools/check_ai_context.py` | exit 0 |
| `git diff --check` | exit 0 |
| `python3 -B -m unittest -v …BatchFormTests …AdrTests …CliTests.test_lint_fails_when_a_variable_can_replace_the_batch …CliTests.test_lint_fails_when_the_adr_is_outside_docs_adr` | `Ran 11 tests … OK` |
| `…LintTests …ExclusionFieldTests …test_validate_inputs` (invariantes 7–11) | `Ran 20 tests … OK` |
| Reprodução manual, lint corrigido, `--workflow` com `${{ vars.DEFAULT_FRAMEWORKS \|\| '<lote de 14>' }}` em `build-base-images` | exit 1 — `::error::` `build-base-images`: `frameworks` fora da forma canônica (…). O lote automático precisa ser estático — … — e não pode depender de fonte externa: vars, env, secrets, inputs, fromJSON, concatenação ou fallback dinâmico … |
| Segunda variação manual: `${{ toJSON(fromJSON(vars.PR_BATCH)) }}` em `validate-pr` + `${{ env.PROMOTE_BATCH }}` em `promote-stable` | exit 1 — dois `::error::`, um por job |
| Reprodução manual, `--policy` com `adr` = `README.md`, `/etc/hosts`, `../algum-arquivo.md`, `docs/adr/../../README.md`, `docs/adr/README.md` | exit 1 em cada um — ADR `…` precisa ser um caminho relativo `docs/adr/NNNN-titulo.md` (sem `..`, `/` inicial ou subdiretório) |
| `FRAMEWORKS='["dotnet8"]' python3 -B -m scripts.pipeline.catalog.validate_inputs` | exit 0 — reteste manual de `dotnet8` continua aceito (invariante 2) |
| `default_batch list` | `catalog` contém `dotnet8`; `excluded ["dotnet8"]`; lote 14; cada job 14; `problems []` (invariantes 1, 5, 6) |
| Conferência de links relativos nos 4 Markdown alterados nesta rodada | 45 links, 0 quebrados |
| `git diff --stat .github/workflows/workflow.yml Makefile policies/operations/health.json` | Somente o diff da rodada 1 (três linhas do lote; alvo `lint-local`; campo `adr` + `$comment`). Nada em `frameworks/`, `validate-base-images.yml`, `build-base-images.yml`, `policies/aws/` — gate Trivy, permissões, pins e default do dispatch intocados (invariantes 3, 4) |

### Arquivos alterados nesta rodada

`scripts/pipeline/catalog/default_batch.py`,
`tests/unit/pipeline/catalog/test_default_batch.py`, `docs/adr/README.md`,
`docs/adr/0001-dotnet8-fora-do-lote-padrao.md`, `README.md` (descrição do
lint), `policies/README.md` (forma dos lotes e do `adr`), e nesta pasta
`spec.md` (R3), `acceptance.md` (A02, N07, N08), `tasks.md` (T06),
`evidence.md`, `handoff.md`.

### Limitações restantes

- O lint aceita **uma** forma por job; reformatar a expressão de
  `build-base-images` (espaços, ordem dos operandos) reprova até voltar à
  forma canônica — intencional (fail closed), com a forma esperada na
  mensagem. O PR #50 mantém a mesma forma e só altera o array.
- O lint confere `workflow.yml` como texto YAML; não avalia expressões do
  GitHub nem impede que `build-base-images.yml` (o chamado) mude o que faz
  com `inputs.frameworks` — fora deste lint, coberto por `validate_inputs`
  em execução e por `lint-shared`.
- A validade do ADR é sintática (caminho, arquivo regular, título com o
  número); conteúdo e estado ("Proposto"/"Aceito") continuam sendo revisão
  humana de code owner.
- Auto-revisão do diff desta rodada pelo mesmo agente; a re-revisão
  independente ainda não aconteceu.
- Aceite hospedado: **continua NOT RUN** — nenhum run hospedado deste
  working tree existe; o build diário `success` com 16 frameworks e a saúde
  seguinte só podem ser observados após o merge.

## Rodada 3 — 2ª revisão independente (CHANGES REQUIRED, 1 finding MEDIUM)

A 2ª revisão independente (12/09/2026) fechou os findings HIGH e LOW e
manteve um MEDIUM no mecanismo de validação do ADR. Correção nesta sessão
(Claude Code, Opus 5), mesmo working tree, sem commit/push; escopo restrito
ao finding e ao que o sustenta.

### Finding remanescente e reprodução anterior

`adr_problem` só testava `is_symlink()` no arquivo final. Com `docs/adr`
(ou `docs`) sendo link simbólico para um diretório externo contendo
`0001-dotnet8-fora-do-lote-padrao.md`, o arquivo final não é link,
`is_file()` é verdadeiro e o ADR aceito vinha de fora do repositório.
Reproduzido no scratchpad antes da correção, com a mesma referência
`docs/adr/0001-dotnet8-fora-do-lote-padrao.md`:

| Cenário | `is_symlink()` do arquivo | `resolve()` | `adr_problem` (antes) |
| --- | --- | --- | --- |
| `repo/docs/adr -> externo/adr` | False | `…/external/adr/0001-…md` | `None` (aceito) |
| `repo/docs -> externo/docs` | False | `…/external/docs/adr/0001-…md` | `None` (aceito) |

### Correção (`adr_problem`, mantendo as verificações anteriores)

1. A raiz do repositório é canonizada sozinha: `repo = Path(root).resolve(strict=True)`
   (falha → problema). `docs/adr` é acrescentado **depois, no texto** — nunca
   `(root/'docs'/'adr').resolve()`, o que faria um `docs/adr` apontando para
   fora virar a nova raiz "permitida".
2. Cada componente do caminho relativo (`docs`, `docs/adr`, o arquivo) é
   recusado se for link simbólico, com mensagem nomeando o componente.
3. O arquivo precisa ser regular e `path.resolve(strict=True).parent` tem de
   ser exatamente `repo/docs/adr` — o diretório permitido é construído a
   partir da raiz canônica, logo a contenção em `docs/adr/` implica a
   contenção no repositório.
4. Título `# ADR-NNNN` como antes.

Sem framework genérico: `pathlib` puro, ~15 linhas, determinístico.

### Testes adversariais adicionados (26 → 29)

- `AdrTests.test_symlinked_ancestors_cannot_move_docs_adr_outside_the_repository`:
  `docs/adr -> externo` e `docs -> externo` (cada um com arquivo de nome e
  título válidos; o teste afirma primeiro que o arquivo final **não** é
  link e `is_file()` é verdadeiro — o bypass — e depois que `adr_problem`
  nomeia o componente e `exclusions()` devolve 1 problema);
  `docs/adr/link -> externo` (recusado pela regra textual de subdiretório,
  sem tocar o disco).
- `AdrTests.test_a_symlinked_repository_root_is_canonicalised_not_rejected`:
  raiz acessada por link (`alias -> real`) continua aceita — só a raiz é
  canonizada; raiz inexistente → "não resolve".
- `CliTests.test_lint_fails_when_docs_adr_is_a_symlink_out_of_the_repository`:
  cópia mínima do módulo em diretório temporário (ROOT vem de `__file__`)
  com `docs/adr -> externo` → `returncode != 0`, um `::error::` com
  "`docs/adr` é link simbólico".
- Existente ajustado: symlink no arquivo final continua reprovado
  (`test_missing_symlinked_or_untitled_adr_files_are_rejected`), agora
  pela verificação de componentes, com mensagem "é link simbólico" em vez
  de "não existe".

### Comandos executados e resultados

| Comando | Resultado |
| --- | --- |
| `make test-unit` | exit 0 — `Ran 227 tests … OK` (224 + 3) |
| `make test-integration` | exit 0 — `Ran 20 tests … OK` |
| `make lint-local` | exit 0 — `default_batch lint`: "15 no catálogo, 1 excluído, 3 jobs" |
| `make lint-shared` | exit 0 |
| `make lint-workflows` | exit 0 |
| `python3 -B tools/check_ai_context.py` | exit 0 |
| `git diff --check` | exit 0 |
| Cenário do reviewer, `adr_problem('docs/adr/0001-…md', repo_com_docs_adr_link)` | `'ADR …: \`docs/adr\` é link simbólico; o ADR precisa estar fisicamente em docs/adr/ do repositório'` (≠ None) |
| Cenário do reviewer, `docs -> externo` | `'ADR …: \`docs\` é link simbólico; …'` (≠ None) |
| CLI `default_batch lint` em cópia do repositório com `docs/adr -> externo` | exit 1, 1 `::error::` |
| CLI `default_batch lint` em cópia com `docs -> externo` | exit 1, 1 `::error::` |
| `adr_problem('docs/adr/0001-dotnet8-fora-do-lote-padrao.md')` na árvore real | `None` (aceito); `default_batch lint` na árvore real exit 0 |
| HIGH fechado — `BatchFormTests` + CLI `vars`; manual `vars.DEFAULT_FRAMEWORKS \|\| '<lote>'` e `fromJSON(vars)`/`env` | OK; exit 1 (1 erro) e exit 1 (2 erros) — sem regressão |
| LOW fechado — `workflow.yml` linha 51 `default: '["go1-26"]'` inalterado; ADR-0001 descreve o default | sem regressão |
| `FRAMEWORKS='["dotnet8"]' validate_inputs` | exit 0 |

### Arquivos alterados nesta rodada

`scripts/pipeline/catalog/default_batch.py` (`adr_problem`),
`tests/unit/pipeline/catalog/test_default_batch.py`, `docs/adr/README.md`
(uma frase da convenção), e nesta pasta `acceptance.md` (N08), `tasks.md`
(T07), `evidence.md`, `handoff.md`. `workflow.yml`, `health.json`,
`Makefile`, catálogo e demais workflows não foram tocados.

### Limitações

- A contenção é por resolução de caminho e ausência de links nos
  componentes; não cobre bind mounts nem sistemas de arquivos que
  apresentem o mesmo diretório sob dois caminhos canônicos — fora do
  modelo de ameaça de um checkout Git (que versiona links, não mounts).
- Em sistemas de arquivos sem distinção de maiúsculas, `resolve()` não
  normaliza caixa; a regra textual (nome em minúsculas) é o que fixa o nome.
- Auto-revisão do diff desta rodada, identificada como tal.
- Aceite hospedado: **continua NOT RUN** — nenhum run hospedado deste
  working tree.

## Rodada 4 — reconciliação com a `main` após #4 e #50 (13/09/2026)

Rebase de `feat/dotnet8-default-batch-governance` (c79bcf9) sobre
`origin/main` = `914e287` (merge do #50; a `main` já continha o #49 com
`go1-25-dev`/`java25-dev`). Conflitos e resolução:

| Arquivo | Conflito | Resolução |
| --- | --- | --- |
| `.github/workflows/workflow.yml` (3 lotes) | `main` acrescentou `java25-dev` e `go1-25-dev` e manteve `dotnet8`; a branch removia `dotnet8` da lista antiga | Lista da `main` **sem** `dotnet8` nos três jobs — exatamente `catálogo − exclusões`; forma canônica preservada |
| `RFC-013` (tabela de decisões) | linha de certificados reescrita pelo #50; linha de catálogo reescrita por este PR | Linha de certificados da `main`; linha de catálogo do ADR, sem a frase "`go1-25` e `java25` sem variante `-dev`" (o #49 entregou as variantes) |

Catálogo passou de 15 para 17; lote padrão de 14 para **16**. Os critérios
prospectivos (A01, dependência hospedada da spec, consequência do ADR) foram
atualizados para 16; menções a 14/15 em runs de 10–11/09 são históricas e
ficaram como estavam. `default_batch list` na árvore rebaseada: `catalog` 17,
`excluded ["dotnet8"]`, `default_batch` 16, cada job 16, `problems []`.
Aceite hospedado: **continua NOT RUN**.

## Limites e resultado

- Implementado e comprovado localmente: lote padrão = catálogo − `dotnet8`,
  lint no check obrigatório com positivos/negativos (incluindo forma canônica
  do lote, rodada 2, e contenção física do ADR, rodada 3), política com ADR,
  documentação consistente.
- Não executado: run hospedado do build diário e da saúde após o merge;
  aprovação de code owner; commit/push/PR (EXTERNAL-WRITE, não solicitados).
- Depende de terceiros: aceite formal da decisão (Containers Products +
  Owner RFC) — o ADR nasce "Proposto"; publicação do pacote corrigido pelo
  Wolfi para a reinclusão.
- Interação com o PR #50 (`fix/image-composition`): ele edita as mesmas três
  linhas de `workflow.yml` (acrescenta `java25-dev`/`go1-25-dev` e mantém
  `dotnet8`). Ao reconciliar, o lint desta entrega reprova qualquer lote que
  reintroduza `dotnet8` ou omita as variantes novas — o resultado final é
  verificável, não presumido.
