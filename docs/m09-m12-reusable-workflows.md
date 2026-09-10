# Segregação dos workflows — M09/M12 e identidade M03/M05/M16

O `image-base` já reutilizava jobs localmente. A segregação move execução
compartilhável para `alric-corp/itau-xj7-reusable-workflows` e mantém as decisões
de release no produto. O primeiro pacote tem contrato Apko/OCI explícito;
não promete suportar qualquer pipeline Docker sem adaptação.

| Componente | Destino | Motivo |
| --- | --- | --- |
| Melange + Apko + scan amd64/arm64 + artifact aprovado | Reusable `validate-apko-images.yml` | Sequência reaproveitável para produtos que implementem o contrato Apko |
| Execução de contratos sobre OCI candidato | Reusable `test-runtime-images.yml` | Executor comum; probes, projetos e cobertura continuam sendo do produto |
| Instalação/verificação do Trivy | Composite `actions/setup-trivy` | Mesma definição em validação, promoção e recuperação, sem comandos como input |
| `workflow.yml` | `image-base` | Eventos, cron, catálogo e parâmetros AWS são decisões do produto |
| `build-base-images.yml` | `image-base` | Gates por framework, contrato de publicação, ECR e identidade do assinador |
| `promote-stable.yml` / `recover-stable.yml` | `image-base` | Soak, quarentena, concorrência, assinatura e política de recuperação são acoplados ao produto |
| `test-promotion.yml` | `image-base` | Testes de domínio e nomes dos required checks `test`/`lint-workflows` |
| Saúde operacional | `image-base` | Catálogo, crons, dono, limites e retenção são política do produto |
| `cve-triage.md` / lock gerado | `image-base` | Instruções, ferramentas e permissões do agente de triagem deste produto |
| Scripts, manifests, certificados e projetos de teste | `image-base` | Contrato e comportamento do produto, revisados com seu código |

`validate-base-images.yml` e `test-runtime-images.yml` ficam como pontos de
entrada pequenos. O primeiro preserva as chamadas locais já existentes; o
segundo preserva também o dispatch manual. Os executores remotos aceitam apenas
`workflow_call`, sem cron, dispatch ou secrets. O build e o publicador continuam
em jobs distintos, preservando o retry da publicação sem rebuild.

## Contrato e confiança

O checkout dentro de um workflow reutilizável lê o **consumidor**. Assim,
`frameworks/`, `melange/`, `.github/scripts/` e `tests/runtime/` continuam
resolvendo no commit do `image-base`. Isso é intencional e documentado no
[contrato do pacote](https://github.com/alric-corp/itau-xj7-reusable-workflows/blob/8f82ea345b38142d43fb8f8358ae76d2d4ea97ce/docs/apko-contract.md).
Outro produto precisa implementar as mesmas interfaces antes de adotar o pacote.

As chamadas usam SHA completo. Validação recebe somente `contents: read`;
runtime recebe também `actions: read` para baixar artifacts do próprio produto.
Não há `secrets: inherit`, comandos como input nem novos jobs com OIDC.
As permissões existentes de publicação continuam declaradas no consumidor.

O job assinador permanece em `.github/workflows/build-base-images.yml`;
`verify_promotion.py` não foi alterado. Não há nova identidade de assinador a
autorizar nem wildcard para aceitar candidatos históricos. Uma futura extração
do publicador deve satisfazer o aceite de identidade já registrado na RFC antes
de ser ativada. A migração atual também não altera Environments ou trust policy IAM.

O nome e a retenção dos artifacts são parte da API:
`melange-repo` (1 dia), `validated-oci-*` (3 dias), `build-scans-*` e
`runtime-*` (30 dias). Um run deve chamar a validação uma única vez com o lote
completo, porque os nomes dos artifacts são compartilhados dentro do run.

## Checks e atualização

`workflow_dependencies.py` extrai o SHA dos chamadores reais. Nos checks, um
segundo checkout traz esse commit para `.reusable-workflows/`, sem persistir
credenciais Git. A verificação rejeita SHA flutuante/divergente, checkout ausente,
arquivo diferente do commit, inputs obrigatórios ausentes e inputs desconhecidos.
O lint M16 passa a exigir SHA também em `jobs.<id>.uses`, além das Actions.

O lint lê os YAML compartilhados. Na integração com o trabalho local de saúde,
`operational_health.workflow_files()` usa o mesmo resolvedor para que a
comparação com `.github/pipeline-health.json` continue lendo a retenção efetiva
dos uploaders remotos. Ausência do checkout falha; não omite os artifacts.
Essa integração local não faz parte do PR isolado criado a partir da `main`,
que ainda não contém o trabalho de saúde.

Dependabot agrupa atualizações deste repositório compartilhado. O gate exige
um único SHA para os workflows e a mesma action Trivy em validação, promoção e
recuperação. A action usada pelo validador tem seu próprio SHA, definido no
workflow compartilhado. Ao atualizar, alinhe as chamadas de promoção/recuperação
a esse SHA: simplesmente escolher o último commit da action pode fazê-las
divergir. O lint bloqueia essa divergência, inclusive em PR automático.

Renovate passa a manter Apko/Melange e a versão Trivy no repositório que os
define. No produto, continuam os insumos ainda usados localmente. Configuração
versionada não comprova que o app Renovate está instalado e ativo.

Para executar os checks localmente, aponte para um checkout no SHA dos chamadores:

```sh
export REUSABLE_WORKFLOWS_PATH=/caminho/itau-xj7-reusable-workflows
python3 -B .github/scripts/workflow_dependencies.py lint
python3 -B -m unittest discover -s .github/scripts -p 'test_*.py' -v
```

## Adoção e evidências

PRs: [reusable-workflows #1](https://github.com/alric-corp/itau-xj7-reusable-workflows/pull/1) e [image-base #45](https://github.com/alric-corp/itau-xj7-containers-image-base/pull/45).
Os commits fixados já foram enviados; a `main` do consumidor só deve adotar o
pacote após a revisão da biblioteca. Preserve os commits referenciados: se usar
squash, fixe o SHA final da biblioteca no consumidor e repita os checks antes
do merge. Isso também é necessário em atualizações futuras.

A consulta inicial encontrou a biblioteca pública e `main` sem proteção.
A conferência adicional encontrou `sha_pinning_required: false`, token padrão
com leitura e sem permissão para aprovar PRs, `@vigcf` com acesso de administrador
e nenhum time associado ao repositório. O time do CODEOWNERS precisa receber
escrita para atuar como dono; `@vigcf` já tem acesso suficiente.
`CODEOWNERS` foi preparado, mas aprovação de code owner, required checks,
descarte de aprovações antigas, `enforce_admins` e acesso de escrita dos donos
precisam ser ativados/conferidos antes da adoção em produção. Os arquivos deste
trabalho não alteram as configurações remotas.

A validação local e os runs autenticados estão registrados abaixo e na RFC
com seus limites. Um check aprovado não comprova publicação ECR, promoção, recuperação
ou execução do cron; os aceites remotos dos demais itens continuam separados.

Referências: [reuso e permissões](https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows),
[contexto do chamador](https://docs.github.com/en/actions/reference/workflows-and-actions/reusing-workflow-configurations),
[OIDC e workflow chamado](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-with-reusable-workflows).

## Evidências da segregação — 10/09/2026

- Biblioteca: 11 testes, hardening, actionlint e instalação real do Trivy
  [aprovados](https://github.com/alric-corp/itau-xj7-reusable-workflows/actions/runs/34431800269).
- Consumidor: `test` e `lint-workflows`
  [aprovados](https://github.com/alric-corp/itau-xj7-containers-image-base/actions/runs/34432303109).
- Validação de PR pela biblioteca: [14 de 15 frameworks aprovados](https://github.com/alric-corp/itau-xj7-containers-image-base/actions/runs/34432303814).
  `dotnet8` foi bloqueado nas duas arquiteturas pelo scan: `CVE-2026-47304`
  (CRITICAL), `CVE-2026-47302`, `CVE-2026-50525` e `CVE-2026-50648` (HIGH),
  com versão de correção `8.0.129-r1` reportada pelo Trivy. Nenhum artifact
  `validated-oci-dotnet8` foi liberado; publicação e promoção ficaram `skipped`.
- Runtime Python 3.13: [amd64 nativo e arm64 emulado aprovados](https://github.com/alric-corp/itau-xj7-containers-image-base/actions/runs/34432393980),
  consumindo o artifact do run de validação acima. UID/GID, filesystem somente
  leitura, tmpfs e TLS positivo/negativo passaram sobre o mesmo índice OCI.
- Local: 123 testes de pipeline + 13 de certificados na branch isolada;
  168 testes e a política de retenção aprovados na árvore com os trabalhos
  preexistentes de runtime/saúde. O runtime compilado dessa árvore não foi
  exercido no dispatch hospedado desta segregação.

[Registro com commits, digests e relatórios](evidence/reusable-workflows-2026-09-10.json).
Os runs correspondem ao commit funcional `974384c`; a atualização posterior
registra somente documentação/evidências. Publicação ECR, promoção, recuperação
e merge não foram executados nesta entrega.
