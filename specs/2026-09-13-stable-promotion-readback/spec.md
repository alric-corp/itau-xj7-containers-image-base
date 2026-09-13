# SPEC — P1-01 Stable Promotion Read-Back

## Objetivo
Uma promoção só pode ser declarada bem-sucedida após consultar novamente o
ECR pela tag `stable` e comprovar que ela aponta para o candidato verificado.

## Requisitos
- R1: após mover `stable`, observar seu digest no ECR pela própria tag.
- R2: comparar exatamente com o digest do candidato selecionado, verificado
  por assinatura/provenance e reescaneado. A identidade é o índice OCI
  multiarch (ou manifest list legado aceito pelo verificador), nunca um
  manifest individual de plataforma.
- R3: ausência, erro de consulta, timeout, digest vazio/inválido, resposta
  ambígua ou divergência falham com exit não zero e nunca `promoted=true`.
- R4: a evidência final contém `candidate_digest`, `stable_digest_observed`,
  `read_back_status` (`confirmed`, `mismatch`, `failed`, `not_run`) e `promoted`.
  `digest` continua sendo o candidato; `stable_digest` continua sendo a
  observação anterior à promoção. Nenhum consumidor perde esses campos.
- R5: `promoted=true` exige escrita e read-back concluídos com sucesso e
  digests iguais. Falhas anteriores ou candidato pulado registram `not_run`.
- R6: preservar soak, seleção, quarentena, assinatura, provenance, re-scan,
  OIDC, IAM, Cosign/Sigstore, concorrência e comportamento de recovery.

## Restrições e invariantes
Testes determinísticos sem AWS real, mock apenas da fronteira de subprocesso
externo. Evidência local não equivale a aceite hospedado. Não realizar
auto-aprovação; revisão independente será feita posteriormente por outro modelo.
Preservar alterações locais preexistentes. Sem commit, push ou PR.

## Fora do escopo
Partial retry/P1-02, Wolfi signing key, IAM, Renovate, Veracode, revisão ampla
da RFC, consumer contract, VEX, admission, ARM nativo e workaround de zlib.
Não alterar Trivy nem permitir CVEs para tornar o pipeline verde.

## Dependências
Revisão independente antes da integração. Após merge, operador autorizado
executará o aceite real; `go1-26`/`go1-26-dev` são opções somente se disponíveis
e elegíveis naquele momento. HOSTED ACCEPTANCE = NOT RUN nesta entrega.

## Conclusão
Critérios em [acceptance.md](acceptance.md); execução em [plan.md](plan.md).
