# M09/M16: ferramentas e fronteiras de confiança

Entrega preparada sobre `97c3cb4` (M12, PR #19). Não altera identidades de
assinatura, trust policy AWS, Environments ou o workflow gerado de triagem.

## Implementação

- Checkouts dos workflows mantidos manualmente usam `persist-credentials: false`.
- O bundle valida a lista completa de frameworks antes de compilar; publicação
  e promoção repetem a validação antes de autenticar na AWS. Aceitam somente
  nomes únicos de arquivos do catálogo. Soak deve ser finito e não negativo;
  zero continua permitido para os testes autenticados já previstos.
- Melange acompanha o artifact do bundle com seu arquivo de versão. Apko/Trivy, cosign/AWS/Docker e cosign/Trivy/AWS/gh/buildx têm suas versões
  registradas por etapa, com commit/run/tentativa. Os registros acompanham os
  artifacts existentes. Skopeo continua com seu arquivo de versão e verificação
  de disponibilidade antes da AWS. O coletor não exporta ambiente ou secrets.
- `renovate.json` prepara propostas semanais de atualização dos digests de
  apko, melange, Skopeo e actionlint nos workflows/Makefile. Usa apenas o manager
  customizado, sem concorrer com Dependabot de Actions, sem tocar o lock gerado
  e sem automerge. O canal de consulta é `latest`; a execução continua presa ao
  digest revisado. Nenhum digest foi atualizado por esta entrega.

## Estado remoto observado em 09/09/2026

- Branch protection da main: checks `test` e `lint-workflows`, vinculados ao
  GitHub Actions, obrigatórios; `enforce_admins: true`; `strict: false`.
- Rulesets: lista vazia; isso NÃO significa ausência de branch protection.
- Revisões de PR obrigatórias: não configuradas. CODEOWNERS é boilerplate
  comentado, com ativação dependente de outro revisor/time com acesso adequado.
- Secret scanning e push protection: desativados. Nenhuma configuração remota
  de segurança foi alterada nesta entrega.
- PRs Dependabot #7–#11 continuam pendentes. #8–#10 tocam componentes da triagem
  gerada e exigem revisão do processo `gh aw compile`, não edição casual do lock.

## Aceite ainda pendente

- [ ] Ativar Renovate com acesso somente a este repositório e comprovar primeiro
  PR real de digest, incluindo atualização consistente de todas as ocorrências,
  disponibilidade multi-arch, lint/build/scan e revisão humana.
- [ ] Habilitar secret scanning/push protection e confirmar funcionamento.
- [ ] Definir revisor/time elegível e ativar CODEOWNERS/revisão obrigatória sem
  bloquear o único mantenedor sem alternativa de revisão.
- [ ] Validar as alterações em CI e depois em publicação/promoção autenticadas;
  verificar os artifacts com versões e ausência de credenciais persistidas.
- [ ] Testar fork, inputs inválidos no dispatch real, falhas/cancelamentos e
  recuperação conforme os demais critérios de M16. O job com permissão OIDC
  continua autorizado a obter tokens; o guard impede chegar ao passo AWS com
  input inválido, não constitui uma nova fronteira de IAM.
- [ ] Decidir política/automação de versões Trivy/cosign além dos pins das
  Actions e acompanhar os PRs Dependabot. Registro de versão não é atualização.

M09 e M16 permanecem parciais. A configuração Renovate sozinha não instala um
serviço nem garante que algum PR de atualização será criado.

## Autoria solicitada pelo mantenedor

`AGENTS.md` registra Codex como autor principal dos commits que implementar:
`git commit --author='Codex <codex@openai.com>' ...`.
A identidade Git do operador permanece como committer, sem configuração global
alterada. A API pública do GitHub confirmou a conta `codex` (ID 267193182) e
commits com esse e-mail associados a ela. Autoria não confere acesso ao repo,
assinatura verificada nem endosso da OpenAI. Não reescrever histórico anterior.

## Validação local

- 51 testes de pipeline (incluindo cinco novos de inputs/versões) e 13 testes
  de certificados aprovados; actionlint nos cinco workflows manuais e diff
  sem erros de whitespace.
- Renovate 44.74.0: `renovate-config-validator --strict renovate.json` aprovado.
  Houve aviso de engine por Node local 26 (Renovate declara Node 24); não foi
  executado o serviço de atualização. Extração das expressões em JavaScript
  encontrou 7 ocorrências: melange 3, apko 2, Skopeo 1, actionlint 1.
