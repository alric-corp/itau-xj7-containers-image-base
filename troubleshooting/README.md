# Kubernetes Troubleshooting Toolkit

Imagem Docker baseada em Alpine Linux com ferramentas para troubleshooting, debugging e operação de ambientes Kubernetes, AWS e containers.

## 📋 Descrição

Esta imagem fornece um toolkit portátil para diagnóstico e operação de clusters Kubernetes.

O objetivo é concentrar em uma única imagem ferramentas úteis para:

* Troubleshooting de Kubernetes
* Diagnóstico de rede e DNS
* Debugging de containers
* Operação de AWS
* Análise do runtime de containers
* Backup e recuperação com Velero
* Manipulação de JSON e YAML

A imagem foi pensada principalmente para:

* Laboratórios pessoais
* Ambientes de desenvolvimento
* Troubleshooting temporário
* Ephemeral Containers
* Diagnóstico de nodes e workloads Kubernetes

> Esta imagem não foi projetada para executar aplicações em produção.

---

## 🛠️ Ferramentas incluídas

### Kubernetes & Orquestração

* `kubectl` - Cliente de linha de comando do Kubernetes
* `helm` - Gerenciador de pacotes para Kubernetes
* `velero` - Backup e recuperação de clusters Kubernetes

### Container Runtime

* `crictl` - Cliente CLI para runtimes compatíveis com CRI
* `nerdctl` - CLI compatível com Docker para containerd

Essas ferramentas permitem realizar diagnósticos diretamente no runtime de containers quando o socket do containerd estiver disponível.

### Cloud & AWS

* `aws-cli` - Interface de linha de comando da AWS
* AWS CLI completion configurado no Bash

As credenciais AWS **não são armazenadas na imagem**.

Elas devem ser fornecidas em runtime utilizando mecanismos como:

* `~/.aws`
* Variáveis de ambiente
* IAM Roles
* IAM Roles for Service Accounts (IRSA)
* AWS IAM Identity Center / SSO

---

## 🌐 Análise de Rede

* `tcpdump` - Captura e análise de pacotes
* `net-tools` - `netstat`, `ifconfig`, `route`, entre outros
* `iputils` - Ferramentas como `ping`
* `traceroute` - Análise do caminho de rede
* `mtr` - Diagnóstico combinado de ping e traceroute
* `netcat-openbsd` - Testes de conectividade TCP/UDP
* `bind-tools`

  * `dig`
  * `nslookup`
  * `host`
* `busybox-extras` - Utilitários adicionais de rede
* `dnsperf` - Testes e troubleshooting de DNS
* `resperf` - Testes de performance de resolvers DNS

O `dnsperf` é compilado utilizando Alpine Linux para manter compatibilidade com `musl`, evitando dependências de binários compilados para glibc/Debian.

---

## 📊 Processamento de Dados

* `jq` - Processamento de JSON
* `yq` - Processamento de YAML

Exemplos:

```bash
kubectl get pods -o json | jq .
```

```bash
kubectl get deployment -o yaml | yq .
```

---

## 🔧 Utilitários de Sistema

* `curl`
* `wget`
* `vim`
* `git`
* `bash`
* `fish`
* `zip`
* `coreutils`
* `openssl`
* `ca-certificates`

---

## 🔍 Debugging & Diagnóstico

* `strace` - Rastreamento de chamadas de sistema
* `lsof` - Lista arquivos e sockets abertos
* `procps`

  * `ps`
  * `top`
  * outros utilitários de processos
* `shadow` - Gerenciamento de usuários e grupos
* `coreutils` - Utilitários GNU

---

## 📚 Documentação

* `groff`
* `mandoc`

Permitem utilização de documentação e man pages disponíveis no ambiente.

---

# ⚡ Features

## Bash Completion

Autocomplete configurado para:

* `kubectl`
* `helm`
* `velero`
* `aws`

## Alias do kubectl

O seguinte alias está configurado:

```bash
k=kubectl
```

O autocomplete do `kubectl` também funciona com o alias `k`.

Exemplo:

```bash
k get pods
```

---

# 🚀 Build

Clone o projeto e execute:

```bash
docker build \
  -t k8s-tools:1.0.0 \
  .
```

Para verificar a imagem:

```bash
docker images k8s-tools
```

---

# 🚀 Como utilizar

A imagem pode ser utilizada de diferentes maneiras:

* Docker
* Podman
* Kubernetes Pod
* Kubernetes Deployment
* Kubernetes Ephemeral Container
* Troubleshooting privilegiado de Nodes

---

## Requisitos

Dependendo da forma de utilização:

* Docker ou Podman
* Kubernetes
* kubectl
* Cluster Kubernetes acessível

Helm **não precisa estar instalado na máquina host** para utilizá-lo dentro do container.

---

# 🐳 Docker

## Uso básico

```bash
docker run --rm -it \
  k8s-tools:1.0.0
```

O shell padrão será:

```bash
/bin/bash
```

---

## AWS

As credenciais AWS não fazem parte da imagem.

Para utilizar os profiles configurados na máquina host:

```bash
docker run --rm -it \
  -v "$HOME/.aws:/root/.aws:ro" \
  k8s-tools:1.0.0
```

Dentro do container:

```bash
aws sts get-caller-identity
```

Ou:

```bash
aws eks list-clusters
```

---

## AWS + Kubernetes

Para utilizar AWS CLI e o kubeconfig da máquina host:

```bash
docker run --rm -it \
  -v "$HOME/.aws:/root/.aws:ro" \
  -v "$HOME/.kube:/root/.kube:ro" \
  k8s-tools:1.0.0
```

Depois:

```bash
kubectl get nodes
```

```bash
kubectl get pods -A
```

```bash
aws sts get-caller-identity
```

---

# ☸️ Kubernetes

## Pod de troubleshooting simples

Para troubleshooting comum, prefira iniciar sem privilégios elevados.

Crie:

```bash
vim troubleshooting-pod-toolkit.yaml
```

Manifesto:

```yaml
apiVersion: v1
kind: Pod

metadata:
  name: k8s-toolkit

spec:
  containers:
    - name: k8s-tools
      image: k8s-tools:1.0.0
      command:
        - /bin/bash
        - -c
        - sleep 86400

      resources:
        requests:
          memory: "300Mi"
          cpu: "100m"

  restartPolicy: Never
```

> A imagem precisa estar disponível em um registry acessível pelo cluster ou ser carregada previamente nos nodes do ambiente de laboratório.

Criando o Pod:

```bash
kubectl apply -f troubleshooting-pod-toolkit.yaml
```

Conectando:

```bash
kubectl exec -it k8s-toolkit -- /bin/bash
```

---

# 🔥 Troubleshooting privilegiado

Alguns diagnósticos exigem acesso ao host, namespaces de rede ou runtime de containers.

Para esses cenários é possível executar a imagem com privilégios adicionais.

> ⚠️ **Atenção:** containers privilegiados com acesso ao socket do container runtime possuem permissões extremamente elevadas sobre o Node. Utilize somente em ambientes controlados e quando realmente necessário.

Exemplo:

```yaml
apiVersion: apps/v1
kind: Deployment

metadata:
  name: troubleshooting-pod-toolkit

spec:
  replicas: 1

  selector:
    matchLabels:
      app: k8s-toolkit

  template:
    metadata:
      labels:
        app: k8s-toolkit

    spec:
      containers:
        - name: k8s-tools

          image: k8s-tools:1.0.0

          command:
            - /bin/bash
            - -c
            - sleep 86400

          env:
            - name: CONTAINER_RUNTIME_ENDPOINT
              value: unix:///host/run/containerd/containerd.sock

          resources:
            requests:
              memory: "300Mi"
              cpu: "100m"

          securityContext:
            privileged: true
            runAsUser: 0

          volumeMounts:
            - name: containerd
              mountPath: /host/run/containerd

      hostNetwork: true

      dnsPolicy: ClusterFirstWithHostNet

      volumes:
        - name: containerd
          hostPath:
            path: /run/containerd
            type: Directory
```

Criando:

```bash
kubectl apply -f troubleshooting-pod-toolkit.yaml
```

Identificando o Pod:

```bash
kubectl get pods -l app=k8s-toolkit
```

Conectando:

```bash
kubectl exec -it <POD_NAME> -- /bin/bash
```

---

# 📦 Containerd

Quando o socket do containerd estiver montado:

```bash
crictl ps
```

Para listar todos os containers:

```bash
crictl ps -a
```

Também é possível utilizar:

```bash
nerdctl ps
```

Dependendo da configuração do containerd, pode ser necessário especificar namespace ou endpoint.

---

# 🧩 Kubernetes Ephemeral Container

Ephemeral Containers são úteis para realizar troubleshooting em aplicações que não possuem ferramentas de diagnóstico.

Isso é particularmente útil para imagens:

* Distroless
* Scratch
* Minimalistas
* Sem shell
* Sem ferramentas de rede

Exemplo:

```bash
kubectl debug -it <POD_NAME> \
  --image=<REGISTRY>/k8s-tools:1.0.0 \
  --target=<CONTAINER_NAME>
```

`--target` deve receber o **nome do container existente dentro do Pod**, e não o nome do Pod.

Para troubleshooting que exija um perfil mais privilegiado:

```bash
kubectl debug -it <POD_NAME> \
  --image=<REGISTRY>/k8s-tools:1.0.0 \
  --target=<CONTAINER_NAME> \
  --profile=sysadmin
```

Exemplo para identificar os containers:

```bash
kubectl get pod <POD_NAME> \
  -o jsonpath='{.spec.containers[*].name}'
```

---

# 🌐 Troubleshooting de Rede

## Ping

```bash
ping google.com
```

## DNS

```bash
dig kubernetes.default.svc.cluster.local
```

```bash
nslookup kubernetes.default.svc.cluster.local
```

## Porta TCP

```bash
nc -vz <HOST> <PORT>
```

Exemplo:

```bash
nc -vz kubernetes.default.svc 443
```

## Traceroute

```bash
traceroute <HOST>
```

## MTR

```bash
mtr <HOST>
```

---

# 🔬 tcpdump

Para capturar pacotes:

```bash
tcpdump -i any
```

Salvando a captura:

```bash
tcpdump -i any \
  -w /tmp/capture.pcap
```

Filtrando por porta:

```bash
tcpdump -i any \
  port 443
```

Filtrando por host:

```bash
tcpdump -i any \
  host <IP>
```

Dependendo do ambiente, `tcpdump` pode exigir capabilities adicionais ou execução privilegiada.

---

# 🌐 DNSPerf

O `dnsperf` pode ser utilizado para gerar carga e analisar o comportamento de servidores DNS.

Verificando a instalação:

```bash
dnsperf -h
```

Também está disponível:

```bash
resperf -h
```

O `dnsperf` é compilado durante o build utilizando Alpine Linux, mantendo compatibilidade nativa com a libc `musl` utilizada pela imagem final.

---

# 💾 Velero

Verificando o cliente:

```bash
velero version --client-only
```

Exemplo de consulta:

```bash
velero backup get
```

```bash
velero restore get
```

A imagem contém apenas o cliente Velero. A utilização dos recursos de backup e restore depende de uma instalação e configuração adequada do Velero no cluster.

---

# 🧪 Smoke Tests

Durante o build, as principais ferramentas são verificadas automaticamente.

Entre elas:

```text
kubectl
helm
aws
velero
dnsperf
resperf
jq
yq
crictl
nerdctl
openssl
```

Caso uma dessas ferramentas principais esteja quebrada ou não possa ser executada, o build deve falhar.

---

# 🔐 Segurança

## Credenciais AWS

Credenciais AWS **não devem ser adicionadas ao Dockerfile ou à imagem**.

Não utilize:

```dockerfile
ARG AWS_ACCESS_KEY_ID
ARG AWS_SECRET_ACCESS_KEY
ARG AWS_SESSION_TOKEN
```

para armazenar credenciais durante o build.

Esta imagem não precisa acessar recursos privados durante seu processo de construção e, portanto, não necessita de Docker Build Secrets para funcionar.

As credenciais devem ser disponibilizadas somente quando o container for executado.

Exemplo:

```bash
-v "$HOME/.aws:/root/.aws:ro"
```

Em Kubernetes, prefira os mecanismos de identidade fornecidos pelo ambiente em vez de incorporar credenciais na imagem.

---

# 🔐 Certificados

A imagem utiliza o conjunto padrão de Certificate Authorities fornecido pelo Alpine através do pacote:

```text
ca-certificates
```

Não são utilizados certificados corporativos ou certificados privados.

Caso seja necessário adicionar uma CA privada em um laboratório específico, ela deve ser fornecida separadamente.

---

# 🏗️ Arquiteturas

A imagem pode ser construída para:

```text
linux/amd64
linux/arm64
```

Em máquinas Apple Silicon, o build local normalmente utilizará:

```text
linux/arm64
```

Para builds multi-arquitetura pode ser utilizado Docker Buildx.

Exemplo:

```bash
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t <REGISTRY>/k8s-tools:1.0.0 \
  .
```

---

# 📦 Base Image

```text
Alpine Linux 3.22
```

A versão da imagem base é fixada no Dockerfile através de:

```dockerfile
ARG ALPINE_VERSION=3.22
```

---

# 🔄 Versões

| Ferramenta | Versionamento                                       |
| ---------- | --------------------------------------------------- |
| Alpine     | `3.22`                                              |
| Velero     | Definido por `VELERO_VERSION`                       |
| DNSPerf    | Definido por `DNSPERF_VERSION`                      |
| Kubectl    | Pacote disponibilizado pelo repositório Alpine 3.22 |
| Helm       | Pacote disponibilizado pelo repositório Alpine 3.22 |
| AWS CLI    | Pacote disponibilizado pelo repositório Alpine 3.22 |
| crictl     | Pacote disponibilizado pelo repositório Alpine 3.22 |
| nerdctl    | Pacote disponibilizado pelo repositório Alpine 3.22 |

As versões configuradas diretamente no Dockerfile podem ser consultadas nos respectivos `ARG`.

Exemplo:

```dockerfile
ARG ALPINE_VERSION=3.22
ARG VELERO_VERSION=v1.18.2
ARG DNSPERF_VERSION=v2.14.0
```

---

# 📄 Licença

Uso pessoal.
