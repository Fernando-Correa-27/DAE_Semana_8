# Revisión de código - interfaz web + Partes 2 y 3 del laboratorio

- **Revisor:** Agente `revisor-codigo`
- **Alcance:** `cf61a11` (Partes 2 y 3) y `7c87fd9` (interfaz web), más el estado actual del repositorio
- **Fecha:** 2026-10-16
- **Runner:** `python manage.py test` (no hay linter instalado en el entorno: no existe `flake8`, `ruff` ni `pycodestyle`)

---

## Veredicto

**CAMBIOS** — 1 bloqueante, 9 importantes, 20 menores.

El trabajo es sólido en lo esencial: la invariante de la pregunta es efectivamente **una sola**
(vér sección 2), no hay ni un `|safe` ni `mark_safe` en todo el proyecto, las excepciones son
específicas y encadenadas con `from exc`, `settings.py` solo **añade** (el bloque `REST_FRAMEWORK`
queda intacto), no se toca `quiz/views.py` ni el router, y el contrato OpenAPI no se degrada
(`test_api.py` sigue sin modificarse). El problema de fondo es otro: **la tabla de roles está
duplicada** en `web_mixins.py`, lo que contradice una prohibición explícita de ADR-0002 y
ADR-0003; y hay tres pruebas que los propios ADR declaraban obligatorias y que no existen.

---

## 1. Resumen de lo revisado

| Área | Veredicto |
|---|---|
| Legibilidad y convenciones (PEP 8, nombres en inglés) | Bien. Código, nombres y comentarios en inglés; mensajes de usuario en español, coherente con RN-08 y con el texto idéntico que exige ADR-0002 |
| Modularidad | Bien. `services`, `queries`, `forms`, `web_views`, `web_mixins` y `web_urls` están bien acotados; ninguna vista supera 60 líneas (riesgo R-E del arquitecto respetado) |
| Duplicación | **Dos duplicaciones reales**: la regla de roles (bloqueante B1) y las lecturas (`views.py` frente a `queries.py`, I3) |
| Excepciones y validaciones | Sin `except` amplio en ningún sitio. `QuizRuleError` se traduce con `from exc` en `forms.py:136` y `serializers.py:35`. Correcto |
| Separación de responsabilidades | Correcta: `web_views` no contiene reglas de negocio y `queries` solo lee. Salvedad I3 |
| Plantillas y accesibilidad | Realmente operativa (skip-link, `label for`, `aria-describedby`, `role=alert`, foco visible, radios con `name` común sin JavaScript). Defectos reales: I1 (doble anuncio) e I2 (el radio pierde la marca) |
| CSS | Tokens semánticos usados de verdad: ningún color literal fuera de `:root` (excepción justificada en `500.html`). `prefers-reduced-motion` y responsive presentes. 627 líneas razonables. Salvedades menores en m11 |
| Seguridad | Sin XSS, CSRF obligatorio en la UI, frontera token/sesión intacta y probada. Sin hallazgos cráticos |
| Rendimiento | Sin N+1 (medido: 3 consultas constantes en el detalle, 1 en la lista) |
| Decisiones del arquitecto | ADR-0002 y ADR-0003 incumplidos en un punto (B1) y en un punto de verificación (I5, I6); desviaciones de documento sin registrar (I7, I8, m17) |
| Rúbrica | Tres criterios sólidos; el criterio 4 está en riesgo por el README desactualizado (I9) y por dos pantallas declaradas y no decididas (I7) |

---

## 2. Preguntas concretas del encargo

### 2.1. `quiz/services.py` es la fuente única de la invariante?

**Sí, verificado.** Búsqueda de los dos textos de negocio en todo el código:

- `quiz/services.py:76` y `quiz/services.py:78` son los únicos lugares que contienen
  `cal menos dos opciones` y `Debe haber exactamente una opción correcta`.
- `quiz/serializers.py:31-35` y `quiz/forms.py:129-136` **delegan**; ninguna reescribe la regla.

Por tanto **no hay una segunda copia de la regla en `forms.py`**. Además, `forms.py:146`
desactiva `validate_min` con un comentario que explica por qué (la redacción es del servicio):
bien resuelto.

Matiz menor: el número `2` aparece también como `min_num=2` en `forms.py:145`, fuera de
`services.MIN_CHOICES`. No es una copia de la regla (no produce el mensaje), pero es una constante
mágica que puede divergir sin que nadie lo note (m1).

### 2.2. La tabla de permisos está duplicada entre `services.py` y `web_mixins.py`?

**Sí, y es el hallazgo bloqueante (B1).** `quiz/web_mixins.py:22` decide el rol con
`not user.is_staff`, es decir, **fuera** de `services.METHODS_BY_ROLE`. No es una copia textual,
pero es una segunda *decisión* con dos divergencias reales:

| Caso | `services.role_of` (API) | `web_mixins` (UI) |
|---|---|---|
| `is_superuser=True` con `is_staff=False` | `person` (puede borrar) | 403 |
| Agente o lector en el futuro | tabla compartida | 403 fijo, sin consultar la tabla |

Los tres documentos lo prohíben por escrito: `docs/adr/0002-consumicion-del-dominio-desde-la-interfaz.md:117-119`,
`docs/arquitectura.md:145-148` (nunca decide permisos con `if user.is_staff:`, llama a
`quiz.permissions.may()`) y ADR-0003 :97-98, que exige un mixin que llame `may(user, action)`.

Además, ADR-0003 :110-116 pide que la plantilla **refleje** la misma regla; hoy no hay ninguna
consulta de rol en las plantillas. Es inocuo porque el mixin es más restrictivo, pero la
garantía de R-UI-07 (`docs/requisitos.md:364`) se cumple por casualidad, no por construcción.

### 2.3. `web_views.py` mezcla presentación y lógica de negocio?

**No.** Las vistas solo orquestan: `web_views.py:151-161` y `:183-195` delegan la escritura en
`services.create_question` y `update_question`, y la lectura en `queries`. La comprobación de
ADR-0002 :164 (ni `objects.create(` ni `.save()` sobre `Question`/`Choice` en `web_views.py`)
**no encuentra nada**. Los `form.save()` que sí hay son los de `ExamCreateView` y `ExamUpdateView`,
que la ADR solo prohíbe para `Question`/`Choice`.

### 2.4. `queries.py` está bien acotado?

**Módulo bien acotado, pero no es lo que la ADR dice que sea.** Su docstring
(`quiz/queries.py:3-5`) afirma Both presentations ask this module for data: **es falso**.
`quiz/views.py:11` y `quiz/views.py:26-31` siguen construyendo sus propias consultas. Ver I3.

---

## 3. Hallazgos

### BLOQUEANTE

#### B1. La regla de roles de la UI se reimplementa fuera de la tabla compartida

- **Archivo:línea:** `quiz/web_mixins.py:20-24` (en contraste con `quiz/services.py:39-47`)
- **Qué falla:** `StaffRequiredMixin.dispatch` decide con `if user.is_authenticated and not user.is_staff: raise PermissionDenied(...)`. Es exactamente el `if user.is_staff:` suelto que **prohíben** ADR-0002 :117-119, ADR-0003 :97-98 y `docs/arquitectura.md:145-148`.
- **Por qué importa:** (a) incumple un ADR aceptado, y `AGENTS.md` 6.3 exige escalar antes de integrar; (b) el mismo concepto quién es la persona queda decidido en dos sitios que ya divergen: un `is_superuser` sin `is_staff` puede borrar por API y recibe 403 por UI; (c) si mañana la UI se abre al agente o a un rol nuevo, hay que tocar dos sitios, y ese es justo el escenario en el que un `DELETE` se cuela, que es el agujero que la Parte 3 cierra.
- **Corrección propuesta:** añadir en `quiz/services.py` el adaptador de una línea que falta y usarlo en el mixin:
  ```python
  # quiz/services.py
  def may_use(user, method: str) -> bool:
      """May this user perform this HTTP method? One question for both interfaces."""
      return may(role_of(user), method)
  ```
  ```python
  # quiz/web_mixins.py
  from . import services

  def dispatch(self, request, *args, **kwargs):
      if not request.user.is_authenticated:
          return super().dispatch(request, *args, **kwargs)   # LoginRequiredMixin -> 302
      if not services.may_use(request.user, request.method):
          raise PermissionDenied("Esta interfaz es para el profesorado.")
      return super().dispatch(request, *args, **kwargs)
  ```
  Se mantienen el 302 del anónimo y el 403 del autenticado (lo que ya verifican `test_web.py:51-67`)
  y desaparece la copia. Si el arquitecto quiere que la UI distinga acciones y no solo rol, el mismo
  `may_use` resuelve GET/POST/PUT/PATCH/DELETE sin cambiar la semántica actual.

### IMPORTANTES

#### I1. El mismo error de negocio se muestra dos veces, en dos regiones `role="alert"`

- **Archivo:línea:** `quiz/templates/quiz/question_form.html:35-39` duplica `quiz/templates/quiz/partials/_error_summary.html:24`; además los dos objetivos llevan `role="alert"` (`question_form.html:36` y `_error_summary.html:15`).
- **Evidencia:** con un POST de tres opciones y ninguna marcada como correcta, el HTML devuelto contiene el texto dos veces y dos `role="alert"`:
  ```
  occurrences of invariant wording: 2
  role=alert count: 2
  CONTEXT: ... <ul class="error-summary__list"> <li>Debe haber exactamente una opción correcta.</li>
  CONTEXT: ... <ul class="error-summary__list" role="alert"> <li>Debe haber exactamente una opción correcta.</li>
  ```
- **Por qué importa:** un lector de pantalla anuncia el mismo error dos veces al cargar la página, y en R-UI-08 y R-UI-11 la accesibilidad es criterio de corrección, no un extra.
- **Corrección:** dejar el mensaje **solo** en el resumen (`_error_summary.html`) y, si se quiere cerca del fieldset, referenciarlo sin duplicarlo: poner `id` al mensaje del fieldset y enlazarlo con `aria-describedby` desde el `legend` o desde el texto de ayuda. Con una sola región `role="alert"`.

#### I2. Al volver con errores se pierde cuál opción estaba marcada como correcta

- **Archivo:línea:** `quiz/forms.py:65-77` (widget) y `quiz/forms.py:106-127` (formset). El POST nunca manda `choices-N-is_correct` porque el radio usa `name="choices-correct"` con el índice como `value` (`quiz/templates/quiz/widgets/correct_choice.html:1-3`).
- **Qué falla:** al ser un formset *bound*, `is_correct` se rellena desde `choices-N-is_correct`, que no viaja; por eso no queda ningún radio marcado aunque la persona hubiera elegido uno. El texto de las opciones sí se conserva (`filled_choices` descarta solo las vacías).
- **Evidencia:** POST con `choices-correct=2` y un campo inválido en el formulario principal:
  ```
  status: 200
  radio checked after invalid POST: []
  rows kept (text values): ['A', 'B', 'C']
  ```
- **Por qué importa:** `docs/requisitos.md:362` (R-UI-05) exige que el error se muestre sin perder lo ya escrito. El radio es parte de lo escrito y se pierde en silencio.
- **Corrección:** reconstruir el `initial` desde el propio POST al hacer *bind*:
  ```python
  # quiz/forms.py, ChoiceFormSet.__init__
  def __init__(self, *args, **kwargs):
      super().__init__(*args, **kwargs)
      self.correct_field_name = f"{self.prefix}-correct"
      selected = self.data.get(self.correct_field_name) if self.is_bound else None
      for index, form in enumerate(self.forms):
          widget = form.fields["is_correct"].widget
          widget.group_name = self.correct_field_name
          widget.row_index = index
          if selected is not None:
              form.initial["is_correct"] = str(index) == selected
  ```
  Así `CorrectChoiceRadio.get_context` marca el que corresponde sin cambiar el contrato del POST.

#### I3. `queries.py` es una segunda copia de las lecturas de la API, y su docstring afirma lo contrario

- **Archivo:línea:** `quiz/queries.py:1-8` (docstring), `quiz/queries.py:16-18` y `:29-34`, frente a `quiz/views.py:11` y `quiz/views.py:26-31`.
- **Qué falla:** `exams_with_counts()` es lo mismo que `views.py:11`, y `questions_with_choices()` repite el `select_related` y el `prefetch_related` de `views.py:27`. La API no usa `queries.py`, luego la lectura para que la lista web y la lista de la API lean igual (ADR-0002 :113-115) no se cumple por construcción: dependen, y pueden divergir sin que nada lo advierta.
- **Por qué importa:** es la misma clase de defecto que B1 pero en la capa de lectura, y el docstring afirma una propiedad que el código no tiene, lo que engañará al siguiente revisor.
- **Corrección (dos salidas, la segunda exige ADR):** (a) `quiz/views.py:11` pasa a `queryset = queries.exams_with_counts()`, `quiz/views.py:26-30` pasa a `queries.questions_with_choices()` y el filtro `?exam=` se traslada al módulo (cuidado: `views.py:29` usa `exam.isdigit()`, comportamiento que H4 de `docs/arquitectura.md:404` marca como hueco; moverlo no debe cambiar la respuesta). (b) Si se decide **no** tocar `views.py` para no arriesgar el contrato, corregir el docstring de `queries.py` para que diga lo que es cierto y dejar en el ADR que las lecturas quedan duplicadas a propósito.

#### I4. Últimos exámenes muestra los cinco más antiguos

- **Archivo:línea:** `quiz/web_views.py:47` (`queries.exams_with_counts()[:5]`) con `quiz/queries.py:18` (`order_by("id")`).
- **Qué falla:** el panel rotula la sección Últimos exámenes (`quiz/templates/quiz/dashboard.html:37`) y entrega los cinco de menor `id`. Con más de cinco exámenes el panel nunca muestra uno nuevo.
- **Por qué importa:** es un defecto visible en la primera pantalla, y ninguna prueba lo detecta (`test_web.py:112-117` solo comprueba los contadores).
- **Corrección:** función propia y semántica explícita en `queries.py`:
  ```python
  def recent_exams(limit=5):
      """The newest exams, each one carrying its number of questions."""
      return exams_with_counts().order_by("-id")[:limit]
  ```
  y `web_views.py:47` pasa a `queries.recent_exams()`. Requiere añadir la prueba correspondiente.

#### I5. Falta la prueba obligatoria de que la invariante es la misma por los dos caminos

- **Archivo:línea:** falta `quiz/tests/test_services.py`; lo más cercano es `quiz/tests/test_web.py:234-240`.
- **Qué falla:** ADR-0002 :162-163 exige una prueba que **afirma** que el mismo cuerpo inválido recibe el mismo veredicto por el serializador y por el formset, y `docs/requisitos.md:384` (R-UI-T5) lo marca obligatorio. La prueba existente compara el mensaje del formset con una llamada al servicio, pero **nunca pasa por el serializador**, así que no detectaría una divergencia entre API y UI.
- **Por qué importa:** es la red de seguridad de la decisión central del ADR. Sin ella, la afirmación una sola regla solo está apoyada en lectura de código.
- **Corrección:** añadir `quiz/tests/test_services.py` con, como mínimo:
  ```python
  class SameVerdictTests(TestCase):
      def _api_verdict(self, body):   # POST /api/questions/ -> 400 y su mensaje
      def _form_verdict(self, body):  # formset -> non_form_errors
      def test_one_choice_is_refused_by_both(self): ...
      def test_two_correct_choices_are_refused_by_both(self): ...
      def test_no_correct_choice_is_refused_by_both(self): ...
  ```
  con los mismos cuerpos inválidos en los dos lados y `assertEqual` de la lista de errores.

#### I6. No hay prueba del método desconocido se deniega

- **Archivo:línea:** `quiz/permissions.py:22-23` y `quiz/services.py:57-67`; ningún test las ejercita (búsqueda de `TRACE` y de `method_of` en `quiz/tests/`: cero resultados).
- **Qué falla:** el deny-by-default es el requisito literal de la Parte 3 y ADR-0003 :148-150 lo declara obligatorio y afirma que no está cubierto por las pruebas entregadas. Sigue sin estarlo. Además, la rama `ACTION_METHODS` y el parámetro `view` de `method_of` (`services.py:27-30` y `:57-62`) son **código muerto**: DRF siempre pone `request.method`, así que nunca se ejecutan y nadie los prueba.
- **Corrección:** añadir a `test_permissions.py` sin editar las ocho aserciones existentes, como pide ADR-0003 :144:
  ```python
  def test_an_unknown_verb_is_denied(self):
      request = APIRequestFactory().get("/api/questions/", HTTP_AUTHORIZATION=f"Token {self.reader}")
      request.method = "TRACE"
      view = QuestionViewSet()
      self.assertFalse(AgentPermission().has_permission(request, view))
  ```
  Y decidir sobre `ACTION_METHODS`: o se prueba (`services.method_of` sin `method`, con `view.action`), o se elimina del módulo.

#### I7. Faltan dos pantallas declaradas como requisitos de UI

- **Archivo:línea:** `quiz/web_urls.py:12-32` (no existe ruta de lista de preguntas ni buscador).
- **Qué falla:** `docs/requisitos.md:359` (**R-UI-02**, tabla de preguntas con id, examen, texto, número de opciones, correcta y acciones) y `:361` (**R-UI-04**, filtro por examen y búsqueda por texto **operables desde la pantalla** y con URL compartible) están marcados Imprescindible si la UI entra en alcance, y `docs/trazabilidad.md:241-243` los deja en 🔴 pendiente. La interfaz solo ofrece las preguntas anidadas dentro del detalle de un examen.
- **Por qué importa:** no es un defecto de código sino un **hueco de alcance**: si la UI entra en la rúbrica, faltan dos requisitos. Según `AGENTS.md` 6.2 (datos insuficientes) esto se escala, no se decide en revisión.
- **Corrección:** (a) `analista-requisitos` y `arquitecto` confirman si R-UI-02 y R-UI-04 entran en la entrega; (b) si entran, añadir `QuestionListView` reutilizando `queries.questions_with_choices()` y un filtro de búsqueda de DRF reutilizable (sin dependencias nuevas), más un partial de búsqueda con `method="get"` para que la URL sea compartible; (c) si no entran, dejarlos como fuera de alcance por decisión del cliente en `docs/trazabilidad.md`, con fecha y responsable. **No debe quedar en silencio.**

#### I8. La UI pagina de diez en diez y el requisito dice cinco

- **Archivo:línea:** `quiz/web_views.py:25` (`PAGE_SIZE = 10`) frente a `docs/requisitos.md:360` (R-UI-03: Anterior/Siguiente alineados con la paginación del viewset, `paginate_by=5`) y `config/settings.py:81` (PAGE_SIZE: 5).
- **Por qué importa:** requisito explícito incumplido y, además, dos paginaciones distintas para el mismo dominio sin justificación escrita.
- **Corrección:** `PAGE_SIZE = 5` en `web_views.py` reutilizando la constante en lugar de repetir el número, o registrar la desviación como ADR menor. Nota: `test_web.py:131-139` está escrito contra 10 y 11 exámenes y habrá que ajustarlo.

#### I9. `README.md` y `docs/trazabilidad.md` están desfasados respecto al código

- **Archivo:línea:** `README.md` (sección Parte 2 ... está escrito salvo **dos funciones** marcadas `TODO(equipo)`) y `docs/trazabilidad.md:216` y `:229-260`.
- **Qué falla:** el README sigue describiendo las Partes 2 y 3 como pendientes, no menciona la interfaz web, ni `seed_quiz --password`, ni la tabla de la API (que `docs/arquitectura.md:401` marcaba como hueco H1, entra en esta fase). `trazabilidad.md` mantiene 🔴 en `test_quizctl` y `test_permissions`, afirma que no hay `templates/` ni `static/` (líneas 229-231) y cita rutas que no existen (`quiz/templates/quiz/exams/list.html`, `quiz/tests/test_ui.py`) y un nombre de hoja que no es el implementado (`style.css` frente a `app.css`).
- **Por qué importa:** el **criterio 4** (repositorio) se evala leyendo el README. Además, un revisor futuro que solo lea la documentación revisará un software que no existe.
- **Corrección:** `documentador` actualiza `README.md` (puesta en marcha con `seed_quiz --password`, tabla de la API de `docs/arquitectura.md:375-389`, sección de la interfaz con rutas, criterios de acceso y frontera token/sesión) y `docs/trazabilidad.md` (marcas reales y nombres reales de ficheros). No es código: no lo corrijo yo.

### MENORES

| # | Archivo:línea | Hallazgo | Corrección |
|---|---|---|---|
| m1 | `quiz/forms.py:145` | `min_num=2` repite el 2 de `services.MIN_CHOICES` | `min_num=services.MIN_CHOICES` |
| m2 | `quiz/forms.py:108` y `quiz/web_views.py:26` | El nombre del grupo de radios depende del `prefix`, que vive en otro módulo; si divergen, ninguna opción se marca correcta y el error aparece sin causa visible | Exportar `CHOICES_PREFIX = "choices"` desde `forms.py` y usarlo en ambos sitios |
| m3 | `quiz/web_views.py:123-127` | `get_formset()` crea un formset nuevo por llamada (hasta tres por POST: contexto, `form_valid`, `form_invalid`) | Cachearlo con un atributo propio |
| m4 | `quiz/queries.py:29` | El parámetro `exam` de `questions_with_choices` no lo usa ningún llamador | Quitarlo o añadir el filtro que lo usa (ver I3 e I7) |
| m5 | `quiz/queries.py:37-43` | `totals()` son tres consultas y el panel hace cuatro en total | Un `aggregate` con tres `Count`: el panel pasaría a dos |
| m6 | `quiz/queries.py:6-8` | El docstring promete ñúmero de consultas constante y **no hay ninguna prueba** que lo fije (medido hoy: 3 en el detalle, 1 en la lista) | Dos `assertNumQueries` en `test_web.py` |
| m7 | `quiz/management/commands/seed_quiz.py:54-59` y `:19` | Segunda vía de escritura de `Question` y `Choice` que no pasa por `services` (aceptable para datos fijos, pero conviene que sea explícita) y `get_or_create` no corrige un `profe` preexistente que no sea staff (`defaults` solo aplican al crear) | Comentar la exención; y fijar `is_staff` fuera del `if created` |
| m8 | `quiz/templates/404.html:9` | Usa `{{ request.path }}`; Django ya ofrece `request_path`, que llega escapado por el framework | `{{ request_path }}` |
| m9 | `quiz/templates/quiz/login.html:14-20` | Reimplementa el bloque de resumen de errores en vez de incluir el partial (divergencia entre pantallas) | `{% include "quiz/partials/_error_summary.html" %}` |
| m10 | `quiz/templates/quiz/partials/_messages.html:48,53` | `'error' in message.tags` es búsqueda de subcadena: un tag `no-error` dispararía la alerta de error | `{% if message.tags == "error" %}` |
| m11 | `quiz/static/quiz/css/app.css:315` y `:605` | (a) `.btn--danger` reutiliza `--color-primary-contrast` (fuga semántica de token); (b) el `thead` en móviles reimplementa `.visually-hidden` en vez de usar la clase | (a) añadir `--color-danger-contrast`; (b) aplicar `.visually-hidden` al `thead` |
| m12 | `quiz/templates/404.html` y `500.html` | Con `DEBUG = True` (`config/settings.py:10`) Django **no** usa `page_not_found` ni `server_error`: ambas plantillas son inalcanzables y no hay prueba. Solo `403.html` está cubierta (`test_web.py:63`) | Registrar que son plantillas de `DEBUG=False` y añadir una prueba con `@override_settings(DEBUG=False)` |
| m13 | `config/urls.py:11` | Sin salto de línea final | Añadirlo |
| m14 | `quiz/tests/test_web.py:101` | 140 caracteres: la línea más larga del repositorio (el resto del código nuevo queda en 120) | Partirla |
| m15 | `quiz/tests/test_web.py:218` | Afirma el número mágico de cinco radios, atado a `extra=3` y `min_num=2` | Comparar con `len(choices_formset.forms)` |
| m16 | `quiz/static/quiz/css/app.css:24-41` | Las razones de contraste están escritas a mano en comentarios (13.4:1, 6.6:1...) y no hay herramienta ni prueba que las verifique | Verificarlas una vez con herramienta y anotar el resultado; R-UI-11 lo admite como revisión de la hoja |
| m17 | `quiz/templates/quiz/exam_list.html:16-32` | R-UI-01 (`docs/requisitos.md:358`) pide columnas **id**, título, número de preguntas y acciones; falta el id | Añadir la columna |
| m18 | `quiz/web_views.py:140-149` | `QuestionForm` expone un selector con **todos** los exámenes y `QuestionCreateView` no valida el examen de la URL: se puede crear bajo otro examen mientras la miga de pan dice otro | Restringir el selector al examen de la URL, o quitarlo en la ruta de examen |
| m19 | `quiz/tests/test_web.py:285-290` | La prueba de CSRF solo cubre `exam_create` | Repetir en un POST de borrado y en uno de pregunta |
| m20 | `.gitignore` | `Semana_8/` (bóveda de Obsidian del curso) está sin seguimiento y **no ignorada**: un `git add -A` lo metería en el repositorio | Añadirla al `.gitignore` o decidir intencionadamente si entra |

---

## 4. Lo que está bien (para que no haya que rehacerlo)

1. **Invariante única:** verificada por búsqueda de los textos (sección 2.1).
2. **Sin XSS:** búsqueda de `|safe` y `mark_safe` en todo `quiz/` sin resultados; los mensajes con datos del usuario (`web_mixins.py:35`) se renderizan escapados.
3. **Sin `except` amplio:** solo `QuizRuleError` (`forms.py:135`, `serializers.py:34`), `requests.RequestException` y `ValueError` (`quizctl.py:109,113`).
4. **Frontera de confianza intacta y probada:** `test_web.py:96-108` (la sesión no abre la API, el token no abre la UI) y `test_web.py:285` (CSRF obligatorio). Coincide con `docs/arquitectura.md:284-299`.
5. **`settings.py` solo añade:** `REST_FRAMEWORK`, `SPECTACULAR_SETTINGS`, `DATABASES`, `STATIC_URL` y `LANGUAGE_CODE` intactos (diff del commit 7c87fd9).
6. **Sin N+1**, medido con `CaptureQueriesContext`: `exam_detail` tres consultas constantes (examen, preguntas y opciones), `exam_list` una, `totals` tres.
7. **JavaScript realmente progresivo:** con JS desactivado los radios siguen funcionando por `name` común (`test_web.py:216-218` lo verifica) y los formularios no dependen del script.
8. **Suite en verde, verificada por mí en esta revisión:** `Ran 93 tests ... OK`.

---

## 5. Pruebas exigidas antes de integrar

**Del entregable (se ejecuta entero):**

```bash
python manage.py test
```

**Nuevas, obligatorias (cubren hallazgos y requisitos de ADR):**

| # | Prueba | Módulo | Cierra |
|---|---|---|---|
| P1 | Veredicto idéntico serializer frente a formset para tres cuerpos inválidos | `quiz/tests/test_services.py` (nuevo) | I5, R-UI-T5, ADR-0002 :162 |
| P2 | Verbo desconocido (`TRACE`) denegado | `quiz/tests/test_permissions.py` (sin editar las ocho aserciones) | I6, ADR-0003 :148 |
| P3 | El POST inválido conserva el radio marcado | `quiz/tests/test_web.py` | I2, R-UI-05 |
| P4 | El mensaje de negocio aparece **una sola vez** y hay un único `role="alert"` | `quiz/tests/test_web.py` | I1, R-UI-08 y R-UI-11 |
| P5 | `assertNumQueries` en el detalle y en la lista | `quiz/tests/test_web.py` | m6 |
| P6 | Orden de los «Últimos exámenes» (los más nuevos primero) | `quiz/tests/test_web.py` | I4 |
| P7 | `/admin/` responde 404 (no hay segunda vía de escritura) | `quiz/tests/test_web.py` | R-UI-14 |
| P8 | POST de borrado sin token CSRF responde 403 | `quiz/tests/test_web.py` | m19 |
| P9 | 404 y 500 propias se renderizan con `DEBUG=False` | `quiz/tests/test_web.py` | m12 |

**Afirmaciones que hoy no tienen evidencia y no deben presentarse como cubiertas:**

- El número de consultas es constante (`queries.py:6-8`): medida manual, sin prueba en el repositorio.
- La UI respeta los roles (R-UI-07): lo que hay es un 403 global (`test_web.py:65-67`); **no** existe la matriz por rol que pide ADR-0003 :151-152 en `test_permissions.py`.
- Contraste 4.5:1 (R-UI-11): revisado a ojo sobre el código CSS, sin herramienta ni prueba.
- Los cuatro entregables siguen verdes tras tocar `settings.py` (R-UI-T7): **sí** está cubierto, verificado aquí (93/93 OK), pero hay que repetirlo tras los arreglos de esta revisión.

---

## 6. Cumplimiento de los cuatro criterios

| Criterio | Estado | Nota |
|---|---|---|
| 1. Serializadores y validaciones | **Cumple** | Delegan en `services`, contrato intacto, `test_api.py` sin tocar |
| 2. Vistas y enrutadores | **Cumple con salvedad** | `views.py` y `urls.py` de la API sin cambios; el enrutado de la UI es nuevo y correcto, pero I3 deja las lecturas duplicadas |
| 3. Operaciones HTTP y códigos (Partes 2 y 3) | **Cumple con salvedad** | `quizctl` correcto y probado; `AgentPermission` deniega por defecto pero **sin la prueba del verbo desconocido** (I6), y la UI no reutiliza la tabla (B1) |
| 4. Repositorio, tabla de API o interfaz | **En riesgo** | I9 (README y trazabilidad desfasados) e I7 (R-UI-02 y R-UI-04 sin decidir) |

---

## 7. Riesgos

| # | Riesgo | Mitigación |
|---|---|---|
| R-1 | Que la duplicación de B1 sobreviva porque hoy no pasa nada: es exactamente el tipo de divergencia que solo se detecta cuando ya explotó | Corregir B1 antes de integrar y dejar P2 como red |
| R-2 | Que la corrección de I3 toque `views.py` y rompa el contrato OpenAPI | Si se mueve el `get_queryset`, ejecutar `test_api` y `test_agent` antes y después, y comparar `schema.yml` |
| R-3 | Que I7 se cierre por omisión (nadie contesta la pregunta de alcance) y la entrega se presente como completa | Dejar constancia escrita en `trazabilidad.md` con fecha y responsable, sea se implementa o no entra |
| R-4 | `DEBUG = True` y `SECRET_KEY` con valor por defecto siguen vigentes (riesgo R1 de `AGENTS.md`), y ahora hay **sesiones de usuario** además de la API | Fuera del alcance del laboratorio, pero dejarlo escrito en la entrega |
| R-5 | Sin CI: la calidad depende de que alguien ejecute `python manage.py test` (R5 de `AGENTS.md`) | Con los nueve tests nuevos, un comando basta para proteger el conjunto |
| R-6 | Base SQLite con escritura concurrente; las escrituras atómicas de `services` ayudan, pero `runserver` no es concurrente | Sin acción en este laboratorio |

---

## 8. Siguiente paso

1. `backend-django` corrige **B1**, **I1**, **I2**, **I4** y las menores de una línea (m1, m2, m3, m4, m13, m14, m15).
2. `arquitecto` decide **I3** (mover lecturas o enmendar el ADR) y valida las desviaciones de I7, I8 y m17, dejándolas registradas.
3. `analista-requisitos` y `arquitecto` resuelven **I7**: ¿entran R-UI-02 y R-UI-04?
4. `tester` añade **P1-P9** y ejecuta `python manage.py test`.
5. `documentador` actualiza `README.md` y `docs/trazabilidad.md` (**I9**).
6. Vuelta a `revisor-codigo` para el diff de corrección. No hace falta revisar de nuevo lo que no cambia.

---

## 9. Nota de coordinación: el repositorio cambió durante esta revisión

- **Hecho comprobado:** al terminar, `git status` muestra cinco ficheros de prueba **sin seguimiento** que no estaban al empezar: `quiz/tests/test_http_client.py`, `test_http_matrix.py`, `test_persistence.py`, `test_query_counts.py` y `test_web_gaps.py` (mtime 2026-10-16 20:38-20:40). Con ellos la suite pasa de 93 a **272 tests, todos OK**.
- **Qué implica:** esos ficheros **no forman parte** de `cf61a11` ni de `7c87fd9`, así que quedan fuera del alcance de esta revisión y **necesitan una revisión propia** antes de entrar en un commit. Los hallazgos de este informe se refieren al código de los dos commits, que no ha cambiado.
- **Efecto sobre la sección 5:** P5 queda cubierto por `test_query_counts.py`. Ojo con las cifras: ese módulo cuenta las consultas de una **petición HTTP completa** (sesión, autenticación y mensajes incluidos) y por eso afirma 5 y 6, mientras que mi medición (3, 1 y 3) cuenta solo las **consultas de dominio**. No hay contradicción, pero el número de `test_query_counts.py` es ya un contrato: cualquier cambio de I3 o m5 lo rompe y hay que actualizarlo en el mismo commit.
- **Siguen sin cubrir** tras esos ficheros: P1, P2, P3, P4, P6, P7, P8 y P9.
- **Riesgo de coordinación** (`AGENTS.md` 6.5): hay trabajo en paralelo sobre `quiz/tests/` en el mismo árbol de trabajo. Quien lo haga debe saber que este informe ya existe y que **B1 sigue abierto**.


---

```
Rol: revisor-codigo
Tarea: revisión de los commits cf61a11 (Partes 2 y 3) y 7c87fd9 (interfaz web) del proyecto dae-s08-api-headless
Estado: completado
Hallazgos: 1 bloqueante (B1, tabla de roles duplicada en web_mixins.py:20-24, prohibida por ADR-0002 y ADR-0003),
  9 importantes (I1 doble role=alert, I2 radio perdido, I3 lecturas duplicadas con docstring falso,
  I4 «Últimos exámenes» = los más antiguos, I5 falta test_services.py, I6 falta la prueba del verbo desconocido,
  I7 faltan R-UI-02 y R-UI-04, I8 paginación 10 frente a 5, I9 README y trazabilidad desfasados) y 20 menores.
  Evidencia propia: python manage.py test -> Ran 93 tests, OK; sin N+1 medido (3, 1 y 3 consultas);
  el mensaje de negocio aparece dos veces con dos role=alert; el radio no queda marcado tras un POST inválido.
Decisiones/Riesgos: veredicto CAMBIOS. La invariante de la pregunta sí es fuente única (services.py:76 y :78);
  no hay XSS, ni except amplio, ni regresión de contrato. Se escalan I3 e I7 al arquitecto y al analista por ser
  decisiones de diseño, no de código.
Siguiente: backend-django (B1, I1, I2, I4, menores), arquitecto (I3, I7, I8), tester (P1-P9), documentador (I9)
```
