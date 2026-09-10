# Multi-stage real do M07, versionado: compila na variante -dev e roda na
# variante de runtime. As duas imagens chegam por build-arg porque o
# executor as carrega do artifact OCI candidato, não de um registry.
ARG BUILD_IMAGE
ARG RUNTIME_IMAGE

FROM ${BUILD_IMAGE} AS build
# HOME/caches explícitos: a imagem -dev não presume um home gravável.
ENV HOME=/tmp \
    GOCACHE=/tmp/gocache \
    GOMODCACHE=/tmp/gomodcache \
    GOPATH=/tmp/gopath \
    GOFLAGS=-mod=mod \
    GOTOOLCHAIN=local \
    CGO_ENABLED=0
WORKDIR /app
COPY --chown=10000:10000 go.mod main.go ./
# Shell-form de propósito: é o `RUN` normal de um Dockerfile e só funciona
# porque a variante -dev tem shell (M07). Sem rede: o módulo é stdlib pura.
RUN go build -trimpath -o /app/runtime-contract .

FROM ${RUNTIME_IMAGE}
COPY --from=build --chown=10000:10000 /app/runtime-contract /app/runtime-contract
ENTRYPOINT ["/app/runtime-contract"]
