# TASKS — P1-03 Wolfi signing-key defense-in-depth

- [x] T01 / A05: reconstruir estado e comparar duas fontes oficiais antes da adoção.
- [x] T02 / A01–A10: reformular requisitos, aceite e plano conforme decisão arquitetural.
- [x] T03 / A01–A04: preservar chave/pin, preflight e consumidores locais.
- [x] T04 / A02/A06/A07: preservar monitor detect-only, lint e rotação revisada.
- [x] T05 / A03/A04/A07: preservar fixtures negativas e regressões locais.
- [x] T06 / A08: preservar prova de discovery como EXPECTED TOOLING LIMITATION REPRODUCED.
- [x] T07 / A01–A10: repetir checks, mínimos reais e completar evidence/handoff,
  incluindo os diagnósticos preexistentes do actionlint amplo.
- [x] T08 / A08: registrar requisito corporativo P0-03 e recomendação upstream, sem implementar/publicar.

A antiga task de eliminar auto-discovery não foi concluída nem ocultada:
exclusividade saiu do aceite P1-03 por decisão arquitetural explícita. O
FAIL da propriedade original continua na evidence. Não há mudança de Apko,
expectedFailure ou teste útil removido para obter verde.

## Dependências externas

Nova revisão independente posterior por outro modelo; integração e execução
hospedada somente após autorização. P0-03 exige decisão Cloud/Network/Security
se necessária independência da origem. Zlib permanece fora desta fatia.
