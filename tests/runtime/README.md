# Contratos funcionais M08/M10 — Node e Python

O executor testa as duas plataformas de um artifact OCI existente, sem rebuild
da imagem base, publicação ou autenticação AWS. Aceita Node 22/24, suas variantes
`-dev`, e Python 3.13/3.14 conforme o catálogo `frameworks/`. Outros runtimes
falham explicitamente: ainda precisam de aplicações compiladas e Dockerfiles
multi-stage próprios.

```sh
python3 -B .github/scripts/runtime_images.py /caminho/candidate.oci nodejs24 --reports /tmp/runtime-reports
```

O diretório deve conter o layout completo e `validated-index.json`, como nos
artifacts `validated-oci-<framework>`. Requer Python 3.10+, OpenSSL com `req
-addext`, Docker acessível e emulação da arquitetura diferente da do daemon.
Docker Desktop já forneceu essa emulação no exercício local; o workflow usa
QEMU no runner Linux. O host precisa aceitar conexões do container em duas
portas efêmeras via `host.docker.internal`/`host-gateway`.

O executor verifica todos os blobs do OCI e sua correspondência com a evidência
de validação. Skopeo (mesmo digest fixado no publicador) importa cada plataforma
para uma tag local exclusiva. Uma reexportação pelo Docker confirma o hash da
configuração, que inclui os hashes das camadas descomprimidas. Não se presume
que `docker inspect .Id` seja o digest da configuração: no image store containerd
ele pode ser um digest de manifest. Os relatórios preservam essas identidades
separadamente.

Os probes usam apenas bibliotecas padrão, montados somente para leitura sobre
o candidato. Conferem:

- Versão major de Node ou major/minor de Python correspondente ao framework.
- UID e GID reais iguais a 10000, herdados da imagem, sem `--user` no executor.
- Escrita em `/app` rejeitada com `EROFS`; escrita e leitura permitidas somente
  no `/tmp` explicitamente fornecido como tmpfs de 16 MiB.
- Parsing do bundle presente em `/etc/ssl/certs/ca-certificates.crt`.
- HTTPS com CA efêmera confiável aceito e HTTPS com outra CA rejeitado por erro
  de verificação de certificado. Erro de conexão/timeout não aprova o negativo.
- Shell `/bin/sh` funcional como UID/GID 10000 nas variantes `-dev`.

O processo roda sem capabilities, com `no-new-privileges` e raiz somente leitura.
Não há `--privileged` ou montagem do socket Docker dentro do candidato. As
chaves TLS ficam no host e são descartadas ao final. Só o certificado público
confiável é montado no candidato. As tags e containers criados têm nomes únicos;
o cleanup não executa prune nem remove recursos de outras sessões.

Cada relatório `runtime-<framework>-<arch>.json` registra os digests de índice,
manifest e configuração, o resultado e execução nativa/emulada em relação à
arquitetura do **daemon Docker**. Qualquer falha retorna código diferente de zero.
A segunda arquitetura continua sendo testada quando a primeira falha; erro de
integridade/setup sobrescreve os dois relatórios com falha, sem reutilizar sucesso
antigo. Um encerramento forçado do processo/daemon pode impedir o cleanup e a
gravação final, portanto ausência de evidência nunca deve autorizar publicação.

## Integração com M13

`test-runtime-images.yml` é um workflow reutilizável e também oferece dispatch
manual sobre artifacts de outro run **deste repositório**. Não está conectado ao
gate de publicação nesta entrega. Para a integração, o chamador deve:

1. Esperar o artifact do framework, chamar este workflow com `framework` e
   `artifact-run-id` vazio (o próprio run), concedendo `contents: read` e
   `actions: read`.
2. Fazer o publicador daquele framework depender de sucesso neste contrato e
   na validação/scan. Preservar o artifact/digest testado, sem rebuild ou troca.
3. Manter a falha visível, não usar `continue-on-error`, e não tratar como sucesso
   os frameworks ainda sem contrato. Definir explicitamente a cobertura gradual.
4. Confirmar execução no runner hospedado e um teste negativo bloqueando a
   publicação. O dispatch isolado serve para diagnóstico, não para autorizar
   publicação de outro run.

A retenção de evidências é 30 dias. Reexecução depende também do OCI original,
cuja retenção atual é 3 dias; guardar o relatório não estende esse prazo. O novo
workflow está no actionlint do gate rápido; os testes do executor são descobertos
pela suíte Python existente. O pin Skopeo no executor precisa acompanhar as
atualizações do publicador; incluir essa referência ao integrar a automação M09.

## Evidência e limites desta entrega

Em 09/09/2026, as seis variantes suportadas (Node 22/24, ambas as variantes dev,
Python 3.13/3.14) passaram em amd64 emulado e arm64 nativo: **12 execuções reais**
no daemon Docker do Mac ARM. As duas variantes dev passaram também no shell.
Todos os artifacts da matriz positiva vieram do
[run 34398032502](https://github.com/alric-corp/itau-xj7-containers-image-base/actions/runs/34398032502),
push na `main`, commit `146a1238da67eb2e37a9431d188fa5a26052e606`. O run agregado
falhou nos jobs de dotnet8; isso não invalida os artifacts individuais Node/Python
nem significa que esta entrega resolveu aquele bloqueio. IDs de artifacts e
digests estão na evidência. Rotular deliberadamente um OCI local Node 24 como
Node 22 falhou nas duas
arquiteturas com saída 1. Isso não é resultado de teste de um candidato Node 22.
Os resultados estão em [evidence-2026-09-09.json](evidence-2026-09-09.json).

Ainda faltam implementar Go/Java/.NET, executar o workflow no GitHub e conectá-lo ao gate por framework
com M13. O TLS usa `NODE_EXTRA_CA_CERTS`/`SSL_CERT_FILE` com uma CA sintética:
testa os mecanismos de confiança dos runtimes, mas não comprova distribuição,
pin, legitimidade ou confiança end-to-end do bundle corporativo. O parsing do
bundle da imagem é um check separado. M08/M10 continuam parciais.
