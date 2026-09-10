# Ajustes finais e liberação — 10/09/2026

Os ajustes de código estão nesta branch; produção continua bloqueada até os
aceites abaixo. O sandbox é `alric-corp`, conta AWS `712107929769`, `us-east-1`.
Os documentos e a correção de rename encontrados no workspace foram
preservados em um commit separado dos ajustes desta entrega.

## Correções

- Chamadores adotam `0459275b4a2ffbe6e8961041e7b93b41e88ba215`, que resolve a
  action interna pelo nome novo. A [biblioteca #2](https://github.com/alric-corp/alric-containers-reusable-workflows/pull/2)
  ainda precisa de revisão independente. A trust policy foi relida e contém
  os IDs permanentes e o nome novo; isso não comprova uma sessão OIDC no runner.
- Publicador e executor de contratos usam Skopeo `v1.22.2-immutable`, índice
  `sha256:4a16d57b37617a04b3d643079a477a2848efe892dffcdf0ce56df4262b65f810`.
  Manifestos amd64/arm64 disponíveis e binário amd64 executado: `1.22.2`.
  O Renovate acompanha versões completas com sufixo `-immutable`; o inventário
  reconhece `tag@digest`, mantendo a detecção de divergência e disponibilidade.
  O [upstream](https://github.com/podman-container-tools/image_build/blob/main/README.md)
  documenta que tags de versão comuns também são reconstruídas diariamente;
  `-immutable` preserva a versão, salvo problemas extremos de segurança.
- Melange baixa o [bundle Mozilla de 13/08/2026](https://curl.se/docs/caextract.html)
  por URL datada e verifica o SHA-256 versionado antes de empacotar. A CA
  corporativa continua dependendo de fonte e política aprovadas.
- A [primeira execução de saúde](https://github.com/alric-corp/alric-containers-image-base/actions/runs/34493238551)
  preservou os relatórios e falhou corretamente: Skopeo indisponível, lacuna
  histórica de 24,08h na promoção e busca de jobs truncada em 90 runs.
  A busca agora desconsidera PRs e branches sem autorização de publicação;
  o limite de 300 comporta uma semana nominal de 175 execuções mais manuais.
  A lacuna real do agendador permanece alerta; os limites não foram relaxados.
- A proteção da biblioteca foi aplicada e relida: `test`, `lint-workflows`,
  `smoke-trivy`, aprovação independente de CODEOWNERS, descarte de aprovações
  após mudanças, aprovação do último push e regras válidas para administradores.
  O time recebeu escrita e Actions passaram a exigir SHA completo.
  Configuração reproduzível na [biblioteca #3](https://github.com/alric-corp/alric-containers-reusable-workflows/pull/3).

## Revisão do Dependabot #47

O [PR #47](https://github.com/alric-corp/alric-containers-image-base/pull/47),
head `0cdf7ed463a94664f49dba0b814f1d40d161190b`, troca seis referências de
`github/gh-aw-actions/setup` em `cve-triage.lock.yml` para `v0.88.6`, mas mantém
metadata, manifesto e `actions-lock.json` em `v0.81.6`. Os checks rápidos
verdes não executam esse workflow nem comprovam a compatibilidade do runtime.
**Não integrar essa atualização isolada.** A [orientação do compilador](https://github.github.com/gh-aw/reference/compilation-process/)
é atualizar a versão de `gh-aw` e recompilar o Markdown, mantendo runtime e
código gerado coordenados. O ignore `github/gh-aw-actions/*` em Dependabot
evita novas propostas desse tipo; os outros Actions continuam cobertos.

## Manutenção e retenção

A API `orgs/alric-corp/installations` retornou zero instalações de Apps.
Um administrador precisa [instalar Renovate](https://github.com/apps/renovate)
somente em `alric-containers-image-base` e `alric-containers-reusable-workflows`,
aceitar o onboarding e conferir o primeiro PR real. Automerge permanece
desligado. Este passo não pode ser concluído com o token GitHub disponível.

A [política ECR](../policies/operations/ecr-lifecycle.json) seleciona somente
imagens **sem tag, com mais de 30 dias**. Todas as tags de release, `stable`
e assinaturas com tag ficam preservadas; não há exclusão geral após sete dias.
A janela de remoção de releases publicadas continua sendo decisão corporativa.
Manifestos referenciados por índices são protegidos pelo próprio ECR;
artefatos de referência seguem o ciclo do subject conforme a
[documentação AWS](https://docs.aws.amazon.com/AmazonECR/latest/userguide/LifecyclePolicies.html).
A política foi aplicada e relida nos 15 repositórios do catálogo; todos os
previews tinham zero alvos de expiração. O repositório auxiliar de validação
ficou fora do escopo. [Evidência por repositório](evidence/ecr-lifecycle-2026-09-10.json).
Antes de reaplicar em qualquer ambiente, usar preview e revisar cada alvo:

```sh
aws ecr start-lifecycle-policy-preview --repository-name image-base-go1-26 \
  --lifecycle-policy-text file://policies/operations/ecr-lifecycle.json
aws ecr get-lifecycle-policy-preview --repository-name image-base-go1-26
# Somente após status COMPLETE e revisão do resultado:
aws ecr put-lifecycle-policy --repository-name image-base-go1-26 \
  --lifecycle-policy-text file://policies/operations/ecr-lifecycle.json
```

## Aceites ainda necessários

1. Revisar/integrar a biblioteca #2 e estes ajustes pelo gate normal. Nenhuma
   aprovação, proteção ou soak pode ser substituída por um bypass administrativo.
2. Executar na `main` um lote com `go1-26/go1-26-dev`, `java21/java21-dev` e
   `dotnet10/dotnet10-dev`; verificar validação, contrato amd64/arm64,
   publicação do mesmo digest, assinatura e provenance no mesmo run.
3. Após o soak de seis horas, comprovar a primeira promoção pós-rename e
   executar novamente a saúde. Aprovação local ou de PR não substitui isso.
4. Resolver com AppSec/Containers Products: scanner corporativo, CA, catálogo,
   destino/dono do alerta e SLA baseado na cadência observada.
5. Na conta/organização corporativa, criar os 15 ECRs, resource policy com os
   Org IDs reais, OIDC por IDs, identidades de assinatura, time/CODEOWNERS com
   escrita e proteções. Repetir os aceites de PR/fork sem credenciais,
   publicação por digest, assinatura, imutabilidade, promoção e recuperação.
   Registrar os novos runs e IDs; evidências deste sandbox não se transferem.

Evidência desta entrega: [pins e primeira saúde](evidence/release-readiness-2026-09-10.json).
