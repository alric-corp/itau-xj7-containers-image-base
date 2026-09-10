# syntax=docker/dockerfile:1

# ==============================================================================
# Versions
# ==============================================================================

ARG ALPINE_VERSION=3.22
ARG VELERO_VERSION=v1.18.2
ARG DNSPERF_VERSION=v2.14.0


# ==============================================================================
# Velero
# ==============================================================================
# Utiliza diretamente o binário da imagem oficial.
# Não é necessário baixar ZIP/source code nem recompilar o Velero.

FROM velero/velero:${VELERO_VERSION} AS velero


# ==============================================================================
# DNSPerf Builder
# ==============================================================================
# Compila o dnsperf em Alpine para evitar copiar um binário glibc/Debian
# para uma imagem Alpine/musl.

FROM alpine:${ALPINE_VERSION} AS dnsperf-builder

ARG DNSPERF_VERSION

RUN apk add --no-cache \
        autoconf \
        automake \
        build-base \
        ck-dev \
        git \
        ldns-dev \
        libtool \
        nghttp2-dev \
        openssl-dev \
        pkgconf \
    && git clone \
        --branch "${DNSPERF_VERSION}" \
        --depth 1 \
        https://codeberg.org/DNS-OARC/dnsperf.git \
        /src/dnsperf \
    && cd /src/dnsperf \
    && ./autogen.sh \
    && ./configure \
        --prefix=/usr/local \
    && make -j"$(getconf _NPROCESSORS_ONLN)" \
    && make install DESTDIR=/out


# ==============================================================================
# Kubernetes Troubleshooting Toolkit
# ==============================================================================

FROM alpine:${ALPINE_VERSION}

ARG VELERO_VERSION
ARG DNSPERF_VERSION

LABEL org.opencontainers.image.title="k8s-troubleshooting-toolkit" \
      org.opencontainers.image.description="Personal Kubernetes, AWS and network troubleshooting toolkit" \
      org.opencontainers.image.version="1.0.0"


# ==============================================================================
# Runtime dependencies
# ==============================================================================

RUN apk add --no-cache \
        \
        # Kubernetes / Container Runtime
        kubectl \
        helm \
        cri-tools \
        nerdctl \
        \
        # AWS
        aws-cli \
        groff \
        mandoc \
        \
        # Shell
        bash \
        bash-completion \
        fish \
        \
        # Data processing
        jq \
        yq \
        \
        # Network troubleshooting
        busybox-extras \
        bind-tools \
        curl \
        iputils \
        mtr \
        net-tools \
        netcat-openbsd \
        tcpdump \
        traceroute \
        wget \
        \
        # Debugging / System
        coreutils \
        lsof \
        procps \
        shadow \
        strace \
        \
        # General utilities
        ca-certificates \
        git \
        openssl \
        vim \
        zip \
        \
        # dnsperf runtime dependencies
        ck \
        ldns \
        nghttp2-libs


# ==============================================================================
# Velero
# ==============================================================================

COPY --from=velero \
     --chmod=0755 \
     /velero \
     /usr/local/bin/velero


# ==============================================================================
# DNSPerf
# ==============================================================================

COPY --from=dnsperf-builder \
     --chmod=0755 \
     /out/usr/local/bin/dnsperf \
     /usr/local/bin/dnsperf

COPY --from=dnsperf-builder \
     --chmod=0755 \
     /out/usr/local/bin/resperf \
     /usr/local/bin/resperf


# ==============================================================================
# kubectl compatibility
# ==============================================================================
# Alguns charts/scripts possuem /bin/kubectl hardcoded.

RUN ln -sf /usr/bin/kubectl /bin/kubectl


# ==============================================================================
# Bash autocomplete
# ==============================================================================

RUN mkdir -p /etc/bash_completion.d \
    \
    && kubectl completion bash \
        > /etc/bash_completion.d/kubectl \
    \
    && helm completion bash \
        > /etc/bash_completion.d/helm \
    \
    && velero completion bash \
        > /etc/bash_completion.d/velero \
    \
    && printf '%s\n' \
        '' \
        '# Kubernetes aliases' \
        'alias k=kubectl' \
        'complete -o default -F __start_kubectl k' \
        >> /etc/bash/bashrc \
    \
    && printf '%s\n' \
        '' \
        '# AWS CLI completion' \
        'if command -v aws_completer >/dev/null 2>&1; then' \
        '    complete -C "$(command -v aws_completer)" aws' \
        'fi' \
        >> /etc/bash/bashrc


# ==============================================================================
# Smoke tests
# ==============================================================================
# Se alguma ferramenta principal estiver quebrada, o próprio docker build falha.

RUN kubectl version --client \
    && helm version --short \
    && aws --version \
    && velero version --client-only \
    && dnsperf -h >/dev/null 2>&1 \
    && resperf -h >/dev/null 2>&1 \
    && jq --version \
    && yq --version \
    && crictl --version \
    && nerdctl --version \
    && openssl version


# ==============================================================================
# Runtime
# ==============================================================================

WORKDIR /workspace

CMD ["/bin/bash"]