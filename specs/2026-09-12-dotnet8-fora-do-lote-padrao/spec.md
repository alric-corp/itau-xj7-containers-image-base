# SPEC — 2026-09-12-dotnet8-fora-do-lote-padrao

Item do roadmap consolidado da RFC-013: **"dotnet8 fora do lote padrão"**
(P1 · Fase 1 · decisão arquitetural de catálogo · owner Containers Products
+ Owner RFC).

## Objetivo

O build diário e o `validate-pr` terminam em `failure` todos os dias por causa
de um único framework, `dotnet8`, cujo scan bloqueia com CVEs cuja correção
(`8.0.129-r1`) o repositório Wolfi consultado não publica (máximo
`dotnet-8-sdk 8.0.127-r0`, conferido em 09/09/2026 e novamente em
12/09/2026). Rebuild não resolve; o framework nunca produziu artifact aprovado,
nunca publicou e nunca teve `stable`. Um vermelho crônico treina quem lê a
ignorar o vermelho — e o critério de saída da Fase 1 exige build diário
`success`.

Resultado observável: `dotnet8` deixa de fazer parte do **lote padrão** dos
três chamadores (`validate-pr`, `build-base-images`, `promote-stable`) sem
sair do catálogo, com a exclusão registrada em lista versionada (motivo,
dono, `review_by`, ADR) e um lint offline no check obrigatório que impede o
lote padrão de divergir de `catálogo − exclusões`.

## Requisitos

- R1: o lote padrão de cada um dos três chamadores em `.github/workflows/workflow.yml`
  é exatamente `catálogo (frameworks/*.yaml) − frameworks excluídos`, sem
  repetição. `dotnet8` é o único excluído nesta entrega.
- R2: a lista de frameworks excluídos é versionada em `policies/` e revisada por
  code owner; cada entrada tem `reason`, `owner`, `review_by` (data ISO válida)
  e `adr`, e refere-se a um framework existente no catálogo. A lista é a mesma
  que a saúde operacional já usa para classificar a ausência de publicação/promoção
  como `known` (uma única fonte de verdade, sem duplicar motivo/dono/data).
- R3: um lint offline determinístico, executado por `make lint-local` (parte do
  required check `lint-workflows`), falha quando: um framework do catálogo não
  excluído está ausente de algum lote padrão; um framework excluído (ou
  inexistente no catálogo) aparece em algum lote padrão; um lote tem nome
  repetido; uma exclusão não tem os campos obrigatórios ou `review_by` não é
  data ISO válida; uma exclusão aponta para framework fora do catálogo; o
  valor de `frameworks` de um job não é o literal canônico (array JSON em
  `validate-pr`/`promote-stable`; em `build-base-images`, exatamente a
  expressão do input de dispatch com o array como fallback) — qualquer
  expressão que permita a `vars`, `env`, `secrets`, `inputs` sem a guarda,
  `fromJSON`, concatenação ou fallback substituir o lote é recusada; `adr`
  não é caminho relativo `docs/adr/NNNN-titulo.md` para arquivo regular
  existente com título `# ADR-NNNN` (sem caminho absoluto, `..` ou link).
  (As duas últimas condições vieram da revisão independente de 12/09/2026.)
- R4: a saúde operacional continua reportando o framework excluído como `known`
  (não como alerta novo) e continua gerando alerta próprio quando `review_by`
  vencer. Nenhum limite de alerta é relaxado.
- R5: a decisão fica registrada em um ADR versionado (`docs/adr/`), com contexto,
  decisão, consequências, alternativas rejeitadas, critério de reinclusão e data
  de revisão; a documentação do produto (README, políticas, saúde, RFC-013)
  aponta para ele onde descreve o catálogo ou o lote.
- R6: `frameworks/dotnet8.yaml` permanece no catálogo, sem alteração.
  `workflow_dispatch` com `["dotnet8"]` continua sendo entrada válida, e o gate
  de CVE continua idêntico: é assim que a reinclusão será testada quando o Wolfi
  publicar o pacote corrigido.
- R7: nenhuma operação AWS/ECR; o repositório `image-base-dotnet8`, sua
  configuração de imutabilidade e a ausência de `stable` não são tocados por
  esta mudança. Nenhuma exceção ao gate de CVE é criada.

## Restrições e invariantes

- Não neutralizar gate nenhum: a reprovação de `dotnet8` no scan é correta e
  continua acontecendo em execução manual. O que muda é não pedir esse build
  no lote automático enquanto a correção não existir na origem.
- Manter os nomes dos required checks (`test`, `lint-workflows`) e a cobertura
  dos filtros de path do pipeline.
- Não alterar pins, permissões, concorrência, retenção nem o contrato com o
  executor compartilhado.
- Não duplicar regras em instruções de IA; o ADR e a política são as fontes.
- Domínios Python: o lint entra em `scripts/pipeline/catalog/` e lê apenas
  arquivos (catálogo, política, workflow), sem importar outros domínios.

## Fora do escopo

- Merge/rebase do PR #50 (`fix/image-composition`) e do PR #4 da biblioteca:
  aceite hospedado separado, EXTERNAL-WRITE. O PR #50 altera as mesmas linhas
  de `workflow.yml` (adiciona `java25-dev`/`go1-25-dev`); o lint desta entrega
  passa a proteger a reconciliação.
- Variante `-dev` ou contrato funcional para `dotnet8` (M07/M08).
- Remoção de `dotnet8` do catálogo ou do ECR; qualquer alteração em AWS.
- Bloquear `workflow_dispatch` de frameworks excluídos.
- Falhar o lint por `review_by` vencido: a data vencida é alerta de saúde
  (diário), não bloqueio de todos os PRs.
- Atualização completa da RFC-013 (item P1 próprio); aqui só a linha da decisão
  de catálogo passa a refletir o ADR.

## Dependências

| Owner | Ação | Bloqueia esta entrega? |
| --- | --- | --- |
| Code owners (`@alric-corp/github_xj7_maintainer`, `@vigcf`) | Revisar e aprovar o PR com o ADR e a política | Bloqueia a integração, não a implementação local |
| Runner hospedado (`main`) | Build diário `0 3 * * *` concluir `success` com 16 frameworks (catálogo 17 − `dotnet8`); `pipeline-health` sem alerta novo | Aceite hospedado posterior ao merge (NOT RUN nesta sessão) |
| Wolfi (`packages.wolfi.dev/os`) | Publicar `dotnet-8-sdk ≥ 8.0.129-r1` | Não bloqueia; é o gatilho da reinclusão |

## Conclusão

Ver [acceptance.md](acceptance.md). Validação local não comprova o build
diário hospedado; esse aceite fica registrado como NOT RUN até o primeiro
run agendado após o merge.
