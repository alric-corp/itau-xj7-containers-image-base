# M09/M16: segurança de cache antes de adotá-lo no caminho de release

## Estado atual: nenhum cache no caminho de release

`grep -l actions/cache .github/workflows/*.yml` só encontra
`cve-triage.lock.yml` — o workflow gerado pelo `gh aw compile` para o agente
de triagem de CVE (pausado, sem gatilho automático, fora do escopo dos
required checks e do lint de workflows). **`workflow.yml`,
`validate-base-images.yml`, `build-base-images.yml`, `promote-stable.yml`,
`recover-stable.yml`, `test-runtime-images.yml` e `test-promotion.yml` — os
sete que compõem o caminho de release — não usam `actions/cache` hoje.**
Esta seção documenta a política a aplicar **quando** isso mudar, e comprova
empiricamente as garantias da plataforma que essa política pressupõe.

## Quem pode gravar/restaurar cada cache, e por quê

Modelo verificado contra a [documentação oficial de cache](https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching)
e confirmado empiricamente nesta entrega (não só citado):

- **Escopo por branch, com fallback só para a branch base/default.** Um
  cache gravado numa branch só é restaurável por execuções na mesma branch,
  ou por uma branch cuja base (no fluxo de PR) seja aquela branch, incluindo
  o fallback para a branch default. Duas branches irmãs, sem relação de
  base uma com a outra, não compartilham cache.
- **Escrita restrita ao evento/branch que gerou o run.** Uma execução
  disparada por uma branch/PR só grava cache no escopo dessa branch/PR —
  não sobrescreve o cache de `main` nem de outra branch.
- **Chaves diferentes por nome de workflow não são isolamento.** Duas
  chaves distintas dentro do mesmo escopo de branch continuam
  restauráveis por qualquer workflow que rode nessa branch — o isolamento
  real vem do escopo de branch, não do nome da chave.

### Prova empírica real (nesta entrega)

Duas branches descartáveis, sem relação de parentesco entre si (ambas
criadas diretamente a partir de `main`, nenhuma é PR da outra):

1. `test/cache-scope-writer`: gravou um cache com uma chave fixa
   (`cache-scope-probe-fixed-key`) contendo um arquivo-marcador.
2. `test/cache-scope-reader`: tentou restaurar a **mesma chave**.

Resultado real, não simulado: `cache-hit=` (vazio — miss) e o arquivo
marcador **ausente** no restore. O cache gravado por uma branch não vazou
para uma branch irmã não relacionada. Runs reais (removidos após a
verificação, junto com as duas branches):

- Writer: `Save cache` `success`, gravando o marcador.
- Reader: `Restore cache` `success` (executou sem erro), mas o cache-hit foi
  negativo e o marcador não apareceu — isolamento confirmado, não presumido.

**Não testado nesta entrega:** isolamento a partir de um fork externo. A
plataforma já documenta esse caso com a mesma regra de escopo por
branch/evento, e M05 já estabelece separadamente que PRs de fork não
recebem `id-token: write` nem qualquer credencial — a superfície de ataque
relevante (roubar segredos via cache) já está coberta por essa ausência de
credencial, independente do cache. Testar esse caso especificamente exigiria
um repositório de fork de verdade, fora do escopo desta entrega; registrado
aqui como pendência explícita, não presumido como equivalente ao teste
acima.

## Validar downloads restaurados antes de executá-los

[`verify_cache_integrity.py`](../.github/scripts/verify_cache_integrity.py)
generaliza o mesmo modelo de confiança que `scripts/certificados.sh` já usa
para o bundle de certificados corporativo: um lockfile de checksums SHA-256
committado no Git, e o conteúdo restaurado só é confiável depois de bater
com o lockfile — nunca só porque veio de uma fonte rápida (cache) ou local.

`verify_checksums(directory, lockfile_text)`:

- Rejeita uma linha malformada do lockfile fechado (fail closed), em vez de
  deixar passar uma entrada que não valida nada — mesma regra que
  `certificados.sh` já aplica ao lockfile de certificados.
- Levanta `CacheIntegrityError` se um arquivo restaurado não bate com o
  hash fixado (**arquivo adulterado é rejeitado**, testado com um caso real
  de conteúdo alterado depois do lockfile gerado) ou se um arquivo esperado
  está ausente (restore parcial).
- Não decide o que fazer quando o cache está ausente — isso é decisão do
  chamador (cache ausente deve continuar permitindo build correto, só sem o
  atalho; não é responsabilidade deste validador forçar um fallback).

7 testes cobrindo: parsing válido, linhas malformadas de cada tipo (hex
maiúsculo, tamanho errado, separador errado), lockfile vazio, conteúdo
íntegro aprovado, arquivo adulterado rejeitado, arquivo ausente rejeitado.

Pronto para acoplar a qualquer `actions/cache/restore` futuro no caminho de
release: o passo seguinte ao restore chamaria `verify_checksums` contra um
lockfile committado antes de usar o conteúdo restaurado para qualquer coisa
executável.

## O que não muda

- **OCI aprovado continua sendo artifact vinculado à validação (M02), nunca
  cache promovível.** A publicação usa Skopeo com `--preserve-digests`
  contra o artifact que passou pelo scan, não um cache — isso não muda
  independente de qualquer adoção futura de `actions/cache` para acelerar
  downloads de ferramentas.
- Nenhum diretório executável amplo do workspace deve ser restaurado de um
  cache sem a verificação acima — isso vale como regra de design para
  qualquer adoção futura, não como código a escrever hoje (não há cache
  para restringir ainda).

## Aceite

- [x] Documentado quem pode gravar/restaurar cada cache e seu escopo por
  ref/evento, com a regra verificada contra a documentação oficial.
- [x] Isolamento entre branches não relacionadas comprovado empiricamente
  com um teste real e descartável (não simulado, não só citado da
  documentação).
- [x] Padrão de validação de conteúdo restaurado implementado e testado,
  incluindo rejeição real de arquivo adulterado — pronto para uso quando
  cache for adotado no caminho de release.
- [x] Nenhum cache foi adicionado ao caminho de release nesta entrega —
  cache ausente continua permitindo build correto, por não haver cache
  algum ainda.
- [ ] Isolamento a partir de um fork externo real não foi testado
  (pendência explícita, ver acima). Chaves por nome de workflow como
  suposto isolamento: não há hoje nenhuma chave de cache no caminho de
  release para essa suposição incorreta se manifestar; a regra fica
  registrada para quando a primeira for introduzida.
