# Copilot instructions

Este repositório representa um wrapper Terraform para EKS baseado em `terraform-aws-modules/eks/aws` versão `20.33.1`.

Ao analisar issues:

- use `TRIAGE.md` como política normativa;
- preserve os tipos existentes: `type: bug`, `type: fix`, `type: enhancement` e `type: documentation`;
- diferencie defeito do wrapper, upstream, suporte de EKS/Kubernetes e configuração do consumidor;
- não exponha ID de Conta AWS, nome de cluster, URL interna, credenciais ou logs sensíveis;
- não trate decisões históricas como regra sem validação;
- não aplique labels de backlog ou conclusão automaticamente;
- prefira revisão humana quando houver segurança, breaking change, default ou ambiguidade.
