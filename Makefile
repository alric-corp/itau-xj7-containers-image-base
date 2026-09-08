.DEFAULT_GOAL := help

UNAME_ARCH := $(shell uname -m)
ifeq ($(UNAME_ARCH),arm64)
  ARCH ?= aarch64
else ifeq ($(UNAME_ARCH),aarch64)
  ARCH ?= aarch64
else
  ARCH ?= x86_64
endif

MELANGE_KEY  := melange/.local-keys/melange.rsa
MELANGE_REPO := melange/packages

# apko/melange sempre rodam via `docker run` (nao como binario nativo extraido)
# para o Makefile funcionar em qualquer SO/arquitetura de dev (Mac, Linux, WSL).
DOCKER_MELANGE := docker run --rm -v "$(CURDIR)/melange":/work -w /work cgr.dev/chainguard/melange:latest
DOCKER_APKO    := docker run --rm -v "$(CURDIR)":/work -w /work -v /var/run/docker.sock:/var/run/docker.sock cgr.dev/chainguard/apko:latest

.PHONY: help list keygen bundle build run clean

help:
	@echo "Build local das imagens deste repositorio (sem publicar em nenhum registry)."
	@echo ""
	@echo "  make list                            lista os frameworks disponiveis"
	@echo "  make build FRAMEWORK=go1-26           builda uma imagem local (apko publish --local)"
	@echo "  make run FRAMEWORK=go1-26 \\"
	@echo "       ENTRYPOINT=/usr/bin/go ARGS=version   builda e roda um comando na imagem"
	@echo "  make clean                            remove chave e pacotes locais"
	@echo ""
	@echo "Variaveis: ARCH (padrao: $(ARCH), detectado do host)"

list:
	@for f in frameworks/*.yaml; do basename "$$f" .yaml; done

# Chave de assinatura efemera do melange (nunca commitada, veja .gitignore).
$(MELANGE_KEY):
	@mkdir -p $(dir $(MELANGE_KEY))
	$(DOCKER_MELANGE) keygen .local-keys/melange.rsa

keygen: $(MELANGE_KEY)

# Pacote bundle-pem-test (bundle.pem da Mozilla), consumido por todos os frameworks.
$(MELANGE_REPO): $(MELANGE_KEY) melange/bundle-pem-test.yaml
	docker run --privileged --rm -v "$(CURDIR)/melange":/work -w /work cgr.dev/chainguard/melange:latest \
		build bundle-pem-test.yaml --arch x86_64,aarch64 --signing-key .local-keys/melange.rsa
	@touch $(MELANGE_REPO)

bundle: $(MELANGE_REPO)

build: bundle
ifndef FRAMEWORK
	$(error defina FRAMEWORK, ex.: make build FRAMEWORK=go1-26. Rode "make list" para ver as opcoes)
endif
	$(DOCKER_APKO) publish frameworks/$(FRAMEWORK).yaml localhost/$(FRAMEWORK):local \
		--arch $(ARCH) --local \
		--repository-append /work/melange/packages \
		--keyring-append /work/melange/.local-keys/melange.rsa.pub

run: build
ifndef ENTRYPOINT
	$(error defina ENTRYPOINT, ex.: make run FRAMEWORK=go1-26 ENTRYPOINT=/usr/bin/go ARGS=version)
endif
	docker run --rm --entrypoint $(ENTRYPOINT) localhost/$(FRAMEWORK):local $(ARGS)

clean:
	rm -rf melange/.local-keys melange/packages
	rm -f *.tar sbom-*.json *.spdx.json
