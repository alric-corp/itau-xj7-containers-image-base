# ACCEPTANCE — P1-01

| ID | Requisito | Critério observável | Verificação planejada |
| --- | --- | --- | --- |
| A01 | R1/R2/R5 | Candidato A, stable A: PASS, promoted=true | CLI read-back + recorder real do YAML com ECR simulado |
| A02 | R3/R5 | Candidato A, stable B: FAIL, promoted=false, mismatch | Teste negativo explícito, exit não zero |
| A03 | R3 | Stable ausente: FAIL, promoted=false | Lista vazia e ImageNotFoundException |
| A04 | R3 | Registry falha: FAIL, promoted=false | CalledProcessError, timeout, executável indisponível |
| A05 | R2/R3 | Resposta inválida/ambígua: FAIL, promoted=false | JSON vazio/malformado, digest inválido, múltiplas entradas, chaves duplicadas, plataforma individual |
| A06 | R4/R5 | Evidência final preserva ambos os digests; iguais no sucesso | Executar recorder inclusive falha anterior e skip |
| A07 | R6 | Controles existentes preservados | Diff, regressões de seleção/verificação/publicação, ordem e guards do workflow, lints |
| A08 | R6 | Recovery sem regressão | Executar shell de read-back existente com fronteira AWS simulada; workflow preservado |

## Negativos e limites
Nenhuma falha pode virar sucesso no recorder mesmo quando a escrita retorna
zero. O read-back deve ocorrer depois da escrita e sob o guard de sucesso
implícito do Actions. Uma resposta de manifest individual deve falhar mesmo
com um digest sintaticamente válido. Sucesso confirma a tag naquele instante;
não impede alteração futura por outro escritor autorizado.

## Aceite hospedado
HOSTED ACCEPTANCE = NOT RUN. Após merge: candidato selecionado → verificação
de assinatura/provenance → re-scan → stable movida → consulta ECR por stable
→ igualdade de digest do índice → evidence final armazenada. Registrar
commit, run/tentativa, framework e artifact; não reutilizar runs anteriores
como evidência deste código.
