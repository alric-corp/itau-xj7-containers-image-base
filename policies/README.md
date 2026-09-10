# Políticas do produto

Configuração revisada que define decisões de operação e release. Os módulos
em `scripts/pipeline/` aplicam as regras; os workflows controlam a execução.

| Arquivo | Consumidor | Responsabilidade |
| --- | --- | --- |
| `operations/health.json` | `operations/operational_health.py` | Donos, alertas, exceções, cron e retenção das evidências |
| `release/promotion-quarantine.json` | `release/find_promotion_candidate.py` | Digests retirados de stable que não podem ser promovidos novamente |

Alterações passam por PR e revisão dos donos em `.github/CODEOWNERS`. O lint
compara a política de retenção com os workflows locais e reutilizáveis reais.
Quarentena é por digest e repositório, com motivo, autor e data; consulte o
[runbook de recuperação](../README.md#recuperação-de-stable-runbook-m15).

Estes arquivos não armazenam credenciais ou estado gerado de execução.
