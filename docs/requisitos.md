# Requisitos y criterios de aceptación — API headless de cuestionarios (S08 · lab extra)

> **Autor:** Analista de requisitos y producto
> **Fecha:** 2026-10-16 · **Fase:** A/B (solo análisis y documentación; **no** se ha tocado código de producción)
> **Alcance de este documento:** requisitos verificables del laboratorio (API + cliente + frontera del agente) y,
> en una sección aparte y claramente marcada, las **mejoras de interfaz gráfica** que la misión menciona pero que
> **hoy no existen en el repositorio**.

---

## 1. Propósito y alcance

El proyecto expone una API REST headless de cuestionarios (exámenes, preguntas, opciones) construida con
Django + DRF, consumida de tres formas sin pantalla: el **contrato OpenAPI**, el **cliente de consola `quizctl.py`**
y la **pasarela cerrada del agente de IA** (`agent/`).

Este documento:

1. describe actores y casos de uso;
2. descompone los 4 criterios de la rúbrica en requisitos concretos con criterio de aceptación comprobable;
3. separa lo que es **obligatorio de la API** de lo que es **mejora adicional de interfaz (UI)**;
4. prioriza, y lista dependencias, ambigüedades y riesgos.

**Fuera de alcance (explícitamente):** despliegueproductive, CI/CD, contenedores, escalabilidad real sobre SQLite
y cualquier cliente móvil. No hay en el repositorio evidencia de que formen parte del laboratorio.

---

## 2. Fuentes de evidencia (hecho comprobado)

Todo requisito de este documento se apoya en una de estas fuentes. Citas en formato `archivo:línea`.

| # | Fuente | Qué acredita |
|---|---|---|
| F1 | `README.md:33-105` | Las 4 partes oficiales del laboratorio (contrato, cliente, permisos, frontera del agente) |
| F2 | `README.md:63-71` | Tabla de códigos de salida de `quizctl` (0–6) |
| F3 | `quiz/serializers.py:7-52` | Serializadores, `validate_choices`, `create`/`update` atómicos |
| F4 | `quiz/views.py:9-31` | Vistas, anotación `question_count`, `SearchFilter`, filtro manual `?exam=` |
| F5 | `quiz/urls.py:5-9`, `config/urls.py:4-9` | Rutas `/api/exams/`, `/api/questions/`, `/api/schema/`, `/api/docs/` |
| F6 | `config/settings.py:13-62` | Apps, middleware, paginación, permisos por defecto, SPECTACULAR |
| F7 | `quiz/permissions.py:9-20` | Regla de roles **declarada** y `return True` **pendiente** |
| F8 | `quizctl.py:31-64` | Tabla de códigos de salida y las 2 funciones `TODO` |
| F9 | `agent/gateway.py:32-43` | Lista cerrada `ALLOWED`, riesgos R0/R1/R2, parámetros admitidos |
| F10 | `quiz/seed_data.py:7-10` | Texto hostil `IGNORA TUS INSTRUCCIONES` en la pregunta 3 |
| F11 | `quiz/tests/*` | Pruebas existentes (ver `docs/trazabilidad.md`) |
| F12 | `requirements.txt`, `.gitignore`, `opencode.json`, `AGENTS.md` | Dependencias, higiene del repo, protocolo del equipo |
| F13 | Proyecto de referencia S07 (**solo lectura**): `blog/views.py`, `blog/templates/…`, `config/settings.py` | Patrón de UI del curso: CBV, plantillas, `ModelForm`, admin, sesiones/messages/CSRF, `STATICFILES_DIRS`, tests por app |
| F14 | Enunciado de la misión entregado por el usuario | Los 4 criterios de rúbrica (5 pts c/u) y la petición de UI gráfica |

### 2.1 Etiquetaje (se usa en todas las tablas)

- **HECHO** — verificado leyendo el código de este documento con cita `archivo:línea`.
- **HIPÓTESIS** — deducido del comportamiento estándar de Django/DRF; **requiere una prueba que lo confirme**.
- **PENDIENTE** — no hay evidencia en el repositorio; necesita decisión del usuario o del arquitecto.

### 2.2 Aviso sobre la rúbrica

`README.md:8` declara que *«la guía del laboratorio (con su rúbrica) está en el campus virtual; aquí está el código»*.
**El documento oficial de rúbrica NO está en el repositorio.** Los 4 criterios y su ponderación (5 pts c/u) que
desglosa este documento proceden del **enunciado de la misión (F14)**, no de un documento oficial leído.
No se inventa ningún otro requisito "de campus". Si el campus publica un texto distinto, esta matriz debe
reconciliarse con él → **pregunta abierta Q-01**.

---

## 3. Actores y casos de uso

### 3.1 Actores

| Actor | Identificación técnica (HECHO) | Puede hacer (HECHO, F7) |
|---|---|---|
| **Persona / `profe`** | `User` con `is_staff=True`, token en `Authorization: Token <key>` (`quiz/management/commands/seed_quiz.py:15-18`) | **Todo**: listar, crear, modificar, **borrar** exámenes, preguntas y opciones |
| **Agente / `agente`** | `User` en el grupo `agente` (`quiz/permissions.py:3`, `seed_quiz.py:14,19-23`) | Listar, crear y **modificar**; **nunca borrar** |
| **Lector / cualquier otro autenticado** | `User` autenticado sin rol (fixture `lector`, `quiz/tests/helpers.py:17-20`) | **Solo leer** (lectura es 200; escritura es 403) |
| **Visitante anónimo** | Sin cabecera `Authorization` | **Nada**: 401 |
| **Modelo de IA** | No es un usuario de Django: emite *intents* JSON a `agent/gateway.py` | Solo operaciones de `ALLOWED`, con R0→ejecuta, R1→ejecuta, R2→**plan + aprobación humana** |
| **Consumidor del contrato** | Cualquier programa que lea `/api/schema/` | Descubrir operaciones; no es identidad |

**Nota sobre el contrato (⚠ PENDIENTE de verificación):** `agent/gateway.py:52` lee `/api/schema/` **sin
credenciales** (no envía cabecera `Authorization`), y `quizctl ops` tampoco. Por tanto **el esquema debe poder
leerse sin token o la pasarela y `ops` se rompen**. Mi hipótesis inicial era que `SpectacularAPIView` queda fuera
del alcance de `DEFAULT_PERMISSION_CLASSES`; el arquitecto la marca como **sin verificar**
(`docs/arquitectura.md:301-312`). Hasta que se compruebe con el comando que allí se indica, este documento asume
**contrato público** y lo trata como requisito a confirmar → R-VIE-18, R-REP-08, **Q-11**.

### 3.2 Casos de uso

| ID | Actor | Caso de uso | Precondición | Resultado esperado |
|---|---|---|---|---|
| UC-01 | Persona / Agente / Lector | **Consultar el catálogo de exámenes** con su número de preguntas | Token válido | 200 con `{count, next, previous, results[]}`; cada examen con `question_count` correcto (F4) |
| UC-02 | Persona / Agente / Lector | **Consultar el detalle de un examen** | `exam` existe | 200 con el examen y su `question_count` |
| UC-03 | Persona / Agente / Lector | **Listar preguntas** (paginado, 5 por página) | — | 200 con paginación; orden estable por `id` (F3 `Meta.ordering`) |
| UC-04 | Persona / Agente / Lector | **Filtrar preguntas por examen** (`?exam=<id>`) | — | 200 solo con las preguntas de ese examen |
| UC-05 | Persona / Agente / Lector | **Buscar preguntas por texto** (`?search=`) | — | 200 con las que contienen el texto (case-insensitive) |
| UC-06 | Persona / Agente | **Crear una pregunta con sus opciones** en un solo `POST` | Token con permiso de escritura | 201; la pregunta y sus opciones quedan persistidas atómicamente |
| UC-07 | Persona / Agente | **Crear un examen** | idem | 201 con `id`, `title`, `created_at` |
| UC-08 | Agente | **Modificar parcialmente** una pregunta (`PATCH {"text": …}`) | — | 200; las opciones **no** se tocan |
| UC-09 | Persona / Agente | **Reemplazar las opciones** de una pregunta (`PUT`/`PATCH` con `choices`) | `choices` válido | Las opciones antiguas se sustituyen por las nuevas |
| UC-10 | Persona | **Borrar una pregunta** | — | 204 sin cuerpo; después 404 |
| UC-11 | Persona | **Borrar un examen** | — | 204; en cascada se van sus preguntas y opciones (`models.py:13`) |
| UC-12 | Agente | Intentar borrar (pregunta o examen) | — | **403** y el recurso sigue existiendo (F7) |
| UC-13 | Lector | Intentar crear o modificar | — | **403** |
| UC-14 | Visitante | Cualquier operación | — | **401** (no 403) |
| UC-15 | Persona | **Corregir una pregunta inválida** (2 correctas) | — | **400** con motivo legible en español; **no** se persiste nada |
| UC-16 | Persona | Usar `quizctl` para cualquier operación | `QUIZ_URL` y `QUIZ_TOKEN` | Código de salida según la tabla F2 + salida estable con `--json` |
| UC-17 | Persona | **`--dry-run`** de una escritura | — | Describe la petición, **no la envía**, sale 0 |
| UC-18 | Persona | `quizctl ops` | Servidor vivo | Lista de operaciones del contrato (lee `/api/schema/`) |
| UC-19 | Modelo de IA | Emitir una intención de **lectura** (R0) | Operación en `ALLOWED` | Se ejecuta; la respuesta vuelve envuelta como `untrusted_data` |
| UC-20 | Modelo de IA | Emitir una intención de **creación** (R1) | idem | Se ejecuta con el token del **agente** (nunca con el de la persona) |
| UC-21 | Modelo de IA | Emitir una intención **destructiva** (R2) | idem | **No se ejecuta**: devuelve `plan` + `plan_hash`; requiere aprobación humana |
| UC-22 | Persona | **Aprobar un plan R2** con su propio token | `approval == plan_hash` vigente | Se aplica; si los datos cambiaron, el hash ya no vale → `approval_required` |
| UC-23 | Persona | **Consultar la interfaz gráfica** (futuro) | — | Ver §7 (mejoras de UI) |

### 3.3 Reglas de negocio (HECHO)

| ID | Regla | Fuente |
|---|---|---|
| RN-01 | Una pregunta tiene **≥ 2 opciones** | `quiz/serializers.py:32-33` |
| RN-02 | Una pregunta tiene **exactamente 1 opción correcta** | `quiz/serializers.py:34-35` |
| RN-03 | `Choice.is_correct` tiene valor por defecto `False` | `quiz/models.py:27` |
| RN-04 | Las opciones **viajan anidadas** dentro de la pregunta; el examen viaja como **identificador** | `quiz/serializers.py:23-24` (comentario), `README` |
| RN-05 | Las opciones enviadas en un `update` **reemplazan** a las anteriores | `quiz/serializers.py:49-51` |
| RN-06 | `Exam.title` ≤ 120; `Choice.text` ≤ 200 | `quiz/models.py:5,26` |
| RN-07 | La página de resultados trae **5 elementos** | `config/settings.py:52-53` |
| RN-08 | El texto de la API va en **español** | `config/settings.py:37`, mensajes en `serializers.py:33,35` |
| RN-09 | El borrado en cascada: `Exam → Question → Choice` | `quiz/models.py:13,25` |
| RN-10 | El contenido devuelto por la API es **dato no confiable**, nunca una orden | `agent/gateway.py:20-22` |

---

## 4. Matriz de requisitos y criterios de aceptación — Criterio 1: Serializadores y validaciones (5 pts)

> **Alcance:** qué se expone y qué se valida en `quiz/serializers.py`. Los requisitos ya implementados se
> marcan como *cubiertos por lectura*; lacolumna **Prueba** remite a `docs/trazabilidad.md`.

### 4.1 `ExamSerializer` (`quiz/serializers.py:13-19`)

| ID | Requisito | Criterio de aceptación comprobable | Etiqueta | Prioridad |
|---|---|---|---|---|
| R-SER-01 | El examen expone `id`, `title`, `created_at`, `question_count` | `GET /api/exams/` devuelve esas 4 claves en cada elemento de `results` | HECHO | Imprescindible |
| R-SER-02 | `title` es **obligatorio** | `POST /api/exams/` sin `title` → **400** con error bajo la clave `title` | HIPÓTESIS (validación estándar de DRF) | Imprescindible |
| R-SER-03 | `title` respeta `max_length=120` | `POST /api/exams/` con `title` de 121 caracteres → **400**; con 120 → **201** | HIPÓTESIS | Recomendado |
| R-SER-04 | `title` no puede ser solo espacios | `POST` con `title="   "` → **400** | HIPÓTESIS | Recomendado |
| R-SER-05 | `created_at` es de **solo lectura** | `POST /api/exams/` enviando `created_at` → **201** y el valor enviado se ignora (el devuelto es el del servidor) | HIPÓTESIS | Recomendado |
| R-SER-06 | `question_count` es de **solo lectura** | `POST /api/exams/` enviando `question_count: 99` → **201** y el valor persistido no depende de lo enviado | HIPÓTESIS | Recomendado |
| R-SER-07 | `question_count` refleja el nº real de preguntas | Tras crear 3 preguntas en un examen nuevo, `GET /api/exams/{id}/` devuelve `question_count == 3` | HECHO (`views.py:11` anota `Count`) | Imprescindible |
| R-SER-08 | **Riesgo R-API-01:** `question_count` **falta** en la respuesta de `POST`/`PATCH` | `POST /api/exams/` (201) **no** incluye la clave `question_count` (DRF la omite: campo read-only sin atributo en la instancia recién creada). **Decisión de diseño pendiente**: (a) se acepta la asimetría y se documenta, o (b) se hace siempre presente con `SerializerMethodField`/default `0`. | HIPÓTESIS (fuerte) + **PENDIENTE de decisión** | Imprescindible (como decisión) |

### 4.2 `ChoiceSerializer` (`quiz/serializers.py:7-10`)

| ID | Requisito | Criterio de aceptación comprobable | Etiqueta | Prioridad |
|---|---|---|---|---|
| R-SER-09 | La opción expone `id`, `text`, `is_correct` | Un elemento de `choices` en la respuesta de una pregunta tiene esas 3 claves | HECHO | Imprescindible |
| R-SER-10 | `text` de opción es obligatorio | `POST` con una opción `{"is_correct": true}` → **400** | HIPÓTESIS | Imprescindible |
| R-SER-11 | `text` de opción ≤ 200 | `POST` con `text` de 201 caracteres → **400** | HIPÓTESIS | Recomendado |
| R-SER-12 | `is_correct` ausente equivale a `false` | `POST` con 2+ opciones **ninguna** con `is_correct` → **400** con el mensaje de "exactamente una" (0 correctas) | HECHO (`models.py:27` + `serializers.py:34`) | Imprescindible |
| R-SER-13 | `is_correct` con tipo no booleano → 400 | `POST` con `"is_correct": "sí"` → **400** | HIPÓTESIS | Recomendado |

### 4.3 `QuestionSerializer` (`quiz/serializers.py:22-52`)

| ID | Requisito | Criterio de aceptación comprobable | Etiqueta | Prioridad |
|---|---|---|---|---|
| R-SER-14 | La pregunta expone `id`, `exam`, `text`, `choices`, `created_at` | `GET /api/questions/{id}/` devuelve esas 5 claves | HECHO | Imprescindible |
| R-SER-15 | `exam` es obligatorio y **debe existir** | `POST` sin `exam` → **400**; con `exam: 999999` (inexistente) → **400** | HECHO/HIPÓTESIS (PrimaryKeyRelatedField) | Imprescindible |
| R-SER-16 | `exam` con tipo no numérico → 400 | `POST` con `exam: "no-es-un-numero"` → **400** | HECHO (prueba existente `test_api.py:65`) | Imprescindible |
| R-SER-17 | `text` es obligatorio | `POST` sin `text` → **400** | HECHO (prueba `test_api.py:60`) | Imprescindible |
| R-SER-18 | `choices` es **obligatorio en `POST`** | `POST` sin `choices` → **400** | HIPÓTESIS (campo anidado `many=True`, no `required=False`) | Imprescindible |
| R-SER-19 | **RN-01**: ≥ 2 opciones | `POST` con 1 opción → **400** con texto que contenga `al menos dos opciones` | HECHO (`serializers.py:32-33`) | Imprescindible |
| R-SER-20 | Lista de opciones vacía también se rechaza | `POST` con `choices: []` → **400** con el mismo mensaje | HECHO (misma rama, `len([]) == 0`) | Imprescindible |
| R-SER-21 | **RN-02**: exactamente 1 correcta; 2 o más → 400 | `POST` con 2 opciones `is_correct: true` → **400** con texto que contenga `exactamente una`, y `Question.objects.count()` **sin cambios** | HECHO (prueba `test_api.py:52-58`) | Imprescindible |
| R-SER-22 | 0 correctas → 400 con el mismo motivo | `POST` con 3 opciones todas `false` → **400** con `exactamente una` | HECHO (rama `!= 1`) | Imprescindible |
| R-SER-23 | El error de validación de `choices` se anida bajo la clave `choices` | El 400 contiene `{"choices": ["Debe haber exactamente una opción correcta."]}` | HECHO (`validate_choices` sobre campo anidado) | Imprescindible |
| R-SER-24 | Los mensajes de validación están en **español** | Todo 400 de negocio contiene texto en español | HECHO (`serializers.py:33,35`, `LANGUAGE_CODE="es"`) | Imprescindible |
| R-SER-25 | **`create` es atómico** | Ante un 400, ni la pregunta ni sus opciones quedan en la BD (`transaction.atomic`, `serializers.py:40`) | HECHO (prueba `test_api.py:57-58`) | Imprescindible |
| R-SER-26 | La respuesta de `POST` incluye las opciones creadas con su `id` | `POST` válido → 201 y `len(respuesta["choices"]) == número enviado`, cada una con `id` | HECHO (prueba `test_api.py:48-49`) | Imprescindible |
| R-SER-27 | **`update` es atómico** | Un `PATCH` con `choices` inválido no deja la pregunta a medias (vieja o nueva): estado anterior o posterior, nunca intermedio | HECHO por diseño (`serializers.py:47`) | Imprescindible |
| R-SER-28 | **`PATCH` sin `choices` conserva las opciones** (RN-04 + semántica parcial) | `PATCH {"text": "Nuevo"}` → 200 y la respuesta sigue con las 4 opciones originales | HECHO (prueba `test_api.py:70-74`) | Imprescindible |
| R-SER-29 | **`PATCH`/`PUT` con `choices` las reemplaza** (RN-05) | `PATCH {"choices": [2 nuevas]}` → 200; `Question.objects.get(pk).choices.count() == 2` y ninguna de las antiguas sobrevive | HECHO (`serializers.py:49-51`) | Imprescindible |
| R-SER-30 | **`PUT` exige el cuerpo completo** | `PUT /api/questions/{id}/` con solo `{"text": "x"}` → **400** (falta `exam` y `choices`); con `{"exam":…, "text":…, "choices":[…]}` → **200** | HIPÓTESIS (DRF exige los campos requeridos en `PUT`) | Imprescindible |
| R-SER-31 | No hay endpoint propio de opciones | El router solo expone `exams` y `questions`; `GET /api/choices/` → **404** | HECHO (`quiz/urls.py:6-7`) | Imprescindible |
| R-SER-32 | **Recomendado:** los textos de opción de una misma pregunta son distintos | `POST` con dos opciones de texto idéntico → **400** (o se documenta que se permite) | **PENDIENTE** (hoy no hay `UniqueConstraint` ni `validate`) | Recomendado |
| R-SER-33 | **Recomendado:** `Exam.title` es único | Dos exámenes con el mismo `title` → **400** en el segundo | **PENDIENTE** (hoy S07 sí tenía `UniqueConstraint`; S08 no) | Recomendado |
| R-SER-34 | **Opcional:** normalización de espacios (`strip`) en `title`, `text` y opciones | `"  REST  "` se guarda como `"REST"` | **PENDIENTE** | Opcional |

---

## 5. Matriz de requisitos y criterios de aceptación — Criterio 2: Vistas y enrutadores (5 pts)

| ID | Requisito | Criterio de aceptación comprobable | Etiqueta | Prioridad |
|---|---|---|---|---|
| R-VIE-01 | `DefaultRouter` monta `exams` y `questions` bajo `/api/` | `GET /api/exams/`, `/api/questions/`, `/api/exams/{id}/`, `/api/questions/{id}/` responden; la **raíz** `/api/` lista los recursos | HECHO (`quiz/urls.py`, `config/urls.py:5`) | Imprescindible |
| R-VIE-02 | `basename` explícito y estable (`exam`, `question`) | Los `operationId` del contrato son `exams_list`, `questions_create`, `questions_destroy`, … (los consume `agent/gateway.py:32-40`) | HECHO + probado en `test_api.py:83-93` | Imprescindible |
| R-VIE-03 | El listado de exámenes trae `question_count` real | Con el seed, los 2 exámenes devuelven `question_count == 4` | HECHO (prueba `test_api.py:23-26`) | Imprescindible |
| R-VIE-04 | Orden estable y determinista | `GET /api/questions/` devuelve `results` en orden creciente de `id`, también al paginar | HECHO (`models.py:17-18`, `serializers.py:25-26`) | Imprescindible |
| R-VIE-05 | Filtro por examen: `?exam=<id>` | `GET /api/questions/?exam=<id del 2º examen>` → `count == 4` | HECHO (prueba `test_api.py:33-35`) | Imprescindible |
| R-VIE-06 | Búsqueda por texto: `?search=<texto>` | `GET /api/questions/?search=prefetch_related` → `count == 1` (case-insensitive) | HECHO (prueba `test_api.py:37-39`) | Imprescindible |
| R-VIE-07 | Filtro y búsqueda son **combinables** | `GET /api/questions/?exam=<id>&search=...` devuelve la intersección de ambos | HIPÓTESIS (mismo `get_queryset`) | Imprescindible |
| R-VIE-08 | **Riesgo R-API-02:** un `?exam=` no numérico se **ignora en silencio** | `GET /api/questions/?exam=abc` → **200 con todas las preguntas**, no con un error | HECHO (`views.py:29`, guarda `isdigit()`) + **PENDIENTE de decisión** | Imprescindible (como decisión) |
| R-VIE-09 | Paginación `PageNumberPagination`, tamaño 5 | Con 8 preguntas: `count == 8`, `len(results) == 5`, `next` no nulo | HECHO (prueba `test_api.py:28-31`) | Imprescindible |
| R-VIE-10 | `?page=` funciona y una página inexistente da 404 | `?page=2` devuelve las 3 restantes; `?page=999` → **404** | HIPÓTESIS (comportamiento estándar DRF) | Recomendado |
| R-VIE-11 | **Sin N+1**: exam y opciones se traen en 2 consultas | `GET /api/questions/?page=1` (5 preguntas, 4 opciones cada una) ejecuta **≤ 3 consultas** con `assertNumQueries` | HECHO por diseño (`views.py:27`) | Imprescindible |
| R-VIE-12 | El contrato se publica en `/api/schema/` (JSON) y `/api/docs/` (Swagger UI) | `GET /api/schema/?format=json` → 200 JSON OpenAPI 3 | HECHO (prueba `test_api.py:86`; `config/urls.py:7-8`) | Imprescindible |
| R-VIE-13 | El parámetro `exam` está **documentado** en el contrato | El `operationId` `questions_list` declara un parámetro `exam` de tipo `integer` en la query | HECHO (`views.py:14-20`) | Imprescindible |
| R-VIE-14 | El contrato declara la autenticación por token | `components.securitySchemes` contiene `tokenAuth` | HECHO (prueba `test_api.py:95-97`) | Imprescindible |
| R-VIE-15 | **El contrato no se desincroniza de la pasarela** | `set(ALLOWED) ⊆ operationIds del contrato` | HECHO (prueba `test_api.py:83-93`) | Imprescindible |
| R-VIE-16 | Las operaciones de lectura no filtran datos de otros exámenes | Un lector autenticado ve **todos** los exámenes (no hay ACL por objeto) | HECHO (no hay filtro por usuario en `get_queryset`) | Imprescindible |
| R-VIE-17 | **Recomendado:** `OrderingFilter` con `?ordering=-id` | `GET /api/questions/?ordering=-id` invierte el orden y se documenta en el contrato | **PENDIENTE** | Recomendado |
| R-VIE-18 | **Contrato legible sin token** | `GET /api/schema/?format=json` responde 200 sin cabecera `Authorization` | **PENDIENTE de verificación** (el arquitecto lo marca sin comprobar: `docs/arquitectura.md:301-312`) → Q-11 | Imprescindible |
| R-VIE-19 | **Opcional:** *throttling* por token/IP en la API | N peticiones/min → **429** | **PENDIENTE** | Opcional |
| R-VIE-20 | **Opcional:** `DEFAULT_SCHEMA_CLASS` produce ejemplos de respuesta útiles | `/api/docs/` muestra cuerpos de ejemplo para 201 y 400 | **PENDIENTE** | Opcional |
| R-VIE-21 | **Nota (sin acción):** Swagger UI carga sus recursos de un CDN | Sin internet, `/api/docs/` se ve sin estilos. Si el laboratorio exige Red, hay que fijar `SWAGGER_UI_DIST` a un asset local | **PENDIENTE** (informativo) | Opcional |

---

## 6. Matriz de requisitos y criterios de aceptación — Criterio 3: Operaciones HTTP y códigos de estado (5 pts)

### 6.1 Matriz por endpoint

| Endpoint | Método | Rol | Código esperado | Cuerpo esperado | Requisito |
|---|---|---|---|---|---|
| `/api/exams/` | GET | cualquiera autenticado | **200** | `{count, next, previous, results[]}`; cada elemento con `question_count` | R-API-01 |
| `/api/exams/` | POST | persona, agente | **201** | Objeto creado (ver R-SER-08 sobre `question_count`) | R-API-02 |
| `/api/exams/{id}/` | GET | cualquiera autenticado | **200** | Objeto único | R-API-03 |
| `/api/exams/{id}/` | GET con `id` inexistente | cualquiera autenticado | **404** | `{"detail": "No encontrado."}` | R-API-04 |
| `/api/exams/{id}/` | PUT / PATCH | persona, agente | **200** | Objeto actualizado | R-API-05 |
| `/api/exams/{id}/` | DELETE | **solo persona** | **204** | Vacío; en cascada borra preguntas y opciones | R-API-06 |
| `/api/exams/{id}/` | DELETE | agente / lector | **403** | `{"detail": …}`; el examen sigue existiendo | R-API-07 |
| `/api/questions/` | GET | cualquiera autenticado | **200** | Página de 5 con `choices` anidadas | R-API-08 |
| `/api/questions/` | GET `?exam=&search=&page=` | cualquiera autenticado | **200** | Página filtrada/buscada | R-API-09 |
| `/api/questions/` | POST | persona, agente | **201** | Objeto creado con sus opciones | R-API-10 |
| `/api/questions/{id}/` | GET | cualquiera autenticado | **200** | Pregunta con opciones | R-API-11 |
| `/api/questions/{id}/` | PATCH | persona, agente | **200** | Solo cambia lo enviado | R-API-12 |
| `/api/questions/{id}/` | PUT | persona, agente | **200** / **400** si incompleto | Sustitución completa | R-API-13 |
| `/api/questions/{id}/` | DELETE | **solo persona** | **204** | Vacío; después **404** | R-API-14 |
| `/api/questions/{id}/` | DELETE | agente / lector | **403** | El recurso sobrevive | R-API-07 |
| `/api/schema/` | GET | cualquiera (público) | **200** | Esquema OpenAPI 3 en JSON/YAML | R-API-15 |
| `/api/docs/` | GET | cualquiera (público) | **200** | Swagger UI | R-API-15 |
| Cualquiera | **Sin token o token inválido** | — | **401** | `{"detail": "…"}` + cabecera `WWW-Authenticate: Token` | R-API-16 |
| Cualquiera escritura | Token válido sin permiso | — | **403** | `{"detail": "…"}` | R-API-17 |
| `/api/exams/1/` | POST (método no implementado) | — | **405** | `{"detail": "Method \"POST\" not allowed."}` | R-API-18 |
| `/api/questions/` | `Content-Type: text/plain` | — | **415** | Detalle de media type | R-API-19 |
| Cualquiera | Fallo interno | — | **5xx** | Sin detalles sensibles (con `DEBUG=True` **sí** los habría → ver R-REP-03) | R-API-20 |

### 6.2 Códigos de salida de `quizctl` (Parte 2 — funciones pendientes)

| ID | Requisito | Criterio de aceptación comprobable | Etiqueta |
|---|---|---|---|
| R-API-21 | `exit_code_for`: 2xx → **0** | `exit_code_for(200) == 0`, igual para 201 y 204 | HECHO en la especificación (`quizctl.py:47-49`), **PENDIENTE de implementación** |
| R-API-22 | `exit_code_for`: 400 → **2** | `exit_code_for(400) == 2` | idem |
| R-API-23 | `exit_code_for`: 401 y 403 → **3** | `exit_code_for(401) == exit_code_for(403) == 3` | idem |
| R-API-24 | `exit_code_for`: 404 → **4** | `exit_code_for(404) == 4` | idem |
| R-API-25 | `exit_code_for`: 5xx → **5** | `exit_code_for(500) == exit_code_for(503) == 5` | idem |
| R-API-26 | `exit_code_for`: cualquier otro → **1** | `exit_code_for(302) == 1`; `405` y `409` también | idem |
| R-API-27 | `build_question_payload`: `:ok` **final** marca la correcta | `["Un estilo:ok", "Un lenguaje"]` → `[{"text":"Un estilo","is_correct":true},{"text":"Un lenguaje","is_correct":false}]` | idem |
| R-API-28 | Solo el **último** `:ok` cuenta | `["Verdad: sí:ok", "ok es una palabra"]` → la 1ª `true`, la 2ª `false` (y el texto conserva los dos puntos) | idem |
| R-API-29 | El cliente **no duplica** la validación del servidor | `["a:ok","b:ok"]` produce un body con 2 correctas **sin lanzar error**; el 400 llega del servidor y `quizctl` sale **2** | idem (`quizctl.py:61-62`) |
| R-API-30 | Sin `QUIZ_TOKEN` → **1** (error de uso, no de red) | `quizctl exams list` sin la variable → salida **1** | HECHO (`quizctl.py:73-74`) |
| R-API-31 | Sin conexión → **6** | Servidor inalcanzable → salida **6** | HECHO (`quizctl.py:83-84`) |
| R-API-32 | `--dry-run` no escribe nada | Salida **0**, texto con `[dry-run] POST`, y el listado sigue con el mismo `count` | HECHO (`quizctl.py:76-77`) |
| R-API-33 | `--json` produce una salida **estable** | El JSON tiene siempre las claves `status`, `data`, `error`, `request` | HECHO (`quizctl.py:147-150`) |
| R-API-34 | `ops` lista las operaciones del contrato leyendo la API | La salida contiene `questions_destroy` | HECHO (`quizctl.py:135-143`) |
| R-API-35 | El 403 del servidor se traduce a salida **3** | `quizctl questions delete <id>` con token de agente → salida **3** | Especificado en `README.md:73-80`; depende de la Parte 3 |
| R-API-36 | Un 404 se traduce a salida **4** | `quizctl questions get 99999` → salida **4** | Especificado (`README.md:63-71`) |

### 6.3 Códigos de salida de la frontera del agente (Parte 4 — ya implementada, se documenta como contrato)

| ID | Requisito | Criterio de aceptación comprobable | Etiqueta |
|---|---|---|---|
| R-API-37 | R0 (lectura) se ejecuta y vuelve como `untrusted_data` | `{"op":"exams_list"}` → `status == "ok"`, `http == 200` | HECHO (`test_agent.py:32-35`) |
| R-API-38 | R1 (crear) se ejecuta con el token del **agente** | `{"op":"questions_create", …}` → `status == "ok"`, `http == 201` | HECHO (`test_agent.py:50-54`) |
| R-API-39 | R2 (destructivo) **nunca** se ejecuta solo | `{"op":"exams_destroy",…}` → `status == "approval_required"` + `plan.plan_hash`, y el examen sigue existiendo | HECHO (`test_agent.py:43-48`) |
| R-API-40 | Aprobar R2 exige el token de la **persona** | Sin `human_token` → `status == "denied"` y nada se borra | HECHO (`test_agent.py:72-78`) |
| R-API-41 | La aprobación caduca si el objetivo cambió | Se crea una pregunta nueva entre el plan y la aprobación → vuelve `approval_required` | HECHO (`test_agent.py:80-87`) |
| R-API-42 | Operación fuera de la lista cerrada → `denied` | `{"op":"run_sql"}` / `{"op":"users_list"}` → `denied` | HECHO (`test_agent.py:102-104`) |
| R-API-43 | Los argumentos se validan estrictamente (claves y tipos) | `path.id` como texto, `bool`, clave extra, parámetro desconocido → `denied` | HECHO (`test_agent.py:106-119`) |
| R-API-44 | Una operación que desapareció del contrato deja de ofrecerse | Se inyecta una `operationId` inexistente → `denied` con motivo que menciona el *contrato* | HECHO (`test_agent.py:121-125`) |
| R-API-45 | El texto hostil es **dato**, no orden | Buscar `IGNORA` devuelve la pregunta, **pero** nada se borra | HECHO (`test_agent.py:37-41`, `seed_data.py:7-10`) |
| R-API-46 | Toda decisión deja una línea de auditoría | `agent_audit.jsonl` acumula una línea por decisión con `actor`, `op`, `risk`, `outcome` | HECHO (`test_agent.py:130-136`) |

### 6.4 Reglas de roles (Criterio 3, Parte 3 — `quiz/permissions.py` PENDIENTE)

| ID | Requisito | Criterio de aceptación comprobable | Etiqueta | Prioridad |
|---|---|---|---|---|
| R-API-47 | Persona (`is_staff`) puede **todo**, incluido borrar | `DELETE /api/questions/{id}/` con token de `profe` → **204** y el recurso desaparece | Especificado (`permissions.py:9-11`), **PENDIENTE de implementación** | Imprescindible |
| R-API-48 | Agente (grupo `agente`) lee, crea y modifica | GET → 200; POST → 201; PATCH → 200 | idem | Imprescindible |
| R-API-49 | Agente **nunca** borra | `DELETE /api/questions/{id}/` → **403** y `Question.objects.filter(id=…).exists()` sigue siendo `True` | idem | Imprescindible |
| R-API-50 | El veto del agente aplica también a **exámenes** | `DELETE /api/exams/{id}/` con token de agente → **403** | idem | Imprescindible |
| R-API-51 | Cualquier otro autenticado **solo lee** | GET → 200; POST/PATCH/PUT/DELETE → **403** | idem | Imprescindible |
| R-API-52 | Sin token es **401**, no 403 | `GET` sin cabecera → **401** | idem | Imprescindible |
| R-API-53 | **Denegar por defecto**: método desconocido o no permitido | Un método no contemplado en la regla → **403** | idem (`permissions.py:13`) | Imprescindible |
| R-API-54 | **Ambigüedad PENDIENTE:** ¿puede el agente modificar **exámenes**? | `PATCH /api/exams/{id}/` con token de agente → la regla ("crear y modificar") sugiere 200, pero ninguna prueba lo fija | **PENDIENTE de decisión** | Imprescindible (como decisión) |

---

## 7. Criterio 4: Repositorio y tabla de API (5 pts) — dos bloques

### 7.0 Interpretación del criterio (declarada, no inventada)

El enunciado de la misión nombra el criterio «**Repositorio y tabla de API**». **No consta el texto oficial**
(el documento de rúbrica está en el campus, F1 §2.2). Este documento cubre **las dos lecturas posibles**, para
que el resultado sea correcto con cualquiera de ellas:

- **Lectura A — bloque de repositorio:** higiene del proyecto (README, dependencias, `.gitignore`, pruebas,
  convenciones). → §7.1
- **Lectura B — bloque de interfaz:** una **tabla en pantalla** que liste exámenes y preguntas, alimentada por la
  API. → §7.2 (y requisitos de UI en §8)

### 7.1 Bloque A — Repositorio (imprescindible)

| ID | Requisito | Criterio de aceptación comprobable | Etiqueta | Prioridad |
|---|---|---|---|---|
| R-REP-01 | `README.md` documenta puesta en marcha, las 4 partes y la tabla de códigos de salida | Un lector puede ejecutar los comandos del README desde cero | HECHO (`README.md:10-31`) | Imprescindible |
| R-REP-02 | `requirements.txt` fija las 4 dependencias del laboratorio | `Django>=5.2,<7`, `djangorestframework>=3.16`, `drf-spectacular>=0.28`, `requests>=2.32` | HECHO | Imprescindible |
| R-REP-03 | **No se despliega con `DEBUG=True` ni con la clave de reserva** | Fuera de desarrollo, `DJANGO_SECRET_KEY` es obligatoria y `DEBUG=False` | HECHO que es **inseguro hoy** (`settings.py:9-10`) | Imprescindible (riesgo, ver R-9) |
| R-REP-04 | `.gitignore` excluye secretos y artefactos | `.env`, `db.sqlite3`, `agent_audit.jsonl`, `schema.yml`, `.venv/`, `__pycache__/` | HECHO (`.gitignore:1-7`) | Imprescindible |
| R-REP-05 | Ningún token ni clave versionado | `grep` de `Token.objects…key`/valores de token en el repo → 0 coincidencias fuera de código de seed | HECHO por lectura; **verificación con `rg` pendiente** | Imprescindible |
| R-REP-06 | Estructura de paquetes coherente | `config/` (proyecto), `quiz/` (API), `agent/` (frontera), `quizctl.py` (cliente), `quiz/tests/` (pruebas) | HECHO | Imprescindible |
| R-REP-07 | `python manage.py test` deja los 4 módulos en verde | `test_api`, `test_agent`, `test_quizctl`, `test_permissions` → todos OK | Especificado; **no ejecutado en esta fase** | Imprescindible |
| R-REP-08 | El contrato es regenerable y ** legible sin token** (lo consume `agent/gateway.py:52` sin credencial) | `python manage.py spectacular --file schema.yml` produce el esquema **y** `GET /api/schema/?format=json` sin `Authorization` → 200 | PENDIENTE de verificación → Q-11 | Imprescindible |
| R-REP-09 | Convenciones del curso | Código, nombres y comentarios en inglés; entregables en español; PEP 8 | HECHO (`AGENTS.md`, `README.md:117-119`) | Imprescindible |
| R-REP-10 | Protocolo de equipo documentado | `AGENTS.md` + `opencode.json` presentes | HECHO | Recomendado |
| R-REP-11 | Datos de arranque reproducibles e idempotentes | `seed_quiz` se puede repetir y conserva los tokens | HECHO (`seed_quiz.py:11-27`) | Imprescindible |
| R-REP-12 | Migraciones solo de esquema, sin datos | `0001_initial` crea tablas; `seed_quiz` carga datos aparte | HECHO | Recomendado |
| R-REP-13 | Documentación de arquitectura cuando haya decisión nueva | Un ADR si se adoptan plantillas/sesiones o si se cambia una regla de la API | **PENDIENTE** (no existe `docs/adr/`) | Recomendado |
| R-REP-14 | CI o guía de verificación reproducible | Alternativa mínima: script documentado que ejecute `migrate` + `seed_quiz` + `test` | **PENDIENTE** (no hay CI) | Opcional |

### 7.2 Bloque B — Tabla de API / interfaz (mejora adicional: §8)

Si el criterio 4 incluye la tabla en pantalla, sus requisitos son **R-UI-01 … R-UI-10** (§8). Si el criterio 4 es
solo "repositorio", este bloque no aporta puntaje y es **recomendado**, no imprescindible.

---

## 8. Mejoras adicionales de INTERFAZ (UI) — **no existe hoy en el repositorio**

> **Hecho comprobado:** el proyecto es headless. `INSTALLED_APPS` **no** incluye `admin`, `sessions`, `messages`
> ni `staticfiles`; `MIDDLEWARE` solo tiene `SecurityMiddleware` y `CommonMiddleware`; **no hay bloque `TEMPLATES`**;
> **no existe** ninguna carpeta `templates/` ni `static/`; la única interfaz es `/api/docs/` (Swagger UI, que es
> documentación del contrato, no una UI de gestión). Todo esto es verificable en `config/settings.py:13-25` y por
> ausencia de archivos.
>
> El proyecto de referencia S07 (F13) **sí** tiene esa capa: CBV, plantillas con `base.html` + partials,
> `ModelForm`, admin, sesiones/messages/csrf/auth, `STATICFILES_DIRS`, tests por app. La UI de este laboratorio
> **sería un bloque nuevo**, no una adaptación.

> **Estado de la decisión de arquitectura:** el arquitecto ya decidió la UI en
> `docs/adr/0001-arquitectura-de-la-interfaz-web.md` (**server-rendered**: plantillas Django + `ModelForm` +
> `formset` en línea para `Choice` + CBVs en `quiz/web_views.py` + una única hoja CSS propia, **sin CDN, sin
> JavaScript obligatorio y sin `django.contrib.admin`**), con detalle en `docs/arquitectura.md`.
> Los requisitos R-UI-01…14 de abajo se han **alineado** con esa decisión; las preguntas Q-02 y Q-03 quedan por
> tanto **respondidas técnicamente**, aunque siguen necesitando el visto bueno del usuario sobre si la UI entra
> en el alcance de **esta** entrega.

### 8.1 Requisitos de UI

| ID | Requisito | Criterio de aceptación comprobable | Prioridad |
|---|---|---|---|
| R-UI-01 | **Tabla de exámenes**: columnas id, título, nº de preguntas y acciones | `GET /examenes/` devuelve una tabla con una fila por examen y el nº de preguntas coincide con `question_count` del API | Imprescindible *si* la UI entra en alcance |
| R-UI-02 | **Tabla de preguntas**: columnas id, examen, texto (truncado), nº de opciones, opción correcta, acciones | `GET /preguntas/` muestra una fila por pregunta con sus datos | Ídem |
| R-UI-03 | Las tablas son **paginadas** y navegables | Hay Anterior/Siguiente alineados con la paginación del viewset (`paginate_by=5`) | Ídem |
| R-UI-04 | Filtro por examen y búsqueda por texto operables desde la pantalla | Los parámetros `GET` `?search=` y `?exam=` reducen la tabla; **la página es compartible por URL** | Ídem |
| R-UI-05 | Alta/edición de pregunta en **un solo formulario** con `formset` en línea de `Choice` | Enviar 1 opción, o 2 correctas, muestra el error del campo o no-de-campo **sin perder lo ya escrito** | Ídem |
| R-UI-06 | Confirmación antes de borrar (`DeleteView` con plantilla propia) | Un clic en «Eliminar» pide confirmación; sin `POST` de confirmación no se borra | Ídem |
| R-UI-07 | La UI **respeta los roles** mediante la tabla de acciones compartida con la API | Con sesión de agente, «Eliminar» no se renderiza **y** la vista responde 403 si se fuerza | Ídem |
| R-UI-08 | Los errores se muestran con las plantillas `403/404/500` propias | Un POST inválido vuelve a la misma página con errores visibles, no una página 500 genérica | Ídem |
| R-UI-09 | Estados vacíos contemplados | Sin exámenes/preguntas se muestra un estado vacío, no una tabla rota | Recomendado |
| R-UI-10 | Plantilla `base.html` + partials + `quiz/static/quiz/css/style.css`, **sin CDN** | Las vistas extienden `base.html`; la hoja se sirve con `DEBUG=False` y sin internet | Recomendado |
| R-UI-11 | Accesibilidad como parte del CSS: `:focus-visible`, contraste ≥ 4.5:1, navegación por tabulador sin trampas, `prefers-reduced-motion` | Revisión de plantilla + hoja; ningún `:focus { outline: none }` | Recomendado |
| R-UI-12 | La UI **funciona sin JavaScript** | Con el JS deshabilitado se pueden listar, crear, editar y borrar | Recomendado |
| R-UI-13 | Pruebas de la UI | `quiz/tests/test_ui.py` con el patrón de S07 (`test_front_page`, `test_auth`, `test_crud`) | Recomendado |
| R-UI-14 | Sin `django.contrib.admin` | `/admin/` no existe o da 404: **no hay una segunda vía de escritura** que esquive RN-01/RN-02 | Imprescindible *si* la UI entra en alcance |

### 8.2 Requisitos técnicos que la UI arrastra (decisión de arquitectura, no de producto)

Estos **no son requisitos de negocio**; son consecuencias que el arquitecto debe resolver (ADR) antes de
implementar R-UI-01…14:

| ID | Necesidad | Situación actual (hecho) |
|---|---|---|
| R-UI-T1 | Motor de plantillas | Falta el bloque `TEMPLATES` por completo. **Resuelto en ADR 0001**: `quiz/templates/quiz/` con `base.html` + `partials/` (`docs/arquitectura.md:216-240`) |
| R-UI-T2 | Servir estáticos | `staticfiles` **no** está en `INSTALLED_APPS`; con `runserver` los estáticos no se sirven → añadir la app (`docs/arquitectura.md:164-190`) |
| R-UI-T3 | Identidad del navegador | Hoy la API es **solo por token**. **Resuelto en ADR 0001 / arquitectura §4.5**: API por token, UI por cookie `sessionid`, **las dos no se mezclan**; CSRF obligatorio solo en la UI |
| R-UI-T4 | Ruta de los datos | **Resuelto en ADR 0001**: la UI usa **`ModelForm` + ORM**, no llama a la API por HTTP. Por tanto RN-01/RN-02 **no** se aplican solos → ver R-UI-T5 (**obligatorio**) |
| R-UI-T5 | Reutilizar las reglas de negocio | **Crítico**: con `ModelForm` el `formset` reimplementa RN-01/RN-02. Debe haber **un único validador** en `quiz/` reutilizado por el serializador y por el formulario, o dos caminos que pueden divergir |
| R-UI-T6 | Coexistencia con el agente | La UI no debe ofrecer acciones que el agente no puede ejecutar, ni abrir la puerta de R2 sin aprobación humana. Sin `admin` (R-UI-14) no hay segunda vía de escritura |
| R-UI-T7 | **Los cuatro entregables siguen verdes tras tocar `settings.py`** | Requisito de regresión explícito del arquitecto (`docs/arquitectura.md:294-297`): añadir sesiones/CSRF/auth **no debe** romper `test_api`, `test_agent`, `test_quizctl` ni `test_permissions` |

---

## 9. Qué es obligatorio de la API y qué es mejora de UI

| Bloque | Contenido | Naturaleza |
|---|---|---|
| **A — API headless (obligatorio del laboratorio)** | R-SER-*, R-VIE-*, R-API-01…36, R-API-47…54, R-REP-01…12 | Requisitos de la rúbrica. El 90 % ya está implementado; faltan las **Partes 2 y 3** |
| **B — Frontera del agente (obligatorio, ya hecha)** | R-API-37…46 | Verificar y documentar; no tocar sin acuerdo con `arquitecto-ia` |
| **C — Tabla de API / repositorio (criterio 4)** | R-REP-* si es lectura A; R-UI-01…14 si es lectura B | **Ambigüedad de rúbrica** → Q-01 |
| **D — Mejoras de calidad (no en el enunciado)** | Ordenación, unicidad de título, 405/415, throttling, CSP, normalización | Recomendadas por riesgo, **no** reclamadas por la rúbrica |
| **E —Fuera de alcance** | Docker, CI, despliegue, apps móviles, multi-idioma | No hay evidencia; no implementar salvo decisión |

---

## 10. Priorización

### 10.1 Imprescindible (bloquea la entrega del laboratorio)

| # | Tarea | Requisitos | Depende de |
|---|---|---|---|
| T-IMP-1 | Implementar `quizctl.exit_code_for` (mapeo de estados → códigos 0–6) | R-API-21…26 | — |
| T-IMP-2 | Implementar `quizctl.build_question_payload` (`:ok` final, sin validar) | R-API-27…29 | — |
| T-IMP-3 | Implementar `quiz.permissions.AgentPermission` (4 ramas de la regla + denegar por defecto) | R-API-47…53 | — |
| T-IMP-4 | Cerrar `python manage.py test` en verde | R-REP-07 | T-IMP-1, 2, 3 |
| T-IMP-5 | **Decidir** el contrato de `question_count` en respuestas de escritura | R-SER-08 | — |
| T-IMP-6 | **Decidir** el comportamiento de `?exam=` no numérico (ignorar vs 400) | R-VIE-08 | — |
| T-IMP-7 | **Decidir** si el agente puede modificar exámenes (PUT/PATCH) | R-API-54 | — |
| T-IMP-8 | Actualizar el README con el estado real y la sección de UI si se aprueba | R-REP-01, R-REP-13 | T-IMP-1…7 |

### 10.2 Recomendado

| # | Tarea | Requisitos |
|---|---|---|
| T-REC-1 | Pruebas que cierran los huecos: `PUT` incompleto (400), `choices: []`, 0 correctas, 405, 415, `?page=999`, `is_correct` con tipo raro, `title` a 121 | R-SER-20, R-SER-22, R-SER-30, R-API-18/19, R-VIE-10, R-SER-03, R-SER-13 |
| T-REC-2 | `assertNumQueries` para demostrar que no hay N+1 | R-VIE-11 |
| T-REC-3 | `UniqueConstraint` de `Exam.title` + normalización de espacios | R-SER-33, R-SER-34 |
| T-REC-4 | `OrderingFilter` documentado | R-VIE-17 |
| T-REC-5 | Documentar que el contrato es público y por qué (romperlo rompe la pasarela) | R-VIE-18, R-REP-08 |
| T-REC-6 | ADR si se adoptan plantillas/sesiones/UI | R-REP-13, R-UI-T1…T6 |
| T-REC-7 | `DEBUG`/`SECRET_KEY` con conmutador por entorno | R-REP-03 |
| T-REC-8 | Tests de UI (`test_ui.py`) si entra en alcance | R-UI-12 |

### 10.3 Opcional

| # | Tarea | Requisitos |
|---|---|---|
| T-OP-1 | Throttling (429) | R-VIE-19 |
| T-OP-2 | Swagger UI con assets locales (sin CDN) | R-VIE-21 |
| T-OP-3 | Script/CI de verificación | R-REP-14 |
| T-OP-4 | Modo «jugar» y accesibilidad fina | R-UI-11, R-UI-13 |
| T-OP-5 | Django admin como interfaz mínima de gestión | — (PENDIENTE) |

---

## 11. Dependencias

| # | Dependencia | Tipo | Notas |
|---|---|---|---|
| D-01 | `test_quizctl.CliLiveTests.test_the_agent_token_cannot_delete_exit_three` necesita la **Parte 3** | Funcional | La prueba de permisos bloquea una prueba de cliente (`test_quizctl.py:104-108`) |
| D-02 | T-IMP-1/2 → `test_quizctl` verde | Funcional | `NotImplementedError` hoy |
| D-03 | Las pruebas `LiveServerTestCase` usan `host = "127.0.0.1"` y `STATIC_URL` | Entorno | Sin `STATIC_URL` el servidor de pruebas responde 500 a todo (`settings.py:42`) |
| D-04 | Todas las pruebas dependen de `seed_quiz` | Datos | `helpers.py:8-13`; crea `profe`, `agente` y sus tokens |
| D-05 | La UI depende de decisiones de arquitectura (**Q-02, Q-03**) y de un ADR | Decisión | Bloquea T-REC-6, T-REC-8 y todo R-UI-* |
| D-06 | R-UI-T2 requiere añadir `django.contrib.staticfiles` | Configuración | Afecta `INSTALLED_APPS` |
| D-07 | R-UI-T3 requiere `sessions` + `csrf` + `auth` en `MIDDLEWARE` | Configuración | Afecta al `settings` actual, que hoy es deliberadamente mínimo |
| D-08 | `drf-spectacular` es requisito de R-VIE-12…15 y de R-API-46 | Paquete | Ya en `requirements.txt` |
| D-09 | `requests` es requisito del cliente y de la pasarela | Paquete | Ya en `requirements.txt` |

---

## 12. Ambigüedades

| ID | Ambigüedad | Impacto | Quién decide |
|---|---|---|---|
| A-01 | Texto oficial de la rúbrica no está en el repo | Define qué puntúa el bloque «tabla de API» | Usuario (Q-01) |
| A-02 | ¿La UI debe existir? La misión lo pide; el repo y el README son headless | Define ~13 requisitos | Usuario (Q-02) |
| A-03 | `question_count` ausente en la respuesta de escritura | Inconsistencia visible en cualquier consumidor | Arquitecto + Backend (Q-04) |
| A-04 | `?exam=abc` se ignora en silencio | Un filtro mal escrito devuelve datos que no son los pedidos | Backend (Q-05) |
| A-05 | Alcance de «modificar» del agente sobre exámenes | 200 o 403 en `PATCH /api/exams/{id}/` | Seguridad (Q-06) |
| A-06 | El agente puede **crear exámenes** (POST `/api/exams/`), sin prueba que lo fije | Hueco de contrato sin cobertura | Seguridad (Q-06) |
| A-07 | ¿Duplicar `title` de examen es un error? | En la tabla de UI aparecerían filas indistinguibles | Backend (Q-07) |
| A-08 | ¿Se admite `?ordering=`? | No está en `ALLOWED` del agente ni en el contrato actual | Arquitecto |
| A-09 | `runserver` + `DEBUG=True` como única forma de probar | No es requisito, pero la rúbrica puede penalizar «no documentado que es solo desarrollo» | Documentador |
| A-10 | ¿`pytest` o `manage.py test`? | El repo usa `manage.py test`; no está declarado en ninguna parte | Usuario (Q-08) |

---

## 13. Riesgos

| ID | Riesgo | Prob. | Impacto | Mitigación / requisito |
|---|---|---|---|---|
| R-01 | **`AgentPermission` devuelve `True`**: con el token del agente se puede **borrar** (`permissions.py:20`) | Cierta (código abierto) | **Crítico** | T-IMP-3 (R-API-49/50) + `test_permissions` |
| R-02 | `DEBUG=True` y `SECRET_KEY` con reserva en el código (`settings.py:9-10`) | Cierta | Alto | R-REP-03, T-REC-7; documentar «solo desarrollo» |
| R-03 | Un 500 en `DEBUG=True` puede filtrar estructura interna | Media | Medio | R-REP-03 |
| R-04 | **`question_count` no aparece** en respuestas de escritura | Alta | Medio | R-SER-08 / Q-04 |
| R-05 | `?exam=` no numérico se ignora en silencio | Alta | Bajo | R-VIE-08 / Q-05 |
| R-06 | **UI sin identidad**: meter un token en el navegador lo expone a XSS/CSRF | Media | **Alto** | Q-02/Q-03 + ADR antes de implementar R-UI |
| R-07 | Si la UI usa el ORM, las reglas RN-01/RN-02 quedan **sin aplicar** en esa vía | Media | Alto | R-UI-T4/R-UI-T5 + prueba compartida |
| R-08 | Añadir `admin`/`sessions`/`staticfiles` es un **cambio de arquitectura** en un repo deliberadamente mínimo | Media | Medio | R-REP-13 (ADR) y decisión del arquitecto |
| R-09 | Texto hostil (`seed_data.py:7-10`) renderizado en una futura tabla HTML | Media | Medio | Escapado automático de Django + R-UI-07 (no mostrar «Ejecutar instrucciones») |
| R-10 | Relajar `validate_choices` para dar mejor experiencia en la UI rompería RN-01/RN-02 | Baja | **Alto** | Regla única en `quiz/`, reutilizada (R-UI-T5) |
| R-11 | Cambiar el contrato puede dejar `ALLOWED` desalineado | Baja | Alto | R-VIE-15 ya lo detecta (`test_api.py:83-93`) |
| R-12 | SQLite: conclusiones de rendimiento/escala no extrapolables | Cierta | Bajo | Documentar el alcance del laboratorio |
| R-13 | Sin CI, la calidad depende de que alguien ejecute las pruebas | Cierta | Medio | R-REP-14 (opcional) |
| R-14 | La rúbrica real puede pedir cosas no recogidas aquí | Media | Medio | Q-01 antes de cerrar la entrega |

---

## 14. Preguntas abiertas (al usuario)

| ID | Pregunta | Por qué bloquea | Respuesta |
|---|---|---|---|
| Q-01 | ¿Puedes compartir el texto de la rúbrica del campus? ¿«tabla de API» significa tabla en pantalla o tabla de operaciones documentada? | Define si R-UI-* puntúa o no | _pendiente_ (el arquitecto ya dejó una tabla de la API documentada en `docs/arquitectura.md:373-394`, pero eso **no** resuelve si la rúbrica pide una UI) |
| Q-02 | La UI: ¿plantillas server-rendered + sesión (patrón S07), SPA que consume la API con token, o Django admin? | Bloquea todo R-UI-* y R-UI-T1…T6 | **RESPONDIDA** en ADR 0001 (server-rendered, sin admin). Falta solo que el usuario confirme que la UI entra en el alcance de esta entrega → Q-09 |
| Q-03 | ¿La UI **llama a la API por HTTP** o **usa el ORM** de Django? | Decide si hay una o dos rutas de validación | **RESPONDIDA** en ADR 0001: usa el ORM (`ModelForm` + `formset`). **Consecuencia obligatoria: R-UI-T5** (validador único compartido) |
| Q-04 | ¿`question_count` debe aparecer siempre (incluso con 0 al crear) o se acepta que falte en escrituras? | Contrato hacia el cliente y la UI | _pendiente_ |
| Q-05 | ¿`?exam=abc` debe dar 400 o se ignora como hoy? | Coherencia y depuración | _pendiente_ |
| Q-06 | ¿El agente puede crear y modificar **exámenes** además de preguntas? | Cobertura del contrato y de la pasarela | _pendiente_ (el arquitecto ya diseñó la tabla de permisos en `docs/arquitectura.md:316-321`; hay que confirmar que incluye estas acciones) |
| Q-07 | ¿`Exam.title` debe ser único? | Calidad de datos y de la tabla | _pendiente_ |
| Q-08 | ¿Se mantiene `manage.py test` o se adopta `pytest`/`pytest-django`? | Herramienta de verificación | _pendiente_ |
| Q-09 | ¿La UI entra en el alcance de esta entrega o es una fase posterior? | Priorización: R-UI-* son ~15 requisitos sin implementar | _pendiente_ (**la decisión que más pesa ahora mismo**) |
| Q-10 | ¿Se espera CI/Docker? | Activa al agente DevOps | _pendiente_ |
| Q-11 | ¿`/api/schema/` es legible sin token? El arquitecto lo marca **sin verificar** (`docs/arquitectura.md:301-312`) | Si exige token, `agent.gateway.load_catalog` y `quizctl ops` se rompen | _pendiente_ (comando de comprobación ya dado en ese documento) |
| Q-12 | ¿Quién es la **tabla de acciones única** que comparten API y UI? | Sin ella hay dos reglas de permisos que pueden divergir | _pendiente_ de confirmación (ADR 0003 citado en `docs/arquitectura.md:318`) |

---

## 15. Criterio de aceptación de **este** documento

- [x] Cubre los 4 criterios de la rúbrica con requisitos desglosados.
- [x] Cada requisito tiene un criterio de aceptación **comprobable** (estado HTTP, clave del JSON, mensaje o conteo).
- [x] Separa API obligatoria de mejora de UI.
- [x] Distingue **HECHO** / **HIPÓTESIS** / **PENDIENTE** en cada fila.
- [x] Declara explícitamente que **el texto oficial de la rúbrica no está en el repositorio**.
- [x] Prioriza, y lista dependencias, ambigüedades, riesgos y preguntas abiertas.
- [x] No afirma que ninguna prueba se haya ejecutado en esta fase.
- [x] Trazabilidad requisito → implementación → prueba en `docs/trazabilidad.md`.
