# API headless de cuestionarios + interfaz de gestión — S08 (DAE)

Laboratorio de la **semana 8** de Desarrollo de Aplicaciones Empresariales. El repositorio expone un
dominio de **exámenes, preguntas y opciones** (Django + Django REST Framework) de **dos maneras**:

1. Una **API REST headless** que se describe a sí misma con un contrato OpenAPI, la consume un
   **cliente de consola** (`quizctl.py`) y, detrás de una frontera cerrada, un **agente de IA**.
2. Una **interfaz web de gestión** (plantillas de Django, en español, sin JavaScript obligatorio) para
   que el profesorado pueda listar, buscar, crear, editar y borrar contenido sin usar la API a mano.

Las dos son **dos presentaciones del mismo dominio**: la invariante de negocio y la tabla de roles
viven **una sola vez**, en `quiz/services.py`, y ninguna de las dos se llama a la otra.

> ⚠️ **Esto es configuración de laboratorio, no de producción.** Arranca con `DEBUG = True` y con un
> `SECRET_KEY` de reserva en el código. Está pensado para `runserver` en `127.0.0.1`. Ver
> [Configuración](#configuración).

---

## Qué hay aquí: las cuatro partes del laboratorio

| Parte | Qué es | Dónde vive | Estado |
|---|---|---|---|
| **1 · El contrato** | La API se documenta a sí misma: esquema OpenAPI en `/api/schema/` y Swagger UI en `/api/docs/` | `config/urls.py`, `drf-spectacular` | Hecho |
| **2 · El cliente de consola** | `quizctl.py`: un cliente sin pantalla que traduce el estado HTTP a **códigos de salida** y construye el cuerpo de una pregunta | `quizctl.py` | Hecho |
| **3 · Identidades y permisos** | Dos capas en el servidor: hay que ser alguien (`IsAuthenticated`) y el **rol** decide qué puede hacer. El agente **nunca** borra | `quiz/permissions.py`, `quiz/services.py` | Hecho |
| **4 · La frontera del agente** | `agent/`: pasarela **cerrada** entre un modelo de IA y la API. R0 ejecuta, R1 ejecuta, R2 (**destructivo**) exige **aprobación humana** y deja rastro | `agent/gateway.py` | Hecho |
| **+ · Interfaz gráfica** | Servidor-rendered, sin CDN, sin emojis, accesible por teclado, con paginación, búsqueda y filtros | `quiz/web_*.py`, `quiz/templates/`, `quiz/static/` | Hecho |

Las decisiones de arquitectura que sostienen la interfaz están en [`docs/adr/`](docs/adr/) y el detalle
técnico en [`docs/arquitectura.md`](docs/arquitectura.md).

---

## Requisitos

- **Python 3.14.4** (probado en esa versión).
- Las cuatro dependencias de `requirements.txt`: Django 5.2.18, djangorestframework 3.18.3,
  drf-spectacular 0.30.0, requests 2.34.2.
- **No hay** JavaScript, ni bundler, ni `node_modules`, ni base de datos externa: SQLite viene con
  Python.

## Instalación

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux / macOS

pip install -r requirements.txt
```

## Puesta en marcha

```bash
python manage.py migrate
python manage.py seed_quiz --password "TU_CLAVE"
python manage.py runserver
```

- `migrate` crea las tablas (`quiz/migrations/0001_initial.py`).
- `seed_quiz` carga los datos fijos del laboratorio y crea los usuarios **`profe`** (persona,
  `is_staff=True`) y **`agente`** (grupo `agente`). **Imprime los dos tokens por terminal**: cópialos
  de ahí; nunca están en el repositorio.
- `--password` es **necesario para entrar en la interfaz web**: sin la opción, `profe` nace con
  `set_unusable_password()` (porque la API no usa contraseñas) y no hay nadie que pueda iniciar
  sesión en el navegador. Si ya existe y quieres otra clave:
  `python manage.py changepassword profe`.
- `seed_quiz` es **idempotente respecto a los tokens**: al repetirlo no cambian, así que las
  variables de entorno siguen valiendo. Ojo: sí **borra y recarga** exámenes, preguntas y opciones.

El servidor queda en `http://127.0.0.1:8000`.

### Variables de entorno

Se nombran; los valores no se documentan aquí.

| Variable | Para qué |
|---|---|
| `QUIZ_URL` | Base de la API que llama `quizctl.py` y `agent/`. Por defecto `http://127.0.0.1:8000`. |
| `QUIZ_TOKEN_HUMANO` | Token de **la persona** (`profe`). Es el único que puede borrar y el que aprueba los planes R2 del agente. |
| `QUIZ_TOKEN_AGENTE` | Token del **agente**. Lee, crea y modifica; nunca borra. |
| `QUIZ_TOKEN` | Token con el que llama `quizctl.py`. Se asigna al que corresponda en cada prueba. |
| `DJANGO_SECRET_KEY` | Clave de Django. Sin ella arranca con un valor de reserva **solo válido en el aula**. |
| `LLM_URL` | Endpoint del modelo local para `agent/llm.py`. Si no está, el adaptador no se usa. |
| `LLM_MODEL` | Nombre del modelo que se pide a `LLM_URL`. |

En PowerShell (otra terminal, con el servidor ya arrancado):

```powershell
$env:QUIZ_URL = "http://127.0.0.1:8000"
$env:QUIZ_TOKEN_HUMANO = "<lo que imprimió seed_quiz>"
$env:QUIZ_TOKEN_AGENTE = "<lo que imprimió seed_quiz>"
$env:QUIZ_TOKEN = $env:QUIZ_TOKEN_HUMANO
```

---

## Parte 1 — El contrato

```bash
python manage.py spectacular --file schema.yml     # regenera el esquema (schema.yml está ignorado por git)
```

En el navegador: `http://127.0.0.1:8000/api/docs/`. Ambos endpoints responden **sin token**
(verificado en vivo), porque `quizctl ops` y `agent/gateway.py` los leen sin credencial.

## Parte 2 — El cliente de consola

```bash
python quizctl.py exams list
python quizctl.py questions list --exam 1 --search orm --json
python quizctl.py questions create --exam 1 --text "¿Qué es REST?" --choice "Un estilo:ok" --choice "Un lenguaje"
python quizctl.py questions create --exam 1 --text "..." --choice "a:ok" --choice "b" --dry-run
python quizctl.py questions delete 7
python quizctl.py ops                               # operaciones que declara el contrato
```

Solo el `:ok` **final** de una opción la marca como correcta (`"Verdad: sí:ok"` → texto `Verdad: sí`).
El cliente **no duplica** la validación del servidor: si mandas dos `:ok`, el 400 llega del servidor.

| Código | Significa |
|---|---|
| 0 | funcionó |
| 1 | otro error o mal uso (p. ej. falta `QUIZ_TOKEN`) |
| 2 | validación (HTTP 400) |
| 3 | no permitido (HTTP 401 o 403) |
| 4 | no existe (HTTP 404) |
| 5 | error del servidor (5xx) |
| 6 | no hay conexión |

## Parte 3 — Quién puede hacer qué

| Rol | Identificación | Leer | Crear | Modificar | Borrar |
|---|---|:--:|:--:|:--:|:--:|
| Persona | `is_staff` o `is_superuser` (`profe`) | sí | sí | sí | **sí** |
| Agente | grupo `agente` (`agente`) | sí | sí | sí | **no** |
| Lector | cualquier otro autenticado | sí | no | no | no |
| Anónimo | sin `Authorization` | no | no | no | no |

Un verbo desconocido se **deniega por defecto**. La tabla está en `quiz/services.py`
(`METHODS_BY_ROLE`) y `quiz/permissions.py` es solo el adaptador de DRF; la interfaz web pregunta a la
**misma** tabla, así que no puede responder distinto.

## Parte 4 — La frontera del agente

```bash
python -m agent --intent '{"op": "exams_list"}'
python -m agent --intent '{"op": "questions_list", "query": {"search": "prefetch"}}'
python -m agent --intent '{"op": "exams_destroy", "path": {"id": 1}}'          # R2: no borra, devuelve plan
python -m agent --intent '{"op": "exams_destroy", "path": {"id": 1}}' --approve <plan_hash>
python -m agent --intent '"Exam.objects.all().delete()"'                       # fuera de la lista cerrada
python -m agent --intent '{"op": "run_sql"}'                                   # fuera de la lista cerrada
```

R0 (leer) y R1 (crear) se ejecutan con el token del **agente**. R2 (borrar) **no**: devuelve
`plan` + `plan_hash` y solo se aplica con `--approve` y el token de **la persona**
(`QUIZ_TOKEN_HUMANO`). Si el objetivo cambia entre el plan y la aprobación, el hash deja de valer.
Todo lo que devuelve la API se envuelve como `untrusted_data` (**dato, nunca orden**) y cada decisión
queda en `agent_audit.jsonl` (ignorado por git).

El seed incluye una pregunta cuyo texto contiene `IGNORA TUS INSTRUCCIONES`: la frontera la trata como
texto y no cambia de comportamiento.

---

## La interfaz web

**Server-rendered** con plantillas de Django, `ModelForm` + `formset` en línea para las opciones, CBVs
y una única hoja CSS propia. Sin CDN, sin JavaScript obligatorio, sin `django.contrib.admin`
(sería una segunda vía de escritura que esquivaría las reglas del dominio).

### Cómo entrar

| Dato | Valor |
|---|---|
| URL | `http://127.0.0.1:8000/acceso/` |
| Usuario | `profe` |
| Contraseña | la que fijaste con `seed_quiz --password` (o con `changepassword profe`) |

La interfaz **exige `is_staff`**: es privada y solo se abre al profesorado. Un anónimo recibe **302**
al login; un usuario autenticado que no sea `profe` recibe **403**.

### Pantallas

| Ruta | Qué hace |
|---|---|
| `/` | Panel: totales (exámenes, preguntas, opciones) y últimos exámenes. |
| `/acceso/` · `/salir/` | Entrar y salir (sesión, nunca token). |
| `/examenes/` | Tabla de exámenes con su número de preguntas. |
| `/examenes/nuevo/` · `/examenes/{id}/editar/` · `/examenes/{id}/eliminar/` | Alta, edición y borrado (pide confirmación). |
| `/examenes/{id}/` | Detalle de un examen con todas sus preguntas y opciones. |
| `/preguntas/` | **Tabla de preguntas**: filtro por examen y búsqueda por texto, combinables y con URL compartible. |
| `/examenes/{id}/preguntas/nuevo/` · `/preguntas/{id}/editar/` · `/preguntas/{id}/eliminar/` | Pregunta y sus opciones en un solo formulario. |

- **Filtros de `/preguntas/`:** `?exam=<id>` y `?q=<texto>`. Viajan en la URL, así que la vista se
  puede compartir y «Anterior/Siguiente» los conserva. Un `exam` que no es un id da 404.
- **Paginación:** 5 por página, **el mismo número que la API** (`settings.PAGE_SIZE`).
- **Errores:** si una pregunta tiene menos de 2 opciones o no tiene exactamente 1 correcta, el
  formulario vuelve a la misma pantalla **con el error y sin perder lo escrito**.
- **Frontera de confianza:** la sesión **no** abre la API y el token **no** abre la interfaz.

---

## Tabla de la API

Prefijo `/api/`. Autenticación: cabecera `Authorization: Token <clave>`. Respuestas paginadas con
`{count, next, previous, results}` y 5 elementos por página.

### Exámenes

| Recurso | Endpoint | Método | Descripción | Parámetros | Cuerpo JSON de ejemplo | Respuesta esperada | HTTP |
|---|---|---|---|---|---|---|---|
| `exams_list` | `/api/exams/` | GET | Lista paginada de exámenes, cada uno con su número de preguntas | `?page=<n>` | — | `{count, next, previous, results:[{id, title, created_at, question_count}]}` | 200 |
| `exams_create` | `/api/exams/` | POST | Crea un examen | — | `{"title": "Modelado de datos"}` | `{"id": 3, "title": "Modelado de datos", "created_at": "..."}` | 201 |
| `exams_retrieve` | `/api/exams/{id}/` | GET | Detalle de un examen | — | — | `{"id": 1, "title": "...", "created_at": "...", "question_count": 4}` | 200 |
| `exams_update` | `/api/exams/{id}/` | PUT / PATCH | Reemplaza o modifica parcialmente el examen | — | `{"title": "Nuevo título"}` | Objeto actualizado | 200 |
| `exams_destroy` | `/api/exams/{id}/` | DELETE | Borra el examen **y, en cascada, sus preguntas y opciones**. Solo la persona | — | — | Sin cuerpo | 204 |

### Preguntas

Las opciones viajan **anidadas** (`choices`) y el examen viaja como **identificador** (`exam`).

| Recurso | Endpoint | Método | Descripción | Parámetros | Cuerpo JSON de ejemplo | Respuesta esperada | HTTP |
|---|---|---|---|---|---|---|---|
| `questions_list` | `/api/questions/` | GET | Lista paginada de preguntas con sus opciones | `?exam=<id>`, `?search=<texto>`, `?page=<n>` | — | `{count, next, previous, results:[{id, exam, text, choices:[...], created_at}]}` | 200 |
| `questions_create` | `/api/questions/` | POST | Crea una pregunta con sus opciones, todo atómico | — | `{"exam": 1, "text": "¿Qué es REST?", "choices": [{"text": "Un estilo de arquitectura", "is_correct": true}, {"text": "Un lenguaje de programación", "is_correct": false}]}` | Pregunta creada con los `id` de sus opciones | 201 |
| `questions_retrieve` | `/api/questions/{id}/` | GET | Detalle de una pregunta | — | — | `{"id": 1, "exam": 1, "text": "...", "choices": [{"id": 1, "text": "...", "is_correct": true}], "created_at": "..."}` | 200 |
| `questions_update` | `/api/questions/{id}/` | PUT | Sustitución completa (faltan campos obligatorios → 400) | — | `{"exam": 1, "text": "...", "choices": [...]}` | Objeto actualizado | 200 |
| `questions_partial_update` | `/api/questions/{id}/` | PATCH | Modifica solo lo enviado. Sin `choices`, **las opciones no se tocan**; con `choices`, **las reemplazan** | — | `{"text": "Nuevo enunciado"}` | Objeto actualizado | 200 |
| `questions_destroy` | `/api/questions/{id}/` | DELETE | Borra la pregunta. Solo la persona | — | — | Sin cuerpo | 204 |

### Contrato y documentación

| Endpoint | Método | Descripción | HTTP |
|---|---|---|---|
| `/api/schema/` | GET | Esquema OpenAPI 3 en JSON o YAML. **Sin token** | 200 |
| `/api/docs/` | GET | Swagger UI. **Sin token** | 200 |
| `/api/` | GET | Raíz del router: índice de recursos | 200 |

### Reglas de validación (400)

Una pregunta se rechaza, y **no se persiste nada**, cuando: tiene menos de 2 opciones, tiene 0
opciones correctas o tiene más de una, falta un campo obligatorio (`exam`, `text`, `choices`, `title`),
un campo viene con tipo incorrecto, el `exam` no existe, o `?exam=` no es un identificador válido.

### Códigos de error

| Código | Causa |
|---|---|
| **400** | Validación: regla del dominio rota, campo obligatorio ausente, tipo incorrecto, `exam` inexistente, `?exam=` no entero. El cuerpo nombra el campo. |
| **401** | Sin cabecera `Authorization` o con un token inválido. |
| **403** | Autenticado pero sin permiso: el agente o el lector intentan escribir o borrar; verbo desconocido. |
| **404** | El recurso no existe, o `?page=` apunta a una página fuera de rango. |
| **405** | El método HTTP no está implementado en esa ruta. |
| **500** | Fallo interno del servidor. Con `DEBUG = True` la página técnica de Django muestra detalles internos: razón de más para no usar esto fuera del aula. |

### Permisos por operación

| Operación | Lector | Agente | Persona |
|---|:--:|:--:|:--:|
| GET (listar, detalle) | 200 | 200 | 200 |
| POST / PUT / PATCH | 403 | 201 / 200 | 201 / 200 |
| DELETE | 403 | **403** | 204 |
| Sin token | 401 | 401 | 401 |

---

## Pruebas

```bash
python manage.py test
```

**Resultado real de la última ejecución: `Ran 324 tests ... OK`.**

| Módulo | Qué cubre |
|---|---|
| `quiz/tests/test_api.py` | El contrato del laboratorio (entregado, sin tocar): serializadores, paginación, filtros, sincronía con la pasarela. |
| `quiz/tests/test_agent.py` | Frontera R0/R1/R2, allowlist, aprobación humana, auditoría, adaptador de modelo. |
| `quiz/tests/test_quizctl.py` | Códigos de salida, construcción del cuerpo de pregunta y el cliente contra un servidor vivo. |
| `quiz/tests/test_permissions.py` | La matriz de roles de la Parte 3. |
| `quiz/tests/test_services.py` | La invariante **una sola vez**: serializer y formset dan el mismo veredicto; resolución de verbos y denegación por defecto. |
| `quiz/tests/test_http_matrix.py` | Matriz de códigos por endpoint, método y rol; raíz del navegador de DRF; frontera sesión/token. |
| `quiz/tests/test_http_client.py` | El cliente y la pasarela hablando con un servidor real. |
| `quiz/tests/test_persistence.py` | Que un 400 no persiste nada, atomicidad del servicio y borrado en cascada. |
| `quiz/tests/test_query_counts.py` | Número de consultas de API e interfaz (protege contra N+1). |
| `quiz/tests/test_web.py` | Login/logout, CRUD por HTTP, 302 del anónimo, 403 por rol, CSRF, activos. |
| `quiz/tests/test_web_review.py` | Anuncio único del error, opción correcta conservada tras un POST inválido, últimos exámenes, listado de preguntas, una sola página. |
| `quiz/tests/test_web_gaps.py` | Objetos inexistentes, paginación, verbos, sesión, límites de campo, no-staff, contenido del detalle. |

Runner: `python manage.py test` (el repositorio no adopta `pytest`).

## Estructura

| Ruta | Para qué |
|---|---|
| `config/` | `settings.py` (una sola constante `PAGE_SIZE` para API e interfaz) y `urls.py`. |
| `quiz/models.py` | `Exam`, `Question`, `Choice`. |
| `quiz/services.py` | **Reglas de negocio y tabla de roles**, escritas una sola vez. |
| `quiz/queries.py` | Lecturas del dominio, sin N+1. |
| `quiz/serializers.py`, `quiz/views.py`, `quiz/urls.py` | La API: serializadores (que delegan en `services`), vistas y rutas. |
| `quiz/permissions.py` | `AgentPermission`: el adaptador de DRF a la tabla de roles. |
| `quiz/forms.py`, `quiz/web_views.py`, `quiz/web_urls.py`, `quiz/web_mixins.py` | La interfaz web. |
| `quiz/templates/`, `quiz/static/` | Plantillas, parciales y la hoja CSS propia. |
| `quiz/management/commands/seed_quiz.py` | Datos de arranque y usuarios con token. |
| `agent/` | Frontera cerrada del agente de IA y adaptador opcional a un modelo local. |
| `quizctl.py` | Cliente de consola. |
| `docs/` | Requisitos, arquitectura, ADRs, seguridad, revisión, trazabilidad. |
| `Semana_8/` | Bitácora del equipo en formato Obsidian. |

## Configuración

| Ajuste | Valor en el repositorio | Comentario |
|---|---|---|
| Base de datos | SQLite (`db.sqlite3`) | Sin servidor. `db.sqlite3` está ignorado por git. |
| `DEBUG` | `True` | **Solo laboratorio.** Con `DEBUG=True` un 500 muestra la página técnica de Django. |
| `SECRET_KEY` | Reserva `dev-only-not-a-secret` en `config/settings.py:9` | **Solo laboratorio.** Fuera del aula, `DJANGO_SECRET_KEY` es obligatoria. Con la interfaz por sesión, filtrarla permite falsificar cookies. |
| Autenticación | API por token; interfaz por cookie de sesión. **Nunca se mezclan.** | CSRF obligatorio solo en la interfaz. |
| Paginación | `PAGE_SIZE = 5` | Compartida por la API y la interfaz. |

Lo que **no** tiene el proyecto y es deliberado: Docker, CI/CD, despliegue, throttling y
`django.contrib.admin`. La justificación está en [`docs/decisiones-docker-ci.md`](docs/decisiones-docker-ci.md).

## Decisiones

Las decisiones de arquitectura están registradas como ADR en [`docs/adr/`](docs/adr/):

| ADR | Decisión |
|---|---|
| [0001 · Arquitectura de la interfaz web](docs/adr/0001-arquitectura-de-la-interfaz-web.md) | Server-rendered, sin CDN, sin JavaScript obligatorio, sin `admin`. |
| [0002 · Consumo del dominio desde la interfaz](docs/adr/0002-consumicion-del-dominio-desde-la-interfaz.md) | La interfaz usa el ORM a través de `quiz/services.py`; **nunca** habla HTTP con su propia API. Una sola redacción de la invariante. |
| [0003 · Una sola regla de permisos](docs/adr/0003-regla-de-permisos.md) | Una tabla de acciones, dos adaptadores finos (DRF y Django). Deny by default. |

Detalle: [`docs/arquitectura.md`](docs/arquitectura.md). Requisitos y trazabilidad:
[`docs/requisitos.md`](docs/requisitos.md) y [`docs/trazabilidad.md`](docs/trazabilidad.md). Bitácora del
equipo: [`Semana_8/00-Indice.md`](Semana_8/00-Indice.md).

## Convenciones del curso

Código, nombres y comentarios en **inglés**; explicaciones y entregables en **español**. PEP 8.
Ningún token, contraseña ni clave en el repositorio: solo nombres de variables.