# PLAN — P1-01

## Pesquisa
Base real: main `466d5c94790370e4620cd00721adbcebdaaf2129`.
Lidos AGENTS, CLAUDE, PROJECT, CONSTITUTION, CAPABILITY-MATRIX, WORKFLOW,
RFC-013, promoção/recovery/publicação, módulos release e testes/evidence.

- Promoção atual: seleção → verify_promotion → re-scan → imagetools create →
  recorder usa somente `steps.promote.outcome == 'success'`.
- Recovery já consulta `describe-images --image-ids imageTag=stable`, compara
  digest e falha antes de gravar evidência de recuperação.
- Publicação lê bytes do índice pela tag via Skopeo; verify_publication compara
  hash dos bytes com índice validado, digest copiado e referência assinada.
  Cosign e provenance usam esse digest do índice, não o de uma plataforma.
- verify_promotion verifica tipo multiarch, amd64/arm64, assinatura e
  provenance do mesmo digest antes de permitir mover a tag.
- O comentário de recovery que dizia que a promoção já tinha read-back não
  correspondia ao código da main. A RFC/evidência histórica não substitui código.

## Estratégia
1. Registrar spec/aceite antes do código e preservar baseline do working tree.
2. Adicionar módulo release `verify_stable.py` que consulta ECR por `stable`,
   exige uma resposta JSON inequívoca com índice, valida SHA-256 e compara
   com o candidato. Persistir estado de falha antes da consulta e resultado
   em `reports/promotion-evidence.json`, sem marcar sucesso antecipado.
3. Inserir passo de read-back depois da escrita; recorder exige os dois passos
   bem-sucedidos, status confirmed e igualdade. Inicializar campos de evidência
   na seleção sem alterar elegibilidade; preservar `digest`/`stable_digest`.
4. Testar CLI e executar o recorder extraído do YAML; mock apenas AWS.
   Exercitar também o shell existente do recovery, sem modificá-lo.
5. Rodar verificações solicitadas, registrar resultados, limitações e handoff.

## Decisões e hipóteses
- Reutilizar `require_digest_reference`, tipos multiarch da seleção e
  `write_evidence`; não extrair uma abstração genérica para registry.
- Usar JSON completo de DescribeImages, sem projeção `[0]`, para rejeitar
  múltiplos resultados/chaves duplicadas e confirmar tag, repositório e tipo.
  API documentada em [AWS CLI DescribeImages](https://docs.aws.amazon.com/cli/latest/reference/ecr/describe-images.html).
- Região/conta continuam vindo do mesmo login/OIDC já usados pelo workflow.
- Uma consulta limitada a 60s, sem loop de retry nesta fatia. Erro/atraso de
  visibilidade falha fechado e pode ser diagnosticado posteriormente.
- verify_publication requer bytes de OCI/Skopeo; reutilizar seu protocolo
  aqui acrescentaria ferramenta sem necessidade. Recovery permanece intacto.

## Risco e rollback
Read-back pode falhar após a tag já ter sido movida; o resultado será falha,
não reversão automática. Investigar o estado e usar recovery governado se
necessário. A concorrência existente serializa promoção/recovery, não todos
os possíveis escritores externos. Antes de merge, descartar apenas este diff
isolado preservando o trabalho anterior; depois, reverter via mudança revisada.
Revisão independente pendente; esta sessão implementa e verifica, não aprova.

## Validação
`make test-unit`, `make test-integration`, `make lint-local`, `make lint-shared`,
`make lint-workflows`, actionlint dos workflows afetados, check_ai_context e
`git diff --check`. Checkout compartilhado exigido no SHA dos chamadores.
Negativo A02 rodado explicitamente. Evidência e handoff atualizados só com
resultados observados. Aceite hospedado continua NOT RUN.
