# M09/M16: ferramentas e fronteiras de confiança

Primeira parte preparada sobre `97c3cb4` (M12, PR #19); esta versão traz a
branch para a `main` atual (`432da4e`, já com M13/M14/M15) e completa o M16.
Não altera identidades de assinatura, trust policy AWS, Environments nem o
workflow gerado de triagem.

## Implementação

- Todos os checkouts dos workflows mantidos à mão usam `persist-credentials:
  false` — sete passos em cinco workflows, incluindo `recover-stable.yml`,
  que entrou na `main` (M15) depois da primeira parte desta branch. Nenhum
  passo desses jobs faz push por Git.
- Guard de entrada antes de qualquer credencial AWS, compartilhado por
  build, validação, promoção e recuperação
  ([validate_inputs.py](../.github/scripts/validate_inputs.py)): nomes únicos
  do catálogo `frameworks/*.yaml`, soak finito e não negativo (zero continua
  válido para os testes autenticados já previstos) e digest no formato
  `sha256:<64 hex>`. A recuperação passava por uma checagem própria em shell
  que aceitava qualquer caminho terminando em `.yaml` existente
  (`../frameworks/go1-26` passava); agora exige o padrão do nome **e**
  pertinência ao catálogo. O input rejeitado não é ecoado de volta no log.
- Nenhuma entrada é interpolada dentro de um `run` nos jobs privilegiados:
  `matrix.framework` (publicação) e `inputs.soak-hours` (promoção) passaram a
  chegar por `env:` e ser usadas com aspas. Os dois vinham, em última
  instância, de input de `workflow_dispatch`.
- Regra virou lint, não faxina de uma vez só:
  [lint_workflow_hardening.py](../.github/scripts/lint_workflow_hardening.py)
  roda no check obrigatório `lint-workflows` e reprova checkout sem
  `persist-credentials: false`, expressão dentro de `run`, job executor sem
  `timeout-minutes`, workflow sem `permissions` no topo e Action externa sem
  SHA completo. Rodado contra os workflows da `main` de hoje, aponta
  exatamente as nove lacunas que esta branch corrige — é a prova de que o
  lint pega o problema real, não só o estado já limpo.
- Melange acompanha o artifact do bundle com seu arquivo de versão.
  Apko/Trivy, cosign/AWS/Docker e cosign/Trivy/AWS/gh/buildx têm suas versões
  registradas por etapa, com commit/run/tentativa, junto dos artifacts
  existentes. Skopeo mantém arquivo de versão e verificação de
  disponibilidade antes da AWS. O coletor não exporta ambiente nem secrets.
- Código não confiável em contexto privilegiado: nenhum workflow mantido à
  mão usa `pull_request_target`, `issue_comment` ou `workflow_run`. PRs entram
  por `pull_request`, que roda com token de leitura e sem OIDC. O único
  `workflow_run` do repositório está no `cve-triage.lock.yml` gerado, que já
  condiciona a execução a `workflow_run.repository.id == github.repository_id`
  e `!workflow_run.repository.fork`, e cujo gatilho automático está pausado.
  Nenhum job faz checkout de uma ref controlada pelo autor do PR.
- Campos de diagnóstico: nenhum workflow imprime `toJSON(github)`, `printenv`
  ou dump de ambiente. O coletor de versões grava só a saída dos comandos de
  versão em allowlist, mais commit/run/tentativa. Verificado por varredura nos
  seis workflows e coberto por teste (`test_records_versions_without_secrets`).
- `renovate.json` prepara propostas semanais de atualização dos digests de
  apko, melange, Skopeo e actionlint nos workflows/Makefile. Só o manager
  customizado, sem concorrer com o Dependabot de Actions, sem tocar o lock
  gerado e sem automerge. Nenhum digest foi atualizado por esta entrega.

## Configuração remota: observada e alterada em 09/09/2026

Antes de alterar, o estado foi lido pela API — não presumido pela presença de
arquivo. Alterações feitas com autorização explícita do responsável.

| Controle | Antes | Depois |
| --- | --- | --- |
| Secret scanning | desativado | **ativado** |
| Push protection | desativado | **ativado** |
| `sha_pinning_required` (Actions) | `false` | **`true`** |
| Acesso do time `github_xj7_maintainer` ao repo | **nenhum** | `write` |
| CODEOWNERS | 100% comentado, inerte | regras ativas (efetivas só após merge) |
| Revisão obrigatória de PR | não configurada | 1 aprovação + code owner + dismiss stale |
| Required checks (`test`, `lint-workflows`) | obrigatórios | inalterado |
| `enforce_admins` | `true` | inalterado |
| Default token do Actions | `read`, sem aprovar PR | inalterado |
| `allowed_actions` | `all` | inalterado |
| Dependabot security updates | desativado | inalterado (fora do pedido) |
| Rulesets | lista vazia | inalterado — vazio **não** significa ausência de branch protection |

Detalhes que mudam a leitura desses controles:

- O time `github_xj7_maintainer` existia, com um membro, e **não tinha acesso
  nenhum a este repositório**. Code owner sem permissão de escrita é ignorado
  pelo GitHub: as regras comentadas não teriam funcionado nem se
  descomentadas. Por isso o acesso de escrita veio antes de ativar a revisão.
- `@vigcf` (admin do repositório) entra como dono adicional no CODEOWNERS
  para a regra ser satisfazível: o time tem um membro só e ninguém aprova o
  próprio PR — com `enforce_admins: true`, admin também não contorna.
- O GitHub lê o CODEOWNERS da **branch base** do PR. As regras deste arquivo
  só valem para PRs abertos depois que ele estiver na `main`; este PR ainda é
  avaliado pelo CODEOWNERS inerte da `main`, então cai na exigência simples
  de uma aprovação.
- `sha_pinning_required` só foi ativado depois de conferir que todos os
  `uses:` do repositório já estão em SHA de 40 caracteres — inclusive os do
  `cve-triage.lock.yml` gerado, que não é editado à mão.
- Consequência operacional imediata: com `enforce_admins: true` e uma
  aprovação obrigatória, este próprio PR precisa da aprovação do outro admin
  para entrar. Isso é o comportamento pretendido, não um efeito colateral.

## Aceite

- [x] Entradas inválidas falham antes da autenticação AWS: o guard é o passo
  seguinte ao checkout, antes de `configure-aws-credentials`, nos quatro
  workflows que autenticam. Coberto por testes de unidade e de CLI (exit
  code, catálogo, traversal, digest malformado, input não ecoado).
- [x] Checks não precisam de credencial Git persistida: `test` e
  `lint-workflows` rodam com `persist-credentials: false` e o lint reprova
  qualquer checkout novo que esqueça a opção.
- [ ] Proteção de revisão demonstrada em PR de teste: a configuração está
  ativa e este PR já cai nela; falta registrar a evidência do bloqueio real
  (tentativa de merge sem aprovação) e, depois do merge, de um PR tocando
  `.github/workflows/**` exigindo revisão de code owner.
- [ ] Ativar Renovate com acesso somente a este repositório e comprovar o
  primeiro PR real de digest, incluindo atualização consistente de todas as
  ocorrências, disponibilidade multi-arch, lint/build/scan e revisão humana.
- [ ] Validar as alterações em publicação/promoção autenticadas e conferir os
  artifacts com versões e ausência de credenciais persistidas.
- [ ] Testar fork (pertence ao M05), inputs inválidos num dispatch real e
  falhas/cancelamentos conforme os demais critérios. O job com permissão OIDC
  continua autorizado a obter tokens; o guard impede chegar ao passo AWS com
  input inválido, não constitui uma nova fronteira de IAM.
- [ ] Decidir política/automação de versões Trivy/cosign além dos pins das
  Actions e acompanhar os PRs Dependabot. Registro de versão não é
  atualização. M09 permanece parcial.

## Autoria solicitada pelo mantenedor

`AGENTS.md` registra Codex como autor principal dos commits que Codex
implementar: `git commit --author='Codex <codex@openai.com>' ...`. A
identidade Git do operador permanece como committer, sem configuração global
alterada. Autoria não confere acesso ao repo, assinatura verificada nem
endosso da OpenAI. Não reescrever histórico anterior.

## Validação local

- 81 testes de pipeline e 13 de certificados aprovados. Novos nesta parte:
  digest válido/inválido, CLI do guard (framework único, traversal, input não
  ecoado, variável ausente) e dez casos do lint de hardening.
- `actionlint` aprovado nos seis workflows mantidos à mão;
  `lint_workflow_hardening.py` aprovado na branch e reprovando as nove
  lacunas da `main`; `git diff --check` sem erros.
- Renovate 44.74.0: `renovate-config-validator --strict renovate.json`
  aprovado na primeira parte; o serviço de atualização não foi executado.
