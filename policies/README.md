# Políticas do produto

Configuração revisada que define decisões de operação e release. Os módulos
em `scripts/pipeline/` aplicam as regras; os workflows controlam a execução.

| Arquivo | Consumidor | Responsabilidade |
| --- | --- | --- |
| `operations/health.json` | `operations/operational_health.py` | Donos, alertas, exceções, cron e retenção das evidências |
| `release/promotion-quarantine.json` | `release/find_promotion_candidate.py` | Digests retirados de stable que não podem ser promovidos novamente |
| `release/signing-identities.json` | `release/verify_promotion.py` | Nome atual, nomes históricos e IDs imutáveis assinados do repositório e da organização |
| `aws/github-actions-image-base-trust.json` | IAM, role `github-actions-image-base` | Trust policy OIDC aplicada, restrita ao subject exato da main |

Alterações passam por PR e revisão dos donos em `.github/CODEOWNERS`. O lint
compara a política de retenção com os workflows locais e reutilizáveis reais.
Quarentena é por digest e repositório, com motivo, autor e data; consulte o
[runbook de recuperação](../README.md#recuperação-de-stable-runbook-m15).

Estes arquivos não armazenam credenciais ou estado gerado de execução.

A policy IAM é a configuração desejada; editar o arquivo não a aplica na AWS.
A [migração de nomes](../docs/repository-rename.md) registra aplicação, verificação
e limites. Nomes históricos só são aceitos para assinaturas/provenance, com
IDs assinados iguais aos do repositório atual; eles não têm acesso OIDC à role.
