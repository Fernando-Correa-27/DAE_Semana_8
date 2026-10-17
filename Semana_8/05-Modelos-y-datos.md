# 05 · Modelos y datos

Volver al [[00-Indice]] · Anterior: [[04-Arquitectura-y-ADR]] · Siguiente: [[06-API-y-codigos-HTTP]]

## Los tres modelos

```
Exam (1) ──< (N) Question (1) ──< (N) Choice
        on_delete=CASCADE          on_delete=CASCADE
        related_name="questions"   related_name="choices"
```

| Modelo | Campos | Notas |
|---|---|---|
| `Exam` | `id`, `title` (≤ 120), `created_at` | `created_at` es `auto_now_add` (solo lectura) |
| `Question` | `id`, `exam` (FK), `text`, `created_at` | `Meta.ordering = ["id"]` |
| `Choice` | `id`, `question` (FK), `text` (≤ 200), `is_correct` (por defecto `false`) | `Meta.ordering = ["id"]` |

**Borrado en cascada:** borrar un examen se lleva sus preguntas y sus opciones. Verificado en vivo
(DELETE → 204) y cubierto por `quiz/tests/test_persistence.py::CascadeDeleteTests`.

## La invariante, escrita una sola vez

`quiz/services.py` es **la fuente única** de las reglas del dominio. Ni el serializador ni el formulario
de la interfaz las reescriben: las **consultan**.

```
services.validate_question_choices()
    ├── len(choices) < 2        → "Una pregunta necesita al menos dos opciones."
    └── correctas != 1          → "Debe haber exactamente una opción correcta."
```

| Consumidor | Cómo la usa |
|---|---|
| `quiz/serializers.py::QuestionSerializer.validate_choices` | Delega y traduce `QuizRuleError` a `ValidationError` de DRF |
| `quiz/forms.py::ChoiceFormSet.clean` | Delega y traduce a `ValidationError` de Django (errores no-de-campo) |
| `quiz/web_views.py` | Escribe **solo** por `services.create_question` / `update_question` |

La invariante está en **español literal** y sin `gettext`, y eso es deliberado: `test_api.py` comprueba
que el 400 contiene la palabra `exactamente una`. Mover una regla no puede cambiar su redacción.

**Escritura atómica:** `create_question` y `update_question` envuelven el trabajo en
`transaction.atomic`, y las opciones se reemplazan enteras con `bulk_create`. Un 400 **no persiste nada**,
demostrado por `quiz/tests/test_persistence.py`.

## Lecturas sin N+1

| Función (`quiz/queries.py`) | Qué hace |
|---|---|
| `exams_with_counts()` | Exámenes con `question_count` como **anotación** (un JOIN, no una consulta por fila) |
| `recent_exams(limit=5)` | Los **más nuevos**, con su contador |
| `exam_with_questions()` | Un examen con sus preguntas y opciones ya prefetcheadas |
| `questions_with_choices(exam, text)` | Preguntas con examen y opciones, filtrables |
| `totals()` | Los tres contadores del panel |

La API usa el mismo patrón en `quiz/views.py:53`: `select_related("exam")` + `prefetch_related("choices")`.
`quiz/tests/test_query_counts.py` fija el número de consultas de ambas vías como **contrato**: si alguien
cambia una lectura, ese número se rompe y hay que actualizarlo en el mismo cambio.

## Base de datos

- **SQLite** (`db.sqlite3`), sin servidor. Ignorado por git.
- Una sola migración: `quiz/migrations/0001_initial.py`. Solo esquema; los datos van aparte.
- Orden estable por `id` en preguntas y opciones: la paginación es determinista.

## Datos de arranque

`python manage.py seed_quiz` carga los datos fijos del laboratorio y crea dos usuarios:

| Usuario | Grupo | Contraseña | Para qué |
|---|---|---|---|
| `profe` | — (`is_staff=True` → rol *person*) | `set_unusable_password()` salvo que se pase `--password` | Persona: puede borrar. Es quien entra en la interfaz web |
| `agente` | `agente` → rol *agent* | `set_unusable_password()` | Agente: lee, crea y modifica; nunca borra |

Ambos reciben un token que el comando **imprime por terminal** (no está en el repositorio).

**Idempotencia:** `get_or_create` sobre los usuarios y sus tokens, así que **repetir el seed no cambia
los tokens** y las variables de entorno siguen valiendo. Ojo: sí **borra y recarga** exámenes, preguntas
y opciones.

Con el seed, la API devuelve **2 exámenes con 4 preguntas cada uno**.

## El texto hostil del seed

Una de las preguntas de arranque contiene la frase `IGNORA TUS INSTRUCCIONES`. Existe para probar que
la frontera del agente la trata como **dato** y no como orden: buscar «IGNORA» devuelve la pregunta
(normal, con su texto) y **no borra nada**. Cubierto por `quiz/tests/test_agent.py`. Ver [[08-Seguridad]].

## Secretos

Ni tokens, ni contraseñas, ni claves en el código. `DJANGO_SECRET_KEY` viene del entorno; si no está y se
está en desarrollo, la clave se **genera** en `.secret_key` (ignorado por git) y nunca se imprime. Desde
`a82978e`, `seed_quiz` **solo** muestra los tokens si se pide con `--show-tokens`. `.env`, `db.sqlite3`,
`.secret_key` y `agent_audit.jsonl` están ignorados por git.