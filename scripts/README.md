# Automação do produto

Os módulos Python de `pipeline/` concentram as regras de domínio. GitHub
Actions compõe a execução; políticas revisadas ficam em [`policies/`](../policies/).

| Domínio | Responsabilidade |
| --- | --- |
| `certificates/` | Aquisição, integridade e pins do bundle corporativo |
| `pipeline/catalog/` | Entradas do catálogo, soak, digest e lote padrão (catálogo − exclusões) |
| `pipeline/artifacts/` | Formato OCI, identidade por digest e scans |
| `pipeline/runtime/` | Contratos funcionais e readiness |
| `pipeline/release/` | Candidatos, publicação, promoção e evidência de CVEs |
| `pipeline/operations/` | Tempos, saúde, resumos e versões de ferramentas |
| `pipeline/governance/` | Hardening, pins, cache e contrato com executores compartilhados |

Execute módulos pela raiz do repositório, por exemplo:

```sh
python3 -B -m scripts.pipeline.governance.pin_inventory lint
make test-unit
```

Use imports qualificados (`scripts.pipeline.<domínio>.<módulo>`), sem alterações
de `sys.path` no código de domínio. Módulos recebem entradas explícitas;
gates retornam código não zero em falha, evidências automatizadas usam JSON e
resumos para pessoas usam Markdown. Testes espelham os domínios em `tests/unit/`.

Os seis arquivos em `.github/scripts/` são adaptadores para o executor
compartilhado já publicado. Não acrescente regras ou pins neles. Sua remoção
exige migrar os consumidores e validar o contrato de integração.
Veja [arquitetura e dependências permitidas](../docs/repository-architecture.md).
