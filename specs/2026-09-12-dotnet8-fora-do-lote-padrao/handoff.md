# HANDOFF — 2026-09-12-dotnet8-fora-do-lote-padrao

- Repositório, branch e commit base: `alric-containers-image-base`, `main`,
  `517d2bffab084bf7fe90881ef5f288db5cebcc3f` (= `origin/main` em 12/09/2026).
- Objetivo e pasta da spec: retirar `dotnet8` do lote padrão sem sair do
  catálogo, com exceção versionada + ADR + lint no check obrigatório;
  `specs/2026-09-12-dotnet8-fora-do-lote-padrao/`.
- Estado do diff, incluindo arquivos novos: working tree, sem commit/push.
  Novos: `scripts/pipeline/catalog/default_batch.py`,
  `tests/unit/pipeline/catalog/test_default_batch.py`, `docs/adr/README.md`,
  `docs/adr/0001-dotnet8-fora-do-lote-padrao.md`, esta pasta. Modificados:
  `.github/workflows/workflow.yml` (três lotes), `Makefile`,
  `policies/operations/health.json`, `policies/README.md`, `README.md`,
  `RFC-013-*.md`, `CONTRIBUTING.md`, `docs/README.md`,
  `docs/m11-m04-operational-health.md`, `docs/repository-architecture.md`,
  `docs/ai/PROJECT.md`, `scripts/README.md`. O working tree também carrega as
  alterações não commitadas da spec `2026-09-11-ai-workflow` (não desta entrega).
- Tasks concluídas: T01–T07 (T06 = três findings da 1ª revisão independente:
  forma canônica do lote por job, `adr` restrito a `docs/adr/NNNN-titulo.md`
  válido, documentação do dispatch; T07 = finding remanescente da 2ª revisão:
  contenção física do ADR — raiz canonizada, sem link em nenhum componente,
  arquivo resolvido dentro de `<raiz>/docs/adr/`); resultados em
  [evidence.md](evidence.md).
- Verificações e resultados (rodada 3): `make test-unit` 227 OK;
  `make test-integration` 20 OK; `make lint-local`, `make lint-shared`,
  `make lint-workflows`, `actionlint workflow.yml`, `tools/check_ai_context.py`
  e `git diff --check` com exit 0; negativos N07/N08 executados explicitamente
  e reproduzidos manualmente (exit 1). Aceite hospedado NOT RUN.
- Decisões e hipóteses pendentes: ADR-0001 em estado "Proposto" — passa a
  "Aceito" com a aprovação de code owner; `workflow_dispatch` de frameworks
  excluídos permanece permitido (reteste); `review_by` vencido é alerta de
  saúde, não falha de lint.
- Dependências/autorizações ainda necessárias: criar branch/commit/PR
  (EXTERNAL-WRITE, não solicitado); re-revisão independente final (estado:
  READY FOR FINAL INDEPENDENT RE-REVIEW) e aprovação de code owner; após o merge, observar o primeiro build diário (`success` com 16
  frameworks) e a saúde seguinte; reconciliar com o PR #50 (mesmas linhas de
  `workflow.yml`), deixando o lint decidir o lote final.
- Próximo passo: abrir o PR a partir de uma branch (ex.: `adr/dotnet8-lote-padrao`)
  com o diff desta spec; após o merge, registrar aqui o run do build diário e
  da saúde como evidência hospedada. Próxima fatia do roadmap sugerida:
  reconciliação/merge do PR #50 + biblioteca #4 (P0) — fora deste working tree.

Confirme o estado real do Git antes de continuar.
