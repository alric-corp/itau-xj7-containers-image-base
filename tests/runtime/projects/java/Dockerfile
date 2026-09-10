# Multi-stage real do M07, versionado: compila com javac na variante -dev
# (JDK) e roda na variante de runtime (JRE, sem javac). As duas imagens
# chegam por build-arg porque o executor as carrega do artifact OCI
# candidato, não de um registry.
ARG BUILD_IMAGE
ARG RUNTIME_IMAGE

FROM ${BUILD_IMAGE} AS build
ENV HOME=/tmp
WORKDIR /app
COPY --chown=10000:10000 Main.java build.sh ./
# Executa o wrapper de shell, não `javac` direto: é o caminho que mvnw e
# gradlew usam e o que a variante -dev precisa suportar de verdade.
RUN ./build.sh /app/classes

FROM ${RUNTIME_IMAGE}
COPY --from=build --chown=10000:10000 /app/classes /app/classes
ENTRYPOINT ["java", "-cp", "/app/classes", "Main"]
