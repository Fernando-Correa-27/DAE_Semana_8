# 02 · Equipo de agentes

Volver al [[00-Indice]] · Anterior: [[01-Auditoria-inicial]] · Siguiente: [[03-Requisitos-y-aceptacion]]

## Los once agentes

| # | Agente | Prioridad | Qué entregó |
|---|---|---|---|
| 1 | Analista de requisitos y producto | Imprescindible | `docs/requisitos.md` (actores, casos de uso, ~142 requisitos con criterio comprobable, riesgos, ambigüedades) y `docs/trazabilidad.md` (matriz requisito → implementación → prueba) |
| 2 | Arquitecto de software | Imprescindible | `docs/arquitectura.md` y los tres ADR de `docs/adr/`; decisiones Q-05 y Q-06 |
| 3 | Agente de seguridad | Imprescindible | `docs/seguridad.md`: auditoría de autenticación, autorización, secretos, CSRF, frontera del agente y mapa OWASP API Top 10 |
| 4 | Desarrollador backend Django | Imprescindible | Partes 2 y 3 (`quizctl.py`, `quiz/permissions.py`), interfaz web (`quiz/web_*.py`, plantillas, CSS) y corrección de la revisión |
| 5 | Tester (QA) | Imprescindible | Ampliación de cobertura: `test_services.py`, `test_http_matrix.py`, `test_http_client.py`, `test_persistence.py`, `test_query_counts.py`, `test_web_gaps.py`, `test_web_review.py` |
| 6 | Revisor de código | Imprescindible | `docs/revision-codigo.md`: veredicto CAMBIOS con 1 bloqueante, 9 importantes y 20 menores, con evidencia propia |
| 7 | Documentador | Imprescindible | `README.md` reescrito, actualización de `docs/trazabilidad.md` y `docs/requisitos.md`, `docs/decisiones-docker-ci.md` y esta bitácora |
| 8 | Especialista en bases de datos | Recomendado | Revisión del esquema y de las migraciones: `docs/modelo-datos.md` |
| 9 | Arquitecto de IA | Recomendado | `docs/frontera-ia.md`: auditoría de la frontera R0/R1/R2 y del texto hostil |
| 10 | DevOps e infraestructura | Opcional | **No intervino.** Sin Docker ni CI (ver [[11-Docker-y-CI]]) |
| 11 | Especialista en rendimiento | Opcional | **No intervino.** El riesgo N+1 quedó cubierto por pruebas de conteo de consultas |

## Por qué esa composición

- **Imprescindibles (1–7):** cubren el ciclo completo —requisitos → diseño → seguridad → implementación
  → pruebas → revisión → documentación— y corresponden a entregables reales del repositorio.
- **Recomendados (8–9):** el contrato ya traía riesgo de N+1 (BD) y hay una frontera de IA con riesgo de
  *prompt injection* (IA). Ambos existen y había que protegerlos.
- **Opcionales (10–11):** no hay CI, ni contenedores, ni SLA de rendimiento en un laboratorio local. Se
  activan solo si el alcance crece.
- **No incorporado: especialista frontend/UX/UI.** El proyecto es headless por definición; una interfaz
  server-rendered la cubre el arquitecto y el backend. Si algún día se añade una SPA, se evaluaría.

## Cómo se colaboró

El protocolo está en `AGENTS.md`: matriz RACI, formato de comunicación común, regla de aprobación de
cambios que afectan arquitectura, seguridad, datos o costes, y prohibición explícita de inventar
resultados de pruebas o análisis.

**Escaladas que avalan el método:** la duplicación de la tabla de roles (hallazgo bloqueante B1 de la
revisión) se documentó en vez de resolverse en revisión, porque contradecía tres documentos aprobados;
el arquitecto la resolvió en `services.py` y el mixin de la interfaz pasó a consultarla.

## Cierre

Nueve agentes participaron. DevOps y rendimiento quedaron sin uso, de forma consciente y documentada.