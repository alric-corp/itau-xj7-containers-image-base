# ACCEPTANCE — 2026-09-12-dotnet8-fora-do-lote-padrao

| ID | Requisito | Critério observável | Comando ou inspeção |
| --- | --- | --- | --- |
| A01 | R1 | Os três lotes de `workflow.yml` (`validate-pr`, `build-base-images`, `promote-stable`) contêm exatamente os 16 frameworks do catálogo (17) menos `dotnet8`, sem repetição; `dotnet8.yaml` continua no catálogo | `python3 -B -m scripts.pipeline.catalog.default_batch lint` (exit 0) e `python3 -B -m scripts.pipeline.catalog.default_batch list` (JSON com 16 nomes, `dotnet8` em `excluded`) |
| A02 | R2 | `policies/operations/health.json` → `exceptions.dotnet8` tem `reason`, `owner`, `review_by` (ISO) e `adr` = `docs/adr/0001-dotnet8-fora-do-lote-padrao.md`, aceito por `adr_problem` (caminho na convenção, arquivo regular, título `# ADR-0001`); `policies/README.md` declara os dois consumidores | Lint A01 + `test_the_exclusion_is_a_reviewed_decision_with_a_valid_adr` + inspeção do README de políticas |
| A03 | R3 | O lint faz parte de `make lint-local` (alvo do required check `lint-workflows`) e de `lint-local` no Makefile; `make lint-local` sai com 0 na árvore atual | `make lint-local` (exit 0); `grep default_batch Makefile` |
| A04 | R4 | `operational_health.evaluate` classifica `dotnet8` como `known` e gera `exception_review` quando `review_by` vence; `operational_health lint` continua limpo | `make test-unit` (testes existentes `EvaluateTests`) e `make lint-shared` (exit 0) |
| A05 | R5 | `docs/adr/0001-dotnet8-fora-do-lote-padrao.md` existe com contexto, decisão, consequências, alternativas, critério de reinclusão e data de revisão; `docs/adr/README.md` indexa; README, `policies/README.md`, `docs/m11-m04-operational-health.md`, `docs/README.md` e RFC-013 (linha de catálogo) referenciam o ADR; links locais válidos | `python3 -B tools/check_ai_context.py` (links dos arquivos de IA) + inspeção dos links Markdown novos |
| A06 | R6 | `validate_inputs` aceita `["dotnet8"]` (catálogo inalterado); nenhuma alteração em `frameworks/dotnet8.yaml`, `validate-base-images.yml`, gate Trivy ou executor compartilhado | `git diff --stat` (arquivos tocados) + teste unitário existente de `validate_inputs` |
| A07 | R1, R3 | Nenhum required check muda de nome; `actionlint` e o lint de hardening continuam aprovados; a suíte unitária inteira passa, incluindo os testes novos do lint | `make test-unit`, `make lint-local`, `actionlint .github/workflows/workflow.yml` (exit 0) |
| A08 | R7 | Nenhum comando AWS/ECR foi executado nesta entrega; nenhuma política em `policies/aws/` ou `policies/operations/ecr-lifecycle.json` alterada | Evidência da sessão + `git diff --stat` |

## Negativos e limites

| ID | Cenário que deve falhar | Verificação |
| --- | --- | --- |
| N01 | Framework do catálogo não excluído ausente de um dos lotes (ex.: remover `nodejs22` só de `promote-stable`) | Teste unitário: `lint` devolve problema citando o job e o framework |
| N02 | Framework excluído presente em um lote (o estado anterior a esta entrega: `dotnet8` nos três lotes) | Teste unitário com fixture do workflow antigo: três problemas, um por job |
| N03 | Nome fora do catálogo em um lote, ou nome repetido | Teste unitário: problema por nome desconhecido/duplicado |
| N04 | Exclusão sem `reason`/`owner`/`review_by`/`adr`, `review_by` inválido (`2026-13-40`) ou exclusão de framework inexistente | Teste unitário: um problema por campo/entrada |
| N05 | `exceptions` ausente ou `null` na política: comportamento definido (lista vazia), lote = catálogo | Teste unitário |
| N06 | Exceção com `review_by` vencido continua virando alerta de saúde (comportamento existente preservado) | `test_expired_exception_becomes_an_alert_of_its_own` (existente) |
| N07 | `frameworks` de um job escrito como expressão que permite a uma fonte externa substituir o lote, mesmo com o literal correto dentro: `${{ vars.DEFAULT_FRAMEWORKS \|\| '<lote>' }}` (exemplo do reviewer), `fromJSON(vars.*)`, `env.*`, `secrets.*`, `inputs.frameworks` sem a guarda de evento, `format(...)`, concatenação, fallback extra, literal puro em `build-base-images` ou expressão de dispatch em `validate-pr`/`promote-stable` | `BatchFormTests` (unitário, por job) + `CliTests.test_lint_fails_when_a_variable_can_replace_the_batch` (exit ≠ 0, mensagem cita forma estática e fonte externa) |
| N08 | `adr` fora da convenção: `README.md`, `/etc/hosts`, `../algum-arquivo.md`, `docs/adr/../../README.md`, `docs/adr/README.md`, subdiretório, nome fora de `NNNN-titulo.md`, arquivo inexistente, link simbólico no arquivo **ou em qualquer componente ancestral** (`docs/adr -> externo`, `docs -> externo`, `docs/adr/link -> externo`), arquivo que resolva para fora de `<raiz canônica>/docs/adr/`, título ausente ou com número diferente. Deve passar: `docs/adr/0001-dotnet8-fora-do-lote-padrao.md`, inclusive com a raiz do repositório acessada por link simbólico | `AdrTests` (unitário) + `CliTests.test_lint_fails_when_the_adr_is_outside_docs_adr` (exit ≠ 0 para os quatro caminhos do reviewer) + `CliTests.test_lint_fails_when_docs_adr_is_a_symlink_out_of_the_repository` (exit ≠ 0 end-to-end) |

## Aceite externo

| Owner | Evidência exigida | Estado nesta entrega |
| --- | --- | --- |
| Code owners | Aprovação do PR (política e workflow são caminhos do CODEOWNERS) | Pendente — EXTERNAL-WRITE |
| Runner hospedado | Primeiro build diário após o merge com conclusão `success` (14 publicações) e `pipeline-health` subsequente sem alerta além dos históricos que expiram da janela | NOT RUN — não existe execução hospedada deste working tree |

Um critério obrigatório não executado impede declarar verificação completa:
A01–A08 e N01–N08 são verificáveis localmente; o aceite hospedado permanece
NOT RUN até o merge.
