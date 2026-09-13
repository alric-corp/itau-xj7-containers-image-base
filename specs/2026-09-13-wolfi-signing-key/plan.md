# PLAN — P1-03 Wolfi signing-key defense-in-depth

## Pesquisa

Baseline limpo `f792aecd4fbfa28bdb9fd44bf920c167f64c5653`. Contexto AGENTS,
CLAUDE, docs/ai, configurações, Makefile, executor compartilhado fixado,
pin_inventory/testes, políticas de saúde, documentação Wolfi e specs lidos.

Existiam duas referências à signing key remota: base Apko e única receita
Melange. Não havia pin, procedimento Wolfi nem segunda origem. Ambos pediam
a mesma URL em inicializações distintas, sem garantia de bytes idênticos.
Builds fresh buscavam a chave; `make bundle` podia reusar output existente.
O inventory só cobria Actions/reusables, imagens e versões de tools.

## Estratégia

1. Registrar requisitos/aceite antes do código e conferir fontes oficiais.
2. Usar `melange/keys/`: o executor fixado monta somente `melange/` em `/work`.
   A base Apko referencia `melange/keys/...` desde a raiz; Melange usa `keys/...`.
   Um JSON adjacente é a única fonte executável do SHA-256 esperado.
3. Estender inventory com local-key gerido por revisão humana e CLI offline
   `trust`. SHA-256 e OpenSSL validam arquivo; PyYAML já existente verifica
   apenas `contents.keyring`/`environment.contents.keyring`, sem parser novo.
4. Preflight no Makefile, build_image e job anterior ao reusable. A fixture
   de CA copia a chave revisada e verifica antes de executar Melange.
5. Reusar `pin_inventory check` no health diário: comparar fonte A atual,
   distinguir same/divergent/unavailable e nunca escrever a chave.
6. Testar falhas com cópias temporárias, executar checks e evidenciar limites.

## Decisões e hipóteses

Não criar segunda infraestrutura de pins nem manager automático. A nova
dependência artifacts → governance serve somente à verificação offline antes
de Apko; fica explícita no mapa/teste. OpenSSL já exigido para certificados
é usado para parsing RSA; não implementar parser criptográfico próprio.
O reusable continua no mesmo SHA e não precisa de modificação remota.

## Decisão arquitetural e limitação preservada

A leitura do código oficial da versão realmente executada encontrou
auto-discovery fora de `contents.keyring`: Apko `InitDB` consulta
`apk-configuration`/JWKS e acrescenta chaves ao keyring. `lock` também
registra essas chaves. Melange utiliza Apko internamente. Não foi encontrado
knob suportado para desativar seletivamente esse comportamento nas versões
fixadas; a versão oficial Apko v1.3.0 consultada mantém o caminho.

O experimento isolado confirmou o bypass: o mesmo índice assinado por chave
de fixture falha sem discovery e é aceito quando o servidor fornece essa
chave por JWKS. Um lint das configs, ou uma checagem tardia do lock, não
impede Melange de ter aceitado insumos usando discovery antes disso.

A revisão arquitetural independente informada pelo usuário aceitou reformular
a propriedade para a chave explícita local, pin e controles de rotação/drift.
O antigo BLOCKED_TOOLING explica por que exclusividade saiu do aceite local;
a evidência adversarial permanece **EXPECTED TOOLING LIMITATION REPRODUCED**.
Não alterar Apko, repositories ou verificações para modificar esse resultado.

Nesta continuação, preservar a implementação e os testes úteis; atualizar os
seis documentos, runbook e referências de produto; repetir todos os checks
pedidos, preflight, hash, monitor e mínimo real. Registrar HTTP 404 atual
somente se observado, com data. Manter a reprodução anterior sem contá-la
como teste verde do controle ou inventar uma nova execução.

Exclusividade corporativa passa a requisito posterior do P0-03: mirror/proxy
sem discovery e egress restrito, a definir por Cloud/Network/Security. Recomendar
issue futura upstream por modo suportado de explicit-keys-only, sem abri-la.

## Risco e rollback

Path local incorreto bloqueia o preflight; uma rotação upstream pode afetar a
verificação de packages e exige investigação, sem repin automático. Validar as
versões fixadas com lock/build mínimo. Monitor falha fechado para alerta, desacoplado
do build. Rollback é restaurar o último par chave/pin revisado por PR e repetir
os negativos; nunca voltar ao download automático nem ignorar assinatura.

## Validação

Suíte unitária/integrada, lints local/shared/workflows, actionlint, contexto
IA, diff whitespace; hash e fonte dupla; mínimos reais sem exigir lote CVE
verde. Nova revisão independente da entrega reformulada e hosted acceptance
permanecem posteriores; a revisão arquitetural já foi informada pelo usuário.
