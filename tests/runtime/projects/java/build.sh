#!/bin/sh
# Wrapper com shebang de shell, no mesmo formato de mvnw/gradlew: só executa
# porque a variante -dev tem shell (busybox). Foi exatamente essa lacuna que
# a revisão do M07 encontrou — um Dockerfile real de projeto Java não roda
# sem /bin/sh, nem em exec-form.
set -eu
OUT="${1:?uso: build.sh <diretorio-de-saida>}"
mkdir -p "$OUT"
javac -d "$OUT" Main.java
