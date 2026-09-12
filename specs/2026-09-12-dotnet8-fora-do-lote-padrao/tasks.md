# TASKS — 2026-09-12-dotnet8-fora-do-lote-padrao

## T01 — Política: exclusão versionada com ADR
- Critério: A02, N04, N05.
- Arquivos: `policies/operations/health.json` (campo `adr` em
  `exceptions.dotnet8`, `$comment` com a semântica de lote padrão),
  `policies/README.md` (consumidores e responsabilidade).
- [x] Implementar.
- [x] Verificar (lint A01/A02).
- [x] Registrar evidência.

## T02 — Lint do lote padrão
- Critério: A01, A03, N01–N05.
- Arquivos: `scripts/pipeline/catalog/default_batch.py` (novo),
  `tests/unit/pipeline/catalog/test_default_batch.py` (novo), `Makefile`
  (`lint-local` + `help`).
- Resultado esperado: `lint` reprova o estado atual (`dotnet8` nos três lotes)
  e aprova após T03; `list` imprime o lote efetivo.
- [x] Implementar.
- [x] Verificar (`make test-unit`, `make lint-local`).
- [x] Registrar evidência.

## T03 — Workflow: lote padrão sem dotnet8
- Critério: A01, A06, A07.
- Arquivos: `.github/workflows/workflow.yml` (três listas).
- [x] Implementar.
- [x] Verificar (lint, actionlint, hardening).
- [x] Registrar evidência.

## T04 — ADR e documentação
- Critério: A05.
- Arquivos: `docs/adr/README.md`, `docs/adr/0001-dotnet8-fora-do-lote-padrao.md`,
  `README.md`, `docs/README.md`, `docs/m11-m04-operational-health.md`,
  `docs/repository-architecture.md`, `scripts/README.md`, `CONTRIBUTING.md`,
  `RFC-013-Image-Base-Completa-com-Mermaid.md` (linha de decisão de catálogo).
- [x] Implementar.
- [x] Verificar (links locais, `check_ai_context`).
- [x] Registrar evidência.

## T05 — Verificação, revisão e evidência
- Critério: A01–A08, N01–N06.
- [x] Executar os comandos do plano e registrar exit codes.
- [x] Revisar o diff contra a spec e o aceite (auto-revisão identificada).
- [x] Preencher `evidence.md` e `handoff.md`.

## T06 — Findings da revisão independente (CHANGES REQUIRED, 12/09/2026)
- Critério: N07 (HIGH), N08 (MEDIUM), A02; Finding 3 (LOW) só documentação.
- Arquivos: `scripts/pipeline/catalog/default_batch.py` (forma canônica por
  job via `fullmatch`; `adr_problem`), `tests/unit/pipeline/catalog/test_default_batch.py`
  (`BatchFormTests`, `AdrTests`, dois testes de CLI), `docs/adr/README.md`
  (convenção que o lint aplica), `docs/adr/0001-…` (item 4 da decisão;
  comportamento real do dispatch), `README.md`, `policies/README.md`,
  `spec.md` (R3), `acceptance.md` (A02, N07, N08).
- [x] Implementar.
- [x] Verificar (suíte completa + negativos explícitos + reprodução manual).
- [x] Registrar evidência.

## T07 — Finding remanescente da 2ª revisão independente (MEDIUM, 12/09/2026)
- Critério: N08 (contenção física do ADR).
- Arquivos: `scripts/pipeline/catalog/default_batch.py` (`adr_problem`: raiz
  canonizada, componentes sem link, arquivo resolvido dentro de
  `<raiz>/docs/adr/`), `tests/unit/pipeline/catalog/test_default_batch.py`
  (symlink ancestral, raiz por link, CLI end-to-end), `docs/adr/README.md`
  (uma frase), `acceptance.md` (N08).
- [x] Implementar.
- [x] Verificar (suíte completa + cenários adversariais do reviewer).
- [x] Registrar evidência.

## Dependências externas
- Code owners: aprovação do PR (pendente).
- Runner hospedado: build diário `success` após o merge (NOT RUN).
- Wolfi: publicação de `dotnet-8-sdk ≥ 8.0.129-r1` (gatilho de reinclusão).
