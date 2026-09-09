# Testes de regressão

As duas suítes rodam no workflow `Test image pipeline scripts`, em PRs e pushes
na `main` que alterem os scripts, os testes de certificados ou o próprio workflow.
O job tem apenas `contents: read` e não autentica na AWS.

```sh
python3 -B -m unittest discover -s .github/scripts -p 'test_*.py' -v
python3 -B -m unittest discover -s tests/certificates -p 'test_*.py' -v
```

## Pipeline: 40 testes

Preservados do PR #1, commit `9704e46`, junto dos módulos que exercitam.
Cobrem seleção cronológica de candidatos, prevenção de rollback, identidade
por digest, integridade OCI, scans nas duas arquiteturas e verificação de
assinatura/provenance. As chamadas a Docker, Trivy, cosign e GitHub são
substituídas nos testes; não exigem instalação dessas ferramentas nem rede.

`find_promotion_candidate.py` continua sendo chamado pelo workflow de promoção
existente. Os novos módulos de scan, OCI e verificação são preservados com seus
testes; sua integração nos workflows de publicação/promoção é trabalho pendente,
não uma garantia já ativa em produção.

## Certificados: 13 testes

A suíte executa `scripts/certificados.sh` de verdade. Gera CAs X.509 sintéticas
temporárias com OpenSSL, incluindo um bundle com múltiplos certificados, e
substitui `aws` e `curl` por cópias locais. Não lê os buckets pessoais/corporativos,
o cache de sessões anteriores ou o bundle Mozilla na internet. Chaves de teste,
certificados, lockfiles e saídas são removidos ao terminar.

Dependências: Python 3, Bash, OpenSSL com `req -addext`, jq, sha256sum e GNU date.
No macOS, a suíte usa `gdate` quando disponível; AWS CLI e curl não são necessários
para os testes. Dependências ausentes falham explicitamente, sem ignorar a suíte.

Cobertura:

- Baseline, JSON de saída, leitura dos bundles pelo OpenSSL e pin repetível.
- Lockfile relativo, ausente, vazio, incompleto, duplicado ou malformado.
- Rotação bloqueada antes do pin e aceita depois da atualização explícita.
- Última linha sem newline no manifesto e em certificados/fragmentos PEM.
- Metadados divergentes e falha simulada de gravação dos metadados no pin.

Os testes locais não substituem rebuild melange/apko, integração S3, revisão
humana da legitimidade das CAs ou testes TLS dos runtimes consumidores.
O `--pin` atualiza dois arquivos sequencialmente; não é uma transação atômica.
Uma falha na segunda cópia pode deixar o par divergente e a verificação normal
bloqueia seu uso. Recupere ambos pelo Git ou repita o pin após revisão.

## Trabalho preservado para retomada

O PR #1 (`improvements/image-pipeline-validation`) contém mudanças adicionais
que não fazem parte desta extração. O histórico permanece em:

- https://github.com/alric-corp/itau-xj7-containers-image-base/pull/1
- https://github.com/alric-corp/itau-xj7-containers-image-base/tree/9704e46ac758298b46ba107d4236f1edf9cc8bf1

Antes de integrar o restante, retomar:

1. Validação sem AWS em ambas as arquiteturas e publicação do mesmo artifact OCI,
   sem rebuild; verificar execução autenticada e retry parcial.
2. Promoção por digest com assinatura/provenance, re-scan, serialização e soak;
   comprovar integração pelo workflow autenticado.
3. Restrição da trust policy OIDC, imutabilidade ECR com exceção para stable,
   tags únicas e atualização das dependências fixadas.
4. Falha de scan do .NET 8 e seleção do lote publicável.
5. Atualização da RFC-013 e README para refletir somente controles integrados.

As mudanças locais de Makefile e melange para fixar o bundle Mozilla não estavam
no PR #1 e não estão nesta extração. O rebuild desse pin continua pendente.
