# SPEC — P1-03 Wolfi signing-key defense-in-depth

## Objetivo

O build deve usar uma chave Wolfi explicitamente versionada, pinada e
revisada, sem depender do download dinâmico da chave configurada, e detectar
mudanças upstream sem substituir automaticamente essa chave local.
Isso oferece defense-in-depth, reviewability, controle de rotação e detecção
de drift. Não estabelece um conjunto de confiança exclusivamente local.

A revisão arquitetural independente, comunicada pelo usuário em 13/09/2026
com resultado **READY TO REFORMULATE AND IMPLEMENT**, autorizou esta mudança
de requisito. O blocker da propriedade original permanece registrado na
[evidence](evidence.md); não foi resolvido nem apagado.

## Requisitos

- R1: Apko e todas as receitas Melange configuram explicitamente os mesmos
  bytes locais. A chave configurada não é adquirida remotamente no build.
- R2: ausência, alteração sem atualização explícita do pin, fingerprint
  incorreto ou formato diferente de RSA public key PEM falham antes do build.
- R3: a adoção inicial exige igualdade SHA-256 de duas fontes oficiais
  distribuídas independentemente. Divergência interrompe a adoção.
- R4: APKINDEX e packages continuam sujeitos à verificação APK normal.
- R5: a rotação exige duas fontes oficiais, atualização conjunta chave/pin em
  PR, revisão humana e merge. Nenhuma automação substitui a chave/pin locais.
- R6: monitoramento remoto é detecção. Mismatch ou endpoint indisponível
  falham o health check; esse monitor não é controle de confiança nem
  dependência do build. O preflight da chave explícita é offline.
- R7: lint impede reintrodução de keyring remoto nas configurações do produto.
- R8: a limitação de discovery permanece visível na spec, evidence e handoff
  corporativo. Sua reprodução não equivale a aprovação de um controle.

## Threat model

Antes, comprometimento conjunto da origem/CDN/transporte podia servir uma
nova chave e packages assinados por ela; ambos eram obtidos da mesma origem.
Depois, uma mudança no endpoint da signing key não substitui os bytes da
chave explicitamente configurada: arquivo e pin exigem atualização revisada.
O monitor permite detectar a mudança. Uma assinatura demonstra autenticidade
segundo uma chave aceita pela ferramenta; não demonstra segurança do package.

Não protege contra comprometimento do próprio repositório, aprovação
maliciosa de rotação, comprometimento da private signing key legítima Wolfi,
package malicioso legitimamente assinado nem vulnerabilidades sem CVE.
GitHub oficial e packages.wolfi.dev são canais de distribuição distintos,
não duas autoridades de assinatura independentes.

## Known Tooling Limitation

`contents.keyring` **≠ exclusive trust set**. O Apko pode adicionar chaves
anunciadas pelo próprio repository via `/apk-configuration`/JWKS ao conjunto
usado para verificar índices: `explicit keyring + discovered keys`.
Melange usa Apko internamente. Não há modo oficial suportado equivalente a
`explicit-keys-only`/`--no-key-discovery` nas versões avaliadas.

Um adversário capaz de comprometer repository/CDN/TLS e servir configuração
de discovery, JWKS e index/packages assinados pela nova chave pode introduzir
uma trust key aceita pelo Apko. A chave local não elimina esse risco.
A reprodução registrada é **EXPECTED TOOLING LIMITATION REPRODUCED**; ela
continua reprovando a propriedade original de exclusividade.

O HTTP 404 atual do endpoint oficial, quando observado, torna discovery um
no-op para essa origem naquele momento. É um fato operacional datado, não
um invariant nem uma garantia contratual futura; ver [evidence.md](evidence.md).

## Handoff corporativo e upstream

Requisito posterior do **P0-03**: se a corporação exigir uma trust boundary
independente da origem Wolfi, usar mirror/proxy controlado que não exponha
`apk-configuration`/JWKS e restringir egress do build à origem aprovada.
Tecnologia e aceite cabem a Cloud/Network/Security; nada disso é implementado
nesta fatia. Detalhes e recomendação de issue futura no Apko em
[handoff.md](handoff.md).

## Restrições e invariantes

Preservar package repositories, Trivy, vulnerability policy, Cosign,
provenance, SBOM, promotion, stable read-back, OIDC/IAM e catálogo. A public
key não é segredo; nunca versionar uma private key. Não fazer commit,
push, PR ou auto-aprovação nesta entrega. Revisão independente posterior.

## Fora do escopo

Fork/patch/custom binary de Apko/go-apk, hacks de DNS/hosts, interceptação,
firewall, cache especial, resign de APKs, repositório privado, bypass de
assinatura, partial retry, IAM, split publisher/promoter, mirrors, Renovate, Veracode,
VEX, Policy Controller, private Sigstore, runner arm64 nativo, workaround
zlib, RFC geral e guia geral do consumidor.

## Dependências

LOCAL-EXECUTE para código/config/chave pública/spec/testes; RESEARCH / EXTERNAL
READ para fontes oficiais. Não exige decisão IAM/PKI corporativa. O incidente
zlib é independente: eventual falha CVE no lote é BLOCKED_UPSTREAM.

## Conclusão

Critérios em [acceptance.md](acceptance.md). Implementação e testes não
substituem revisão independente nem aceite hospedado.
