# Modelo de datos · revisión del especialista de bases de datos

- **Rol:** Especialista en bases de datos (`especialista-bd`)
- **Fase:** A/B — **solo análisis**. No se modificó `quiz/models.py` ni se creó ninguna migración.
- **Alcance:** `Exam → Question → Choice`, sus índices, el acceso a datos real de la API y de la
  interfaz prevista, y la invariante «exactamente una opción correcta».
- **Fecha:** 2026-10-16

## 0. Cómo se verificó (evidencia reproducible)

Todo lo que sigue como «comprobado» se obtuvo ejecutando, **fuera del repositorio**:

1. `makemigrations --check --dry-run` sobre el app `quiz` → `No changes detected in app 'quiz'`.
2. Las migraciones del proyecto aplicadas sobre una **base SQLite desechable en `%TEMP%`**
   (`INSTALLED_APPS` reducido a `auth`, `contenttypes`, `quiz`; `NAME` en una carpeta temporal),
   y lectura de `sqlite_master`, `PRAGMA foreign_keys`, `PRAGMA foreign_key_check`.
3. `EXPLAIN QUERY PLAN` de las consultas reales (`views.py:11`, `views.py:27-30`, filtro `search`)
   y de las que emite la paginación de DRF.
4. Contadores de consultas (`connection.queries_log`) con y sin `select_related`/`prefetch_related`.
5. Cronometraje con 4 000 preguntas / 8 000 opciones, con y sin índices temporales (creados y
   eliminados dentro de la base temporal).

**Limitación del entorno (no verificado):** en el intérprete por defecto de esta máquina
(`C:\Python314`) están `Django 5.2.18` y `requests`, pero **no** `djangorestframework` ni
`drf-spectacular`. Por eso **no** se pudo ejecutar `python manage.py test` ni cargar DRF. Todo lo
que dependa del comportamiento de DRF se marca explícitamente como *hipótesis*.

---

## 1. Diagrama de relaciones

```mermaid
erDiagram
    Exam ||--o{ Question : "questions (CASCADE)"
    Question ||--o{ Choice : "choices (CASCADE)"

    Exam {
        bigint id PK "BigAutoField / INTEGER PRIMARY KEY AUTOINCREMENT"
        varchar_120 title "NOT NULL"
        datetime created_at "auto_now_add, NOT NULL"
    }
    Question {
        bigint id PK
        bigint exam_id FK "-> exam.id, INDEX, CASCADE"
        text text "NOT NULL"
        datetime created_at "auto_now_add, NOT NULL"
        "Meta.ordering = [id]"
    }
    Choice {
        bigint id PK
        bigint question_id FK "-> question.id, INDEX, CASCADE"
        varchar_200 text "NOT NULL"
        bool is_correct "NOT NULL, default False"
        "Meta.ordering = [id]"
    }
```

En texto:

```
Exam 1 ──< N Question 1 ──< N Choice
      (FK exam_id)          (FK question_id)
      CASCADE               CASCADE
      related_name          related_name
      "questions"           "choices"
```

Cardinalidades: un examen tiene de 0 a N preguntas; una pregunta, de 0 a N opciones **según la
base de datos** (el mínimo de 2 solo lo impone la capa de aplicación, ver §6); una opción
pertenece exactamente a una pregunta (FK `NOT NULL`, sin `null=True` en ninguna parte).

Esquema real creado por la migración (extracto de `sqlite_master`, comprobado):

```sql
CREATE TABLE "quiz_exam"     ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
                              "title" varchar(120) NOT NULL, "created_at" datetime NOT NULL);
CREATE TABLE "quiz_question" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
                              "text" text NOT NULL, "created_at" datetime NOT NULL,
                              "exam_id" bigint NOT NULL REFERENCES "quiz_exam" ("id")
                                  DEFERRABLE INITIALLY DEFERRED);
CREATE TABLE "quiz_choice"   ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
                              "text" varchar(200) NOT NULL, "is_correct" bool NOT NULL,
                              "question_id" bigint NOT NULL REFERENCES "quiz_question" ("id")
                                  DEFERRABLE INITIALLY DEFERRED);
CREATE INDEX "quiz_question_exam_id_963bb8ea"     ON "quiz_question" ("exam_id");
CREATE INDEX "quiz_choice_question_id_6297ad3f"    ON "quiz_choice"   ("question_id");
PRAGMA foreign_keys = 1        -- Django activa la integridad referencial en SQLite
PRAGMA foreign_key_check = []  -- sin violaciones tras sembrar y borrar en cascada
```

---

## 2. Revisión del esquema

### 2.1 Claves primarias

- Las tres tablas usan `BigAutoField` (`DEFAULT_AUTO_FIELD`, `config/settings.py:41`), es decir
  `id` implícito `primary_key=True`. Simple, sin surrogates externos, sin claves naturales.
- Coherencia de tipos: Django declara `bigint`, pero en SQLite la columna se materializa como
  `integer PRIMARY KEY AUTOINCREMENT` (afinidad SQLite). Es inocuo en el laboratorio y **no**
  afecta a las migraciones: Django seguiría emitiendo `bigint` al migrar a PostgreSQL. Solo es un
  recordatorio de que el motor de desarrollo no es el de destino.
- `AUTOINCREMENT` garantiza que los ids no se reutilicen tras un borrado. Relevante porque la
  interfaz y los tests citan ids de preguntas en URLs y porque `ordering = ["id"]` se usa como
  orden estable de paginación.

### 2.2 Claves foráneas y `on_delete=CASCADE`

Las dos FK son correctas en tipo, nombre y `related_name`:

| FK | Tipo | `related_name` | Coherente con el uso |
|---|---|---|---|
| `Question.exam` | `ForeignKey(Exam)` | `questions` | `views.py:11` (`Count("questions")`), `seed_quiz.py:39` |
| `Choice.question` | `ForeignKey(Question)` | `choices` | `views.py:27` (`prefetch_related("choices")`), `serializers.py:50` |

Ambos `related_name` son correctos y **necesarios**: sin ellos Django crearía `question_set` /
`choice_set`. Además evitan el anti‑patrón `Choice.objects.filter(question__exam=...)` en la lista
de la interfaz.

**¿Es correcto `CASCADE` en toda la cadena para un laboratorio? Sí, y con argumentos a favor y
en contra.**

A favor (razones para mantenerlo):

1. **Es la regla del dominio:** un examen sin sus preguntas no es un examen; una pregunta sin sus
   opciones no es una pregunta. La dependencia es de existencia, no de referencia opcional.
2. **Es la regla del requisito:** RN-09 «el borrado en cascada `Exam → Question → Choice»»
   (`docs/requisitos.md:126`) y UC-11 «en cascada se van sus preguntas y opciones»
   (`docs/requisitos.md:100`). El comportamiento está especificado, no heredado por descuido.
3. **Coherencia con el permiso de borrado:** solo la persona puede borrar (`docs/requisitos.md:72`),
   y el borrado es un acto administrativo consciente. `PROTECT` o `SET_NULL` no aportan nada en un
   dominio sin versionado ni referencias externas.
4. **El laboratorio regenera los datos:** `seed_quiz` es idempotente (`helpers.seed()` lo llama en
   cada test), así que el borrado en cascada es reversible en la práctica.

En contra (riesgos asumidos):

- **Pérdida irreversible e inmediata.** `DELETE /api/exams/{id}/` borra N preguntas y N×M opciones
  en una sola transacción; no hay papelera, ni `deleted_at`, ni auditoría. En SQLite el único
  camino de recuperación es restaurar una copia del fichero.
- **La cascada no es transaccional por defecto en el ORM si se borra con `QuerySet.delete()`**
  fuera de `transaction.atomic()`: Django envuelve el borrado en cascada en su propia transacción,
  pero si el proceso muere a mitad puede quedar estado parcial. En este proyecto no es un problema
  real (`seed_quiz.handle` es atómico, ver §5).

Comprobado (base temporal): tras `Exam.objects.filter(title="A").delete()` con 22 preguntas y 44
opciones, quedan 0 preguntas y 0 opciones huérfanas; `Choice.objects.filter(question__isnull=True).count() == 0`.
`PRAGMA foreign_keys = 1` está activo (lo enciende Django en su backend SQLite), así que la cascada
no es solo de Python.

Alternativas descartadas para este alcance: `SET_NULL` en `Question.exam` dejaría preguntas
huérfanas que la API no sabría listar (`/api/questions/` sin filtro las mostraría sin examen);
`PROTECT` obligaría a un flujo de borrado en dos pasos que nadie ha pedido.

### 2.3 Normalización y redundancia

- **3NF, sin redundancia derivada persistida.** No hay columnas calculadas (`question_count` es
  una anotación, no una columna), ni copias de `Exam.title` dentro de `Question`, ni duplicación
  entre `Question.text` y `Choice.text`.
- **Grano correcto:** `Exam` (contenedor), `Question` (enunciado), `Choice` (opción). La tabla
  puente no hace falta: `Choice` **es** la entidad, no una relación entre dos.
- **No falta nada** para el alcance. Candidato descartado por sobre‑modelado:
  `Question.correct_choice` (FK a `Choice`) o `Question.correct_index`. Sería **denormalización con
  riesgo de incoherencia**: dos fuentes de verdad para «cuál es la correcta» (`is_correct` y el
  puntero) que se desincronizan en cuanto un `PATCH` reemplaza las opciones. El `is_correct` en
  `Choice` es la representación normalizada y no tiene duplicado. **No se recomienda.**
- **No sobra nada.** `created_at` en `Exam` y `Question` (y no en `Choice`) está justificado: es
  auditoría de cuándo se creó el agregado y el orden natural de las listas; en `Choice` sería ruido,
  porque su orden de aparición es el `id`.
- **Índice único sobre `Choice (question_id, text)`**: tempting pero **no recomendado**. Impediría
  opciones repetidas, que el requisito no prohíbe (RN‑01/RN‑02 hablan de cantidad y de
  correcciones, no de unicidad del texto). Añadiría una regla de negocio no pedida y una
  restricción que puede volver a rejectar peticiones antes aceptadas. Descartado.

**Discrepancia detectada (no es de esquema, pero nace de él):** `docs/requisitos.md:118` redacta
RN‑01 como «Una pregunta tiene **= 2** opciones», mientras el código exige `len(value) < 2 →
error` (`serializers.py:32`), es decir **≥ 2**. Los datos semilla tienen 4 opciones por pregunta
(`quiz/seed_data.py`), así que la redacción «= 2» es incorrecta y la código es el que manda.
Se pasa al Analista de requisitos para que ajuste RN‑01 a «≥ 2» y sus casos de aceptación.

---

## 3. Índices

### 3.1 Los que ya existen (comprobados en `sqlite_master`)

| Índice | Tipo | Columnas | Quién lo usa |
|---|---|---|---|
| `sqlite_autoindex_quiz_exam_1` / `_question_1` / `_choice_1` | implícito (PK) | `id` | Todas las consultas por clave; `ORDER BY id` de la paginación |
| `quiz_question_exam_id_963bb8ea` | B‑tree | `exam_id` | `filter(exam_id=…)` (`views.py:30`), `LEFT JOIN` de `Count("questions")` (`views.py:11`) |
| `quiz_choice_question_id_6297ad3f` | B‑tree | `question_id` | `prefetch_related("choices")`, `instance.choices.all().delete()` (`serializers.py:50`), cascada de Django |

Los dos índices de FK los crea Django automáticamente. **Cubren el 100 % de los filtros y de las
uniones del proyecto.** Evidencia de los planes:

```
QuestionViewSet con ?exam=1
  SEARCH quiz_exam USING INTEGER PRIMARY KEY (rowid=?)
  SEARCH quiz_question USING INDEX quiz_question_exam_id_963bb8ea (exam_id=?)   ← índice usado
prefetch de choices
  SEARCH quiz_choice USING INDEX quiz_choice_question_id_6297ad3f (question_id=?) ← índice usado
ExamViewSet.list
  SEARCH quiz_question USING COVERING INDEX quiz_question_exam_id_963bb8ea (exam_id=?) LEFT-JOIN
```

Que el `LEFT JOIN` del `Count` sea **covering** prueba que el índice de `exam_id` es exactamente el
que necesita esa consulta: no hay nada que optimizar ahí.

### 3.2 Candidatos evaluados y **descartados** (con coste/beneficio medido)

| Candidato | ¿Lo necesita alguna consulta real? | Medición (4 000 preguntas / 8 000 opciones, 100 repeticiones) | Veredicto |
|---|---|---|---|
| `Choice.is_correct` | **Ninguna.** La única forma de filtrar por él es siempre acompañada de `question_id`, y ese filtro ya usa `quiz_choice_question_id_...` | `filter(is_correct=True)[:5]`: **0,333 ms** sin índice → **0,317 ms** *con* índice temporal. Además, con índice, SQLite **sigue haciendo `SCAN`** (eligió el barrido por `ORDER BY id + LIMIT`) | ❌ No añadir. Ganancia = ruido, y el índice se escribiría en cada alta de opción sin ser consultado |
| `Question.text` (para `?search=`) | El filtro es `LIKE '%texto%'` (`SearchFilter` → `icontains`), con **wildcard delante**: un B‑tree de SQLite no puede servirlo | `icontains("ORM")[:5]`: **0,373 ms** → **0,378 ms** con índice; plan sigue siendo `SCAN quiz_question` | ❌ No añadir. Un índice solo sobre `text` no puede acelerar el `LIKE '%…%'`; para eso haría falta FTS5, fuera del alcance |
| `Exam.title` / `created_at` | **Ninguna consulta ordena ni filtra por ellos.** No hay `SearchFilter` en `ExamViewSet`; el orden es `order_by("id")` explícito | `order_by(created_at)` / `order_by(title)` → `SCAN` + `USE TEMP B-TREE` sobre 21 filas | ❌ No añadir. Índice «por si acaso» = coste de escritura y mantenimiento de migraciones sin ninguna consulta que lo aproveche |
| `Question.created_at` | Ninguna | `order_by("-created_at")` → `SCAN` + temp B‑tree | ❌ No añadir |
| Índice compuesto `(question_id, is_correct)` | Se pensaría para «dame la correcta de cada pregunta» de la tabla de la UI | `filter(question_id=7, is_correct=True)`: **0,349 ms**, y el plan es `SEARCH quiz_choice USING INDEX quiz_choice_question_id_6297ad3f (question_id=?)`: el índice de FK ya resuelve la consulta | ❌ No añadir. El índice existente basta; un compuesto solo aportaría cuando el plan tiene que leer `is_correct` desde la propia fila, ganancia despreciable a esta escala |
| Cambiar `Choice.Meta.ordering` a `["question", "id"]` | El `ORDER BY id` del `prefetch` genera `USE TEMP B-TREE FOR ORDER BY` | Con `order_by("question","id")` el temp B‑tree **desaparece** (medido) | ⚠️ No recomendado **ahora**: el beneficio es de microsegundos a 8 000 filas, y `Meta.ordering` está en el estado de la migración, así que cambiarlo **exige migración**. Coste alto, beneficio nulo |

### 3.3 Índice recomendado

**Para el alcance actual del laboratorio: ningún índice nuevo.** Los tres índices implícitos
cubren todas las consultas reales, y cada candidato alternative está o sin consulta que lo use o
medido sin ganancia.

La **única** adición que se propone —y no como índice de rendimiento, sino como **restricción de
integridad**— está en §6.3: un índice **único parcial** `UNIQUE (question_id) WHERE is_correct`.
Se deja como decisión del Arquitecto (ADR) y **no** se crea en esta fase.

### 3.4 Coste de escritura (para el Argumento coste/beneficio)

Con ~8 000 opciones, cada índice adicional paga: una escritura extra por `Choice` creado (y el
`update` de `serializers.py:50-51` borra y recrea 4 opciones por `PATCH`: ×5 filas), más una
migración que revisar y una copia de seguridad más grande. A cambio, el beneficio medido es
0,0–0,05 ms. Conclusión: en SQLite, con este volumen y estas consultas, **los índices solo se
justifican por integridad, nunca por rendimiento**.

---

## 4. Análisis de N+1

### 4.1 `QuestionViewSet`: correcto, 2 consultas constantes

Medido con `connection.queries_log` sobre 5 preguntas:

| Escenario | Consultas |
|---|---|
| `select_related("exam").prefetch_related("choices")` (`views.py:27`) | **2** (1 de preguntas + 1 de opciones) |
| Sin optimizar, accediendo a `question.choices` en bucle | **1 + N** (6 para 5 preguntas) |

- `select_related("exam")` es el correcto: es una FK (`forward`), se resuelve con un `JOIN`;
  plan comprobado → `INNER JOIN quiz_exam ... USING INTEGER PRIMARY KEY (rowid=?)`.
- `prefetch_related("choices")` es el correcto: es relación inversa 1→N; con `select_related` la
  tabla `quiz_choice` traería **8 000 filas** para 5 preguntas (multiplicación de filas) o
  necesitaría un `distinct` frágil. El `prefetch` hace una segunda consulta con
  `WHERE question_id IN (...)`.
- **La paginación no rompe nada:** DRF corta a 5 objetos *antes* de serializar, así que el
  `prefetch` se ejecuta **solo para los 5 de la página**. Es el orden correcto
  (paginar → después prefetch), y por eso el patrón actual debe preservarse tal cual.
- El serializer anida `choices = ChoiceSerializer(many=True)` (`serializers.py:24`), es decir lee
  `instance.choices.all()`, que es exactamente lo que el `prefetch` deja en caché. Sin
  `prefetch`, ese `choices.all()` por pregunta es el N+1 clásico. El código está bien alineado.

### 4.2 `ExamViewSet`: el `Count` no introduce N+1, y la paginación con `annotate` se comporta bien

- `annotate(question_count=Count("questions"))` es un **`JOIN` + `GROUP BY` en una sola consulta**,
  no una consulta por examen. Plan comprobado: `SCAN quiz_exam` +
  `SEARCH quiz_question USING COVERING INDEX ... LEFT-JOIN`. Con 21 exámenes y 4 000 preguntas:
  **0,97 ms**. No hay N+1 posible.
- Es `LEFT OUTER JOIN` + `COUNT(quiz_question.id)`, luego un examen **sin** preguntas cuenta `0`
  en lugar de desaparecer. Es la semántica correcta (un examen vacío es un examen vacío, y la UI
  lo muestra con `question_count = 0`).
- **La paginación con `annotate` + `Count` es correcta.** `PageNumberPagination.get_count()`
  llama a `queryset.count()`, y Django envuelve la consulta anotada en una subconsulta para
  contar **grupos**, no filas:
  ```sql
  SELECT COUNT(*) FROM (
    SELECT quiz_exam.id AS col1 FROM quiz_exam
    LEFT OUTER JOIN quiz_question ON (quiz_exam.id = quiz_question.exam_id)
    GROUP BY 1
  ) subquery
  ```
  Devolvió `2` con 2 exámenes y 4 000 preguntas (contó exámenes, no preguntas). Sin ese
  envoltorio, un `COUNT(*)` directo habría devuelto el número de filas unidas. **No hay que tocar
  nada.**
- Detalle menor, sin impacto: la anotación obliga a `GROUP BY` sobre las 3 columnas de `quiz_exam`,
  y SQLite resuelve el `ORDER BY quiz_exam.id` con un `USE TEMP B-TREE FOR ORDER BY`. A 21
  exámenes es ruido; y aunque no lo fuera, el plan elegido (recorrer exámenes y buscar preguntas
  por el índice) es el adecuado para «todos los exámenes con su contador».

### 4.3 Hallazgo colateral: `question_count` no existe en la instancia recién creada

Comprobado: tras `Exam.objects.create(title="x")`, `getattr(exam, "question_count")` **devuelve
`AttributeError` (ausente)**. Las anotaciones son del *queryset*, no del modelo: una instancia
creada por el serializer no lleva el atributo.

- **Lectura (`GET /api/exams/` y `GET /api/exams/{id}/`)**: no hay problema, porque el objeto sale
  del queryset anotado.
- **Escritura (`POST /api/exams/`, `PUT`/`PATCH`)**: *hipótesis* — DRF no encuentra el atributo y
  el campo `question_count = IntegerField(read_only=True)` (`serializers.py:14`), sin `default`,
  se **omite** del cuerpo de la respuesta (`SkipField`), en lugar de devolver `0`. No es un 500,
  pero la respuesta de creación **no traería `question_count`**, cosa que el contrato de UC‑01/F4
  no cubre para escrituras. *No verificado* (falta DRF en este entorno).

**Mitigación sin migración y sin tocar modelos**, para cuando `backend-django` implemente ADR‑0002:
usar un `SerializerMethodField` (`def get_question_count(self, obj): return getattr(obj, "question_count", 0)`).
Es una decisión de serializadores, no de esquema: **se pasa al Arquitecto**, no se implementa aquí.

### 4.4 Recomendación de prueba (sin migración, sin cambio de modelo)

`docs/trazabilidad.md:114` deja R‑VIE‑11 como «🟡 parcial: falta `assertNumQueries`». Cerrarlo es
lo más barato que hay y blinda el patrón:

```python
def test_questions_list_does_two_queries(self):
    with self.assertNumQueries(3):          # 2 del listado + 1 del COUNT del paginador
        self.client.get("/api/exams/…")    # o /api/questions/?exam=1
```

Recomendación: fijar el número **con** `select_related`/`prefetch_related` (contrato del módulo
`queries.py` que el ADR‑0002 prevé) para que cualquier regresión a N+1 falle la suite.

---

## 5. Transacciones y consistencia

### 5.1 Lo que está bien hecho (validado)

- `QuestionSerializer.create` (`serializers.py:38-43`): crea la pregunta y sus opciones dentro de
  `transaction.atomic()` + `bulk_create`. **Correcto**: o se guarda la pregunta con sus opciones, o
  no se guarda nada.
- `QuestionSerializer.update` (`serializers.py:45-51`): borra y recrea las opciones **dentro** de
  la misma transacción. **Correcto**: nunca hay una ventana con cero opciones
  (salvo el instante lógico dentro de la transacción, que es invisible para otras conexiones).
- `seed_quiz.Command.handle` decorado con `@transaction.atomic` (`seed_quiz.py:33-34`): la carga
  completa es todo‑o‑nada. El comentario `# cascades to questions and choices`
  (`seed_quiz.py:35`) deja constancia de que la cascada es intencionada.
- **Rollback verificado** en base temporal: forzando un fallo a mitad del `update`, la
  transacción revierte y la pregunta conserva sus 2 opciones anteriores con exactamente 1
  correcta. Es el comportamiento correcto.

### 5.2 La brecha: la invariante vive en el transporte, no en el dominio

**Comprobado en base temporal**, con el esquema tal como está:

| Operación | ¿La acepta la base de datos? |
|---|---|
| `Question.objects.create(...)` **sin ninguna opción** | **Sí**, se guarda (`id` devuelto) |
| Pregunta con **2 opciones correctas** (`bulk_create`) | **Sí**, se guardan las dos |
| `question.full_clean()` sobre esa pregunta de 2 correctas | **No lanza nada**: `Model.clean()` no existe y las opciones son filas de otra tabla |

Vías por las que se puede saltarse la regla en el estado actual del repositorio:

| Vía | ¿Existe hoy? |
|---|---|
| API REST (`POST`/`PUT`/`PATCH`) | **No** — pasa por `validate_choices` |
| `seed_quiz` | **No** — los datos de `seed_data.py` cumplen la regla (4 opciones, 1 correcta) |
| `quizctl.py` / `agent/` | **No** — hablan HTTP contra la API |
| **Django admin** | **No existe**: no hay `quiz/admin.py` y `django.contrib.admin` **no** está en `INSTALLED_APPS` (`settings.py:13-20`). No hay formulario de admin que permita insertar datos saltándose el serializer |
| **`python manage.py shell` / código propio con el ORM** | **Sí** — esta es la brecha real |
| **Interfaz web (futura)** | Depende: ADR‑0002 exige que pase por `services.py`, y el formset debe validar (§6.2) |

**Conclusión: la brecha es real pero hoy solo la alcanza quien ya tiene acceso al intérprete y al
fichero SQLite.** Para un laboratorio headless, con autenticación por token, dos usuarios fijos y
un seed reejecutable, esto es **un coste aceptado, no un agujero de seguridad**. No lo es en un
sistema donde el contenido lo escriban terceros.

### 5.3 Un matiz que conviene no pasar por alto

`bulk_create` **no llama a `save()`**: se salta señales, `save()` y `full_clean()`. Esto significa
que cualquier validación que en el futuro se ponga en `Choice.save()` o en señales
(`post_save`) **no se ejecutará** en las dos rutas de escritura reales. Es un argumento a favor de
que la invariante se escriba en un servicio explícito y no en señales, y también a favor de dejar
escrito este documento (§7).

---

## 6. «Exactamente una opción correcta»: qué se puede hacer y qué se recomienda

### 6.1 Opción A — `CHECK` en la base de datos: **no es viable**

- `CHECK` es una restricción **de fila**: no puede leer otras filas. «Hay exactamente una opción
  correcta» es un agregado sobre filas de `quiz_choice` agrupadas por `question_id`.
- Comprobado en SQLite: `CHECK` con subconsulta →
  `OperationalError: subqueries prohibited in CHECK constraints`.
- Un `models.CheckConstraint` de Django tampoco puede referenciar otras tablas.
- **Descartada por imposible, no por inconvenientemente.**

### 6.2 Opción B — `Model.clean()` al estilo del proyecto de referencia

- En el proyecto de referencia (`dae-s07-orm-con-ia/blog/models.py:128-131`) `Comment.clean()`
  valida el texto. Es un patrón correcto **para una regla de la propia fila**.
- Pero aquí hay dos límites:
  1. **`clean()` no se ejecuta solo.** `save()` **no** llama a `full_clean()`; hay que llamarlo
     explícitamente. Comprobado: `question.full_clean()` sobre una pregunta con 2 opciones
     correctas **no lanza error** (aunque se añadiera el `clean()`, sin `full_clean()` nadie lo
     llama).
  2. **La invariante es de otra tabla.** Las opciones de una pregunta son filas hijas; en el
     momento de validar un `PATCH` pueden estar en memoria, no en la base, y `delete() +
     bulk_create()` occur dentro de una transacción. Un `Question.clean()` tendría que duplicar el
     `question_rules()` ya previsto, y aun así no cubriría `bulk_create`.
- **Veredicto: `clean()` no es una garantía de integridad.** Es útil como defensa adicional en las
  rutas que llaman `full_clean()` (los `ModelForm` de la interfaz con `inlineformset_factory` los
  llaman, y por esoADR‑0002 manda que el formset valide), pero **no sustituye** al servicio.

### 6.3 Opción C — Índice **único parcial**: viable, y es lo único que la BD puede expresar

Es la única parte de la invariante que la base de datos puede imponer. **Comprobado** en SQLite:

```sql
CREATE UNIQUE INDEX "one_correct_per_question"
    ON "quiz_choice" ("question_id") WHERE "is_correct";
```

| Prueba | Resultado |
|---|---|
| 1 correcta + 1 incorrecta | aceptada |
| **2 correctas en la misma pregunta** | **`IntegrityError: UNIQUE constraint failed: quiz_choice.question_id`** |
| 2 incorrectas (ninguna correcta) | aceptada → **no** cubre «al menos una» |
| Pregunta con 0 opciones | aceptada → **no** cubre «al menos 2 opciones» |
| Flujo `update` (`delete()` + `bulk_create()` dentro de `atomic`) | **funciona** (compatible) |
| `IntegrityError` a mitad del `atomic` | **rollback correcto**, opciones previas intactas |
| Crear el índice sobre datos ya sucios | **falla** (`IntegrityError`): exige auditar antes |
| Django lo expresa nativamente | Sí: `UniqueConstraint(fields=["question"], condition=Q(is_correct=True), name=...)`; SQLite soporta índices parciales. En Django eso es `AddConstraint`, o sea **una migración** |

**Coste y riesgo:** (a) exige migración y una auditoría previa de datos; (b) cambia la superficie
de error: si una petición llegara con 2 correctas saltándose el serializer, el usuario recibiría un
**500** en vez del 400 con el mensaje en español, salvo que `services.py` traduzca ese
`IntegrityError` al mismo mensaje (lo cual es deseable, pero es código nuevo que probar);
(c) cubre **la mitad** de la invariante, lo que puede dar una **falsa sensación** de garantía.

### 6.4 Recomendación concreta

**Para el alcance del laboratorio (fases A/B/C): la invariante se queda en la capa de dominio, en
`services.question_rules()`, tal y como ya decidió el ADR-0002. No se crea ninguna migración ni se
toca `models.py`.**

Concretamente:

1. **Una sola implementación** de la invariante en `quiz/services.py` (`question_rules`), llamada
   por `QuestionSerializer.validate_choices`, por el formset de la UI y por los servicios de
   escritura. Es exactamente lo que ya aprobó ADR‑0002; desde la perspectiva de datos, es la
   decisión correcta porque **la invariante es de dominio, no de almacenamiento**.
2. **Añadir `Question.clean()`** que delega en `question_rules()` **no es necesario para el
   objetivo**, y se desaconseja: no se ejecutaría en ninguna de las dos rutas de escritura reales
   (`bulk_create`), y daría la impresión de una garantía que no existe. Si más tarde se quiere la
   redecencia del proyecto de referencia, que sea `QuestionForm.clean()` en la interfaz (donde sí
   se llama) y no `Model.clean()`.
3. **Cerrar la brecha de forma barata y verificable, sin migración**, con dos pruebas en
   `quiz/tests/test_services.py`:
   - una que fije que `question_rules` rechaza 0 correctas, 2 correctas y 1 sola opción;
   - una que afirme que **serializer y formset** coinciden (ya pedida por ADR‑0002, punto 2 de
     «Verificación»).
4. **Dejar el índice único parcial como endurecimiento opcional (fase posterior, con ADR).** Si el
   campus lo pide o si el contenido pasa a ser escrito por terceros, la secuencia correcta es:
   1. consulta de auditoría que liste preguntas con 0 o ≥2 correctas (debe salir vacía);
   2. migración `AddConstraint` con `UniqueConstraint(fields=["question"], condition=Q(is_correct=True))`;
   3. `services.py` captura `IntegrityError` y devuelve el **mismo** 400 en español (el contrato
      de `test_api.py:52-58` no cambia: ese caso se rechaza antes de llegar a la base);
   4. prueba de regresión con `IntegrityError` simulado.
   Con eso, la BD garantiza «como máximo una correcta» y el dominio garantiza el resto. **Ni
   `CHECK` ni nada que dependa de disparadores** (SQLite no los tiene y no hay soporte en Django).

---

## 7. Estado de la migración y otros hechos verificados

### 7.1 `0001_initial.py` es coherente con `models.py`

- `makemigrations --check --dry-run` → **`No changes detected in app 'quiz'`**. No hay cambios
  pendientes: el modelo y la migración están sincronizados.
- Campo a campo, la migración declara exactamente los tres modelos, con `BigAutoField`,
  `auto_now_add`, `CASCADE`, `related_name` y `options={'ordering': ['id']}` en `Question` y
  `Choice`, tal como `quiz/models.py:4-33`.
- Imposible que esté desfasada por algo que no se migra: `Meta.ordering` sí está en el estado de
  las migraciones (líneas 31-33 y 43-45), así que un cambio futuro de orden **exigirá** migración
  (relevante para §3.2, última fila).
- **Observación cosmética:** el encabezado dice `Generated by Django 6.1.2` y la máquina tiene
  `Django 5.2.18` (`requirements.txt` fija `Django>=5.2,<7`). El contenido de la migración es
  válido en ambas versiones; solo es ruido del entorno que generó el archivo. No requiere acción.

### 7.2 Efectos del borrado en cascada: documentados y aceptados

- **Sí están documentados**: RN‑09 en `docs/requisitos.md:126` y UC‑11 en
  `docs/requisitos.md:100` («en cascada se van sus preguntas y opciones»), más el comentario en
  `seed_quiz.py:35`.
- **Lo que no estaba escrito en ninguna parte, y este documento deja constancia de:**
  `DELETE /api/exams/{id}/` es **irreversible** y borra en la misma operación N preguntas y sus
  opciones. Recuperación: solo restaurar una copia de `db.sqlite3` (que está ignorada por git y,
  por tanto, **no está en el repositorio**: no hay copia de seguridad en el control de versiones).
- **Aceptado para el laboratorio** porque: (a) el requisito lo pide explícitamente; (b) solo la
  persona puede borrarlo (`docs/requisitos.md:72`); (c) `seed_quiz` regenera el catálogo completo;
  (d) el volumen es de 2 exámenes y 8 preguntas.
- **Acción recomendada, no bloqueante:** una línea en el README del laboratorio («borrar un
  examen borra también sus preguntas y opciones; no hay forma de recuperarlas desde la
  aplicación») y, si la interfaz web muestra la acción, un texto de confirmación que lo diga. Se
  pasa al Documentador y a `backend-django`; aquí no se toca código.

### 7.3 Otras comprobaciones

- `PRAGMA foreign_key_check` vacío tras sembrar y tras borrar en cascada: no hay referencias
  colgantes.
- `bulk_create` de `choices` (`serializers.py:42`, `:51`, `seed_quiz.py:40`) se apoya en el
  índice de `question_id`: es la forma más rápida de insertar las opciones y no requiere ids
  previos. Correcto tal como está.
- Sin índices «por si acaso», sin campos de auditoría innecesarios y sin `unique=True` no
  justificados: el esquema es **más pequeño** de lo que suele ser un diseño de producción, y eso
  es lo adecuado aquí.

---

## 8. Resumen de decisiones y pendientes

| # | Decisión | Estado | Quién decide |
|---|---|---|---|
| D‑1 | `CASCADE` en toda la cadena | **Se mantiene** (RN‑09) | Arquitecto (ratifica) |
| D‑2 | **Ningún índice de rendimiento nuevo** | **Recomendado** para el alcance | `especialista-bd` → Arquitecto ratifica |
| D‑3 | Invariante «exactamente una correcta» en `services.question_rules()` (ADR‑0002), **sin migración** | **Recomendado** | Arquitecto (ya aceptado en ADR‑0002) |
| D‑4 | Índice único parcial `UNIQUE(question_id) WHERE is_correct` como endurecimiento **opcional** | **No en esta fase**; requiere ADR + auditoría de datos + traducción de `IntegrityError` a 400 | Arquitecto |
| D‑5 | Sin `Model.clean()` para la invariante | **Desaconsejado** (no se ejecuta en `bulk_create`) | `especialista-bd` |
| P‑1 | `question_count` ausente en la respuesta de `POST/PUT /api/exams/` (*hipótesis*, falta DRF) | Pendiente de verificar; candidato: `SerializerMethodField` | `backend-django` / Arquitecto |
| P‑2 | RN‑01 redactada como «= 2 opciones» cuando el código exige «≥ 2» | Corrección de requisito | Analista de requisitos |
| P‑3 | Prueba `assertNumQueries` para fijar el contrato de consultas (R‑VIE‑11) | Pendiente, sin migración | `tester` |
| P‑4 | Aviso de irreversibilidad del borrado en cascada en README/UI | Pendiente | Documentador / `backend-django` |
| P‑5 | `python manage.py test` no se pudo ejecutar aquí (falta `djangorestframework` en el intérprete por defecto) | **No verificado** | `tester`, en el entorno correcto |

---

```
Rol: especialista-bd
Tarea: revisión del esquema `Exam -> Question -> Choice` (Fase A/B, solo análisis)
Estado: completado (análisis) · P‑1 y P‑5 marcados como no verificados por entorno
Hallazgos:
  - `makemigrations --check --dry-run` → sin cambios: 0001_initial.py es coherente con models.py
  - Los 2 índices de FK de Django cubren el 100 % de las consultas reales (planes comprobados)
  - `QuestionViewSet`: 2 consultas constantes con select_related+prefetch_related (vs 1+N sin optimizar)
  - `annotate(Count)` + paginación: correcta; `count()` cuenta subconsulta agrupada (2, no 4000)
  - La BD acepta preguntas con 0 opciones y con 2 correctas; `full_clean()` no lo detecta
  - CHECK con subconsulta: imposible en SQLite; índice único parcial: viable y probado (cubre solo "como máximo una")
  - Medido: índice en `is_correct` o en `text` no mejora nada (0,333→0,317 ms; 0,373→0,378 ms)
Decisiones/Riesgos:
  - D‑2 sin índices nuevos; D‑3 invariante en el dominio; D‑4 índice parcial solo con ADR
  - Riesgo asumido: la brecha de integridad solo la alcanza quien tiene el intérprete y el SQLite
Siguiente: arquitecto (ratificar D‑1..D‑5 y P‑1), analista-requisitos (P‑2),
  tester (P‑3, P‑5), backend-django (P‑4)
```