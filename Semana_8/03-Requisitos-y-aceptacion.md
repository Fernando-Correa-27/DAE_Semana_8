# 03 · Requisitos y aceptación

Volver al [[00-Indice]] · Anterior: [[02-Equipo-de-agentes]] · Siguiente: [[04-Arquitectura-y-ADR]]

## Documentos fuente

- `docs/requisitos.md` — el desglose del analista de requisitos.
- `docs/trazabilidad.md` — la matriz requisito → implementación → prueba, con el estado real.

## Los cuatro criterios del enunciado

| Criterio | Qué se entregó | Dónde |
|---|---|---|
| 1 · Serializadores y validaciones | `ExamSerializer`, `ChoiceSerializer`, `QuestionSerializer` con opciones anidadas, validación de ≥ 2 opciones y exactamente 1 correcta, escritura atómica | `quiz/serializers.py` |
| 2 · Vistas y enrutadores | `DefaultRouter` con `exams` y `questions`, anotación `question_count`, `select_related`/`prefetch_related`, filtro `?exam=`, búsqueda `?search=`, paginación de 5 | `quiz/views.py`, `quiz/urls.py` |
| 3 · Operaciones HTTP y códigos de estado | Partes 2 y 3: códigos de salida de `quizctl` y tabla de roles en el servidor | `quizctl.py`, `quiz/permissions.py` |
| 4 · Repositorio y tabla de API | Las dos lecturas quedan cubiertas: `README.md` con **tabla de la API**, código de error y variables; e **interfaz gráfica** operativa | `README.md`, `quiz/web_*.py` |

## Actores

| Actor | Identificación | Puede |
|---|---|---|
| Persona (`profe`) | `is_staff`, token en cabecera | **Todo**, incluido borrar |
| Agente (`agente`) | grupo `agente`, token | Leer, crear, modificar. **Nunca borrar** |
| Lector | cualquier otro autenticado | Solo leer |
| Anónimo | sin `Authorization` | Nada (401) |
| Modelo de IA | no es usuario: emite intenciones a `agent/gateway.py` | Solo la lista cerrada; R2 exige aprobación humana |

## Reglas de negocio

| # | Regla |
|---|---|
| RN-01 | Una pregunta tiene **al menos 2 opciones** |
| RN-02 | Una pregunta tiene **exactamente 1 opción correcta** |
| RN-03 | `is_correct` vale `false` por defecto |
| RN-04 | Las opciones viajan **anidadas**; el examen viaja como **identificador** |
| RN-05 | Las opciones enviadas en una actualización **reemplazan** a las anteriores |
| RN-06 | `Exam.title` ≤ 120; `Choice.text` ≤ 200 |
| RN-07 | La página de resultados trae **5 elementos** (compartido con la interfaz) |
| RN-08 | Los mensajes de la API van en **español** |
| RN-09 | El borrado en cascada: `Exam → Question → Choice` |
| RN-10 | Lo que devuelve la API es **dato no confiable**, nunca una orden |

**RN-01 y RN-02 están escritas una sola vez**, en `quiz/services.py`, y las usan tanto el serializador
como el formulario de la interfaz. Ver [[04-Arquitectura-y-ADR]].

## Requisitos de interfaz (R-UI)

| ID | Requisito | Estado |
|---|---|---|
| R-UI-01 | Tabla de exámenes con su número de preguntas | Completado |
| **R-UI-02** | **Tabla de preguntas**: id, examen, texto, nº de opciones, correcta, acciones | **Completado** — `web_views.py:109-151`, cubierto por `test_web_review.py::QuestionListingTests` |
| R-UI-03 | Tablas paginadas y navegables | Completado — `settings.PAGE_SIZE = 5`, **una sola constante** para API e interfaz |
| **R-UI-04** | **Filtro por examen y búsqueda por texto operables desde la pantalla, con URL compartible** | **Completado** — `web_views.py:120-134`; los filtros viajan en la URL |
| R-UI-05 | Alta/edición de pregunta con `formset` en línea, sin perder lo escrito | Completado |
| R-UI-06 | Confirmación antes de borrar | Completado |
| R-UI-07 | La UI respeta los roles | **Parcial**: hay un 403 global probado; falta la matriz completa por rol |
| R-UI-08 | Errores mostrados con plantillas propias | Completado |
| R-UI-09 | Estados vacíos | Completado |
| R-UI-10 | `base.html` + parcials + CSS propia, sin CDN | Completado |
| R-UI-11 | Accesibilidad en el CSS | **Parcial**: el contraste está revisado a ojo, sin herramienta |
| R-UI-12 | Funciona sin JavaScript | Completado |
| R-UI-13 | Pruebas de la interfaz | Completado (`test_web.py`, `test_web_review.py`, `test_web_gaps.py`) |
| R-UI-14 | Sin `django.contrib.admin` | Completado |

## Criterio de aceptación de la entrega

- [x] Las cuatro partes del laboratorio implementadas.
- [x] La interfaz gráfica existe y está verificada en vivo.
- [x] `python manage.py test` en verde: **365 pruebas**.
- [x] Cada requisito con un criterio comprobable (estado HTTP, clave del JSON, mensaje o conteo).
- [x] Se distingue **hecho / hipótesis / pendiente** en cada fila.
- [x] **No** se inventa ningún requisito del campus: el texto oficial de la rúbrica no está en el
      repositorio y se declara como tal.

## Preguntas que siguen abiertas

| ID | Pregunta |
|---|---|
| Q-01 | ¿Cuál es el texto oficial de la rúbrica? («tabla de API» = tabla documentada o tabla en pantalla). Se cubren **ambas** lecturas, pero no se puede cerrar sin el campus. |
| Q-04 | ¿`question_count` debe aparecer siempre, incluso en las respuestas de escritura? Hoy falta en 201/200. |
| Q-07 | ¿`Exam.title` debe ser único? Hoy se permiten títulos repetidos. |
| Q-08 | ¿Se mantiene `manage.py test` o se adopta `pytest`? El repositorio usa `manage.py test` y no ha cambiado. |

El detalle completo está en `docs/requisitos.md` §14 y `docs/trazabilidad.md`.