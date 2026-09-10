# Adaptadores de compatibilidade

O executor reutilizável fixado no commit
`081270ccf18ee4d98da23f22f761846d29f71486` ainda usa estes caminhos do consumidor:

| Adaptador | Implementação canônica |
| --- | --- |
| `validate_inputs.py` | `scripts.pipeline.catalog.validate_inputs` |
| `oci_artifact.py` | `scripts.pipeline.artifacts.oci_artifact` |
| `scan_images.py` | `scripts.pipeline.artifacts.scan_images` |
| `tool_versions.py` | `scripts.pipeline.operations.tool_versions` |
| `report_unfixed_cves.py` | `scripts.pipeline.release.report_unfixed_cves` |
| `runtime_images.py` | `scripts.pipeline.runtime.runtime_images` |

Os adaptadores não contêm regras de domínio. `runtime_images.py` expõe também
`runtime`, `supported` e `project`, importadas pelo executor publicado.
Os demais contratos são a CLI e seu código de saída; `validate_inputs.py`
preserva ainda a função `validate`.

Novos workflows do produto usam `python3 -m scripts.pipeline...`.
Remova adaptadores somente após atualizar todos os releases suportados do
executor e comprovar a migração com `make test-integration`.
