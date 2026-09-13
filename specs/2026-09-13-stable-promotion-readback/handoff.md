# HANDOFF — P1-01

- Repo: alric-containers-image-base; main `466d5c94790370e4620cd00721adbcebdaaf2129`.
- Spec: esta pasta; objetivo/aceite em [spec.md](spec.md) e [acceptance.md](acceptance.md).
- Estado: implementação local concluída e verificada; sem commit/push/PR.
- Arquivos desta entrega: `.github/workflows/promote-stable.yml`, `README.md`,
  `scripts/pipeline/release/find_promotion_candidate.py`, novo
  `scripts/pipeline/release/verify_stable.py`,
  `tests/unit/pipeline/release/test_find_promotion_candidate.py`, novo
  `tests/unit/pipeline/release/test_verify_stable.py` e os seis Markdown desta pasta.
- Trabalho preexistente de IA: 31 arquivos conferidos por SHA-256, preservados;
  não incluir automaticamente esse material na entrega de P1-01.
- T01–T06 concluídas. Ver [evidence.md](evidence.md): 251 unitários e 24 de
  integração OK; todos os lints/actionlint/contexto/diff OK. Integração exigiu
  repetição autorizada fora do sandbox para abrir socket TLS.
- Negativos explícitos: teste de mismatch e processo CLI real com AWS simulado,
  ambos exigem exit 1 e promoted=false; os testes retornaram OK.
- Regra implementada: só o recorder marca promoted=true, após escrita e
  read-back bem-sucedidos, status confirmed e igualdade exata do digest do índice.
  `digest` e `stable_digest` mantêm os significados anteriores; novos campos
  explicitam candidato, observação posterior e estado do read-back.
- Recovery intacto, com teste de seu shell de read-back. Nenhum controle de
  assinatura/provenance, re-scan, soak, quarentena, OIDC/IAM ou Cosign alterado.
- Riscos para revisão: resposta ambígua/malformada e falhas AWS devem continuar
  fechadas; checar ordenação/guards e evidência em falha. Escrita pode ocorrer
  antes de um read-back falhar; sem rollback automático ou retry novo.
- Próximo passo: revisão independente por outro modelo sobre este diff e esta
  spec. Não houve auto-aprovação nem revisão independente nesta sessão.
- Após revisão/merge, operador autorizado executa aceite hospedado da cadeia
  inteira. `go1-26`/`go1-26-dev` publicaram no run 34727294191, mas disponibilidade
  e elegibilidade atuais no ECR não foram consultadas. Revalidar no momento.
- Revisão independente e HOSTED ACCEPTANCE = **NOT RUN**.

Confirme o estado real do Git antes de continuar.
