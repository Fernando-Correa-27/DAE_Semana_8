# 10 · Git y commits

Volver al [[00-Indice]] · Anterior: [[09-Pruebas-y-resultados]] · Siguiente: [[11-Docker-y-CI]]

## Los commits de la entrega

| Hash | Mensaje | Qué aporta |
|---|---|---|
| `5bdd1fa` | (punto de partida) | El repositorio tal como llegó: API headless, `quizctl.py` con dos `TODO`, `permissions.py` con `return True`, `agent/` y las pruebas originales |
| `ca04610` | `docs: analisis inicial, equipo de agentes y diseno de la interfaz` | Análisis del estado real, definición del equipo de agentes, requisitos, trazabilidad, arquitectura y los tres ADR |
| `cf61a11` | `feat: implementar partes 2 y 3 del laboratorio` | **Parte 2**: `quizctl.exit_code_for` y `build_question_payload`. **Parte 3**: la regla de roles en el servidor |
| `7c87fd9` | `feat: desarrollar la interfaz de gestion de examenes` | Interfaz web completa: vistas, formularios, rutas, mixin de acceso, plantillas, CSS, y los ajustes de `settings.py` que hacen falta |
| `7992f2a` | `test: ampliar cobertura y corregir hallazgos de la revision` | Corrección de los hallazgos de `docs/revision-codigo.md` y siete módulos de prueba nuevos |
| `a82978e` | `fix: cerrar hallazgos criticos de seguridad y documentar la entrega` | Cierra SUI-01, SUI-02, SUI-04 y SUI-05 (configuración sin secretos en el código, arranque que falla cerrado, `seed_quiz --show-tokens`, `X-Frame-Options` + CSP en HTML) y añade `test_config_hardening.py` |

## Qué cambió en cada fase

### `5bdd1fa` → punto de partida

- 61 pruebas, **21 fallando** (18 errores en `test_quizctl`, 3 fallos en `test_permissions`).
- `test_api` y `test_agent` ya pasaban.
- Sin `docs/`, sin `AGENTS.md`, sin `opencode.json`, sin agentes definidos.

### `ca04610` — análisis y diseño

- Los 11 agentes definidos, con prioridad y matriz RACI.
- `docs/requisitos.md` y `docs/trazabilidad.md`: ~142 requisitos con criterio comprobable.
- `docs/arquitectura.md` y los ADR 0001, 0002 y 0003.
- **Sin tocar código de producción.**

### `cf61a11` — Partes 2 y 3

- Los dos `TODO(equipo)` de `quizctl.py` implementados.
- La regla de roles, con la tabla compartida en `quiz/services.py` y el adaptador `AgentPermission`.
- Las pruebas de `test_quizctl` y `test_permissions` dejan de fallar **sin editar sus aserciones**.

### `7c87fd9` — interfaz web

- `quiz/web_views.py`, `quiz/web_urls.py`, `quiz/web_mixins.py`, `quiz/forms.py`.
- `quiz/templates/quiz/` (plantillas y parciales) y `quiz/static/quiz/css/app.css`.
- `settings.py`: `sessions`, `messages`, `staticfiles`, `TEMPLATES`, `STATIC_URL`, `PAGE_SIZE` y las tres
  URL de login. **El bloque `REST_FRAMEWORK` queda intacto** y `quiz/views.py` no se toca: el contrato no
  se degrada.
- Módulos de prueba de la interfaz.

### `7992f2a` — revisión y cobertura

- Corregido el hallazgo bloqueante: la interfaz ya no reimplementa la tabla de roles, consulta
  `services.may_use()`.
- Corregidos el doble `role="alert"`, la opción correcta que se perdía tras un POST inválido, el orden de
  los últimos exámenes y la divergencia de paginación.
- Añadidos `test_services.py`, `test_http_matrix.py`, `test_http_client.py`, `test_persistence.py`,
  `test_query_counts.py`, `test_web_gaps.py` y `test_web_review.py`.
- **61 → 324 pruebas, todas en verde.**

### `a82978e` — cierre de los hallazgos críticos de seguridad

Mensaje: `fix: cerrar hallazgos criticos de seguridad y documentar la entrega`.

- `config/settings.py`: **fuera toda credencial del código**. Orden: `DJANGO_SECRET_KEY` del entorno → si
  no hay, se lee o se genera una clave aleatoria en `.secret_key` (ignorado por git) → con
  `DJANGO_DEBUG=0` y sin variable de entorno, arranque con `ImproperlyConfigured`.
- `DEBUG` pasa a depender de `DJANGO_DEBUG` (por defecto `"1"`, el laboratorio sigue igual) y
  `ALLOWED_HOSTS` de `DJANGO_ALLOWED_HOSTS` separada por comas, también con fallo cerrado.
- `X_FRAME_OPTIONS = "DENY"` y `XFrameOptionsMiddleware`, más una CSP
  `default-src 'self'; frame-ancestors 'none'` emitida **solo en respuestas HTML** por el nuevo
  `config/middleware.py`.
- El `<script>` inline de `quiz/templates/quiz/base.html` se mueve a
  `quiz/static/quiz/js/app.js`, para poder aplicar la CSP sin `unsafe-inline`.
- `seed_quiz`: los tokens **solo** se imprimen con `--show-tokens`; `--password` nunca imprime la
  contraseña.
- `.gitignore` añade `.secret_key`.
- Nuevo `quiz/tests/test_config_hardening.py` (15 pruebas).
- README y documentación actualizados con el estado real.
- **324 → 365 pruebas, todas en verde.**

### Lista final de commits de la entrega

`5bdd1fa` (previo) → `ca04610` → `cf61a11` → `7c87fd9` → `7992f2a` → `a82978e`.

## Higiene del repositorio

`.gitignore` excluye:

```
.venv/
__pycache__/
*.pyc
db.sqlite3
.env
agent_audit.jsonl
schema.yml
.secret_key
```

**Ningún token, contraseña ni clave está versionado.** Desde `a82978e`, `seed_quiz` tampoco los imprime
salvo que se pida con `--show-tokens`; la documentación solo menciona **nombres** de variables.

`requirements.txt` **intacto** con sus 4 líneas: ninguna dependencia añadida durante el trabajo.

## Pendiente de higiene

`Semana_8/` (esta bóveda) **no está en `.gitignore`**. Un `git add -A` la metería en el repositorio. Es
un hallazgo conocido (menor m20 de la revisión) que queda abierto para el coordinador:
ver [[12-Limitaciones-y-pendientes]].

## Convenciones

- Mensajes de commit en inglés, descriptivos del tipo de cambio.
- Código, nombres y comentarios en **inglés**; entregables y documentación en **español**.
- El **coordinador** hace los commits: los agentes no commitean.