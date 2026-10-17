# AGENTS.md — Equipo de agentes del proyecto

> Instrucciones de trabajo para los agentes especializados de opencode.
> Este archivo es la fuente de verdad de la colaboración; las definiciones viven en `.opencode/agent/`.
>
> **Convención del curso:** código, nombres y comentarios en **inglés**; explicaciones y entregables en **español**. PEP 8.

## 1. Contexto del proyecto (hechos comprobados)

- **Qué es:** API REST headless de cuestionarios (exámenes / preguntas / opciones). Laboratorio extra de la S08 de DAE. No tiene interfaz de usuario.
- **Stack:** Python + **Django 5.2–6.x** (`manage.py` fija `config.settings`), **Django REST Framework**, **drf-spectacular** (contrato OpenAPI en `/api/schema/` y `/api/docs/`), `requests`. Base de datos **SQLite** de desarrollo.
- **Autenticación:** token en la cabecera `Authorization` (`TokenAuthentication`); permisos por defecto `IsAuthenticated` + `quiz.permissions.AgentPermission`.
- **Apps/paquetes:** `config/` (settings, urls), `quiz/` (modelos, serializadores, vistas, rutas, permisos, comando `seed_quiz`, tests), `agent/` (pasarela cerrada modelo↔API + adaptador LLM opcional).
- **Estado:** repositorio con un único commit. `test_api` y `test_agent` pasan; `test_quizctl` y `test_permissions` **fallan** porque faltan dos entregables (ver §7). `agent_audit.jsonl`, `schema.yml`, `db.sqlite3` están ignorados por git.
- **No verificado:** no existe `Dockerfile`, CI ni entorno de despliegue; no hay `AGENTS.md`, `opencode.json` ni agentes previos (no había nada que conservar).

## 2. Equipo de agentes

| # | Agente (`nombre`) | Prioridad | Archivo |
|---|---|---|---|
| 1 | Analista de requisitos y producto | Imprescindible | `analista-requisitos` |
| 2 | Arquitecto de software | Imprescindible | `arquitecto` |
| 3 | Agente de seguridad | Imprescindible | `seguridad` |
| 4 | Desarrollador backend Django | Imprescindible | `backend-django` |
| 5 | Tester (QA) | Imprescindible | `tester` |
| 6 | Revisor de código | Imprescindible | `revisor-codigo` |
| 7 | Documentador | Imprescindible | `documentador` |
| 8 | Especialista en bases de datos | Recomendado | `especialista-bd` |
| 9 | Arquitecto de IA | Recomendado (hay IA en el alcance) | `arquitecto-ia` |
| 10 | DevOps e infraestructura | Opcional (laboratorio) | `devops` |
| 11 | Especialista en rendimiento | Opcional (laboratorio) | `rendimiento` |

**No incorporado:** *Especialista frontend/UX/UI* — el proyecto es **headless** (sin pantalla), por lo que no aporta valor. Si en el futuro se añade una SPA, se evaluará su inclusión.

### Justificación breve
- **Imprescindibles:** cubren el ciclo completo (requisitos → diseño → seguridad → implementación → pruebas → revisión → documentación) y corresponden a los entregables `TODO(team)` reales del repositorio.
- **Recomendados:** el contrato/DI históricamente tiene riesgo de N+1 (base de datos, ya con buenas prácticas presentes) y una frontera de IA con riesgo de prompt injection (arquitecto de IA, ya implementada y a proteger).
- **Opcionales:** no hay CI, Docker ni SLA de rendimiento en un laboratorio local; se activan solo si el alcance crece.

## 3. Matriz de responsabilidades (RACI)

`E` = ejecuta · `R` = revisa · `A` = aprueba · `C` = consultado · `I` = informado.

| Tipo de tarea | Requisitos | Arquitecto | Seguridad | Backend | BD | Tester | Revisor | Documentador | IA | DevOps |
|---|---|---|---|---|---|---|---|---|---|---|
| Definir historias/criterios | **E/A** | C | I | I | | | | I | | |
| Decisiones de arquitectura (ADR) | C | **E/A** | C | C | C | I | R | I | C | C |
| Reglas de permisos/seguridad | I | C | **A** | E | | R | R | I | C | I |
| Implementar el cliente `quizctl.py` | C | C | I | **E** | | R | R | I | | |
| Diseño de esquema / migraciones | | C | C | C | **E/A** | I | R | I | | I |
| Frontera del agente de IA | | C | R | E | | R | R | I | **A** | |
| Pruebas unitarias/integración | R | I | C | C | C | **E/A** | R | I | C | I |
| Pruebas de seguridad | I | C | **E/A** | C | | C | R | I | C | C |
| Revisión de código (PR) | I | C | C | E | C | C | **E/A** | I | C | C |
| Documentación / README / diagramas | C | C | I | I | I | I | I | **E/A** | I | I |
| Rendimiento (si aplica) | I | C | I | C | **E** | C | R | I | | C |
| CI/CD y secretos | I | C | C | C | | C | C | I | | **E/A** |

**Regla de aprobación:** todo cambio que afecte arquitectura, seguridad, datos o costes **escala** al owner de la fila (`A`) antes de integrarse. Ante empate, decide el **Arquitecto** y, en seguridad, el **Agente de seguridad** puede vetar.

## 4. Flujo de colaboración

1. **Análisis inicial** — `analista-requisitos` + `arquitecto` (+ agentes pertinentes) inspeccionan el estado real. Se parte de hechos comprobados.
2. **Planificación** — `arquitecto` fija la solución, sus límites y dependencias (ADR si aplica).
3. **Diseño especializado** — `seguridad`, `especialista-bd`, `arquitecto-ia`, `devops`, `rendimiento` revisan solo lo suyo.
4. **Implementación** — `backend-django` ejecuta según el diseño aprobado.
5. **Validación** — `tester` verifica requisitos; `seguridad` revisa riesgos relevantes.
6. **Revisión** — `revisor-codigo` comprueba calidad y estándares.
7. **Documentación** — `documentador` actualiza registros, instrucciones y diagramas afectados.
8. **Cierre** — pruebas en verde, sin hallazgos críticos abiertos, criterios de aceptación cumplidos.

No todos los agentes intervienen en todas las tareas: se asignan según complejidad y riesgo.

### Resolución de conflictos
- Datos insuficientes → se escala como **pregunta pendiente** al usuario, no se inventa.
- Desacuerdo técnico → `arquitecto` decide y queda registrado en ADR.
- Desacuerdo de seguridad → prevalece `seguridad` (puede bloquear) hasta revisión del usuario.
- Solapamiento → quien tiene `E` en la matriz ejecuta; el otro pasa a `R`/`C`.

## 5. Formato de comunicación común

Cada agente reporta con este bloque (adaptado a su rol):

```
Rol: <agente>
Tarea: <qué se pidió>
Estado: completado | pendiente | bloqueado | no verificado
Hallazgos: <hechos con evidencia archivo:línea>
Decisiones/Riesgos: <qué y por qué>
Siguiente: <a quién pasa la tarea>
```

- Distinguir siempre **hecho comprobado / hipótesis / pregunta pendiente**.
- **Nunca** reportar secretos, tokens ni datos sensibles.
- **Nunca** afirmar que se ejecutó una prueba o despliegue sin evidencia.

## 6. Reglas de colaboración (obligatorias)

1. Responsabilidades delimitadas (matriz §3) para evitar conflictos y duplicación.
2. Compartir hallazgos, dependencias, decisiones y riesgos (§5).
3. Respetar las decisiones arquitectónicas aprobadas; proponer cambios formalmente (ADR).
4. No modificar archivos ajenos a la tarea sin justificación clara.
5. No sobrescribir cambios de otros ni tocar el mismo componente en paralelo sin coordinar.
6. No inventar resultados de pruebas, verificaciones, análisis ni despliegues.
7. Diferenciar tareas completadas / pendientes / bloqueadas / no verificadas.
8. Escalar cambios relevantes de arquitectura, seguridad, datos o costes.
9. Priorizar simplicidad, mantenibilidad, seguridad y claridad.
10. No introducir dependencias ni servicios externos sin evaluar necesidad e implicaciones.

## 7. Estándares técnicos y de calidad

- **Estilo:** PEP 8; nombres y comentarios en inglés. Sin comentarios innecesarios.
- **Capas:** modelos (datos), serializadores (validación), vistas (presentación/API), `agent/` (integración externa aislada). Mantener la separación.
- **Configuración/secretos:** vía variables de entorno (`DJANGO_SECRET_KEY`); nunca en el código ni en docs. `.env`, `db.sqlite3` y artefactos ya están ignorados por git.
- **Migraciones:** controladas y revisadas (`especialista-bd`); reversibles y no destructivas sin advertencia.
- **Pruebas:** obligatorias para permisos, API, cliente `quizctl` y frontera del agente. Runner: `python manage.py test`; `pytest`/`pytest-django` solo si el equipo los adopta.
- **Errores/observabilidad:** sin filtrar información sensible; el cliente `quizctl` comunica por código de salida y `--json` estable.
- **Dependencias:** justificadas, actualizadas y con riesgos evaluados.
- **Compatibilidad:** respetar la versión de Python/Django del repo; no añadir dependencias no declaradas en `requirements.txt`.
- **No imponer** herramientas o patrones por defecto sin comprobar su idoneidad.

### Estrategia de pruebas
1. Priorizar los cuatro entregables verificables: `test_permissions`, `test_quizctl`, `test_api`, `test_agent`.
2. Cubrir reglas de negocio (mínimo 2 opciones, exactamente 1 correcta), permisos por rol/método, códigos de salida y frontera R0/R1/R2.
3. Añadir casos borde y de regresión antes de cerrar cada cambio.

### Estrategia de seguridad
Revisión de auth/autorización, permisos por objeto, secretos, validación de entrada, dependencias y config. de producción; pruebas de seguridad para permisos y para la frontera del agente (prompt injection, aprobación humana).

## 8. Plan de implementación inicial (adaptado al repositorio)

1. **Requisitos y aceptación** (`analista-requisitos`): historias y criterios para las Partes 2, 3 y 4.
2. **Diseño** (`arquitecto` + `seguridad` + `especialista-bd`): reglas de permisos, formato del payload de pregunta, códigos de salida, y confirmación de que no hace falta cambiar la arquitectura.
3. **Implementación** (`backend-django`):
   - `quizctl.exit_code_for` y `quizctl.build_question_payload` (Parte 2).
   - `quiz.permissions.AgentPermission` (Parte 3).
4. **Pruebas** (`tester`): `python manage.py test` en verde.
5. **Revisión** (`revisor-codigo`) y **seguridad** (permisos y frontera del agente).
6. **Documentación** (`documentador`): README y ADR si hubo decisiones.
7. **Cierre:** verificación de los cuatro entregables y criterios de aceptación.

## 9. Riesgos, dependencias y preguntas pendientes

**Riesgos**
- R1. `SECRET_KEY` con fallback y `DEBUG=True`: inviable en producción (seguridad).
- R2. Permisos sin implementar: cualquier token autenticado puede borrar (Parte 3).
- R3. Frontera del agente: riesgo de prompt injection si se relaja la validación (arquitecto-ia/seguridad).
- R4. Base de datos SQLite: conclusiones de rendimiento/escala orientativas.
- R5. Sin CI: la calidad depende de ejecución manual de las pruebas.

**Dependencias**
- Python/Django del entorno; `re`/`requests` para cliente; `drf-spectacular` para el contrato; servidor vivo en `127.0.0.1:8000` para pruebas de integración.

**Preguntas pendientes (al usuario)**
- ¿Se adopta `pytest`/`pytest-django` o se mantiene `manage.py test`?
- ¿Se desea CI/Docker (activa DevOps) o se mantiene el alcance de laboratorio?
- ¿Se asignan modelos concretos por agente o heredan el modelo por defecto?
- ¿Hay una rúbrica/guía oficial en el campus que deba cargarse como requisito?

## 10. Organización de archivos

```
AGENTS.md                  # este protocolo (instrucciones auto-cargadas por opencode)
opencode.json              # $schema + instructions
.opencode/agent/*.md       # definiciones de los agentes especializados
docs/                      # (propuesto) requisitos.md · adr/ · changelog.md
quiz/ agent/ config/       # código del proyecto (NO modificar sin pasar por el flujo)
```
