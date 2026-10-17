# Arquitectura — API headless + interfaz web de cuestionarios

> Documento de diseño del Arquitecto de software. **No implementa código de producción**: define
> estructura, contratos y límites. La implementación corresponde a `backend-django`.
> Convenciones del curso: código, nombres y comentarios en **inglés**; entregables en **español**.

---

## 1. Punto de partida (hechos comprobados en el repositorio)

| Hecho | Evidencia |
|---|---|
| Un único dominio de negocio en la app `quiz` | `quiz/models.py:4-33` |
| API DRF con `ModelViewSet` + `DefaultRouter` | `quiz/views.py:9-31`, `quiz/urls.py:5-9` |
| Contrato OpenAPI servido con `drf-spectacular` | `config/urls.py:7-8`, `settings.py:57-62` |
| Autenticación de la API **solo por token** | `settings.py:46` |
| La invariante de opciones vive **solo** en el serializador | `quiz/serializers.py:31-36` |
| `quiz/permissions.py` sin implementar (`return True`) | `quiz/permissions.py:19-20` |
| `quizctl.py` con 2 funciones `TODO(team)` | `quizctl.py:45-64` |
| No existe UI, ni plantillas, ni estáticos, ni formularios, ni admin | `glob **/*.html/css` → sin resultados |
| No hay bloque `TEMPLATES`, ni `sessions`, `messages`, `staticfiles`, `admin` | `config/settings.py:13-25` |
| `agent/` es una frontera cerrada R0/R1/R2 que habla **HTTP** con la API | `agent/gateway.py:124-181` |

**Implicación clave:** la invariante de negocio y la regla de permisos están hoy *atadas al
transporte HTTP*. Añadir una segunda interfaz obligará a decidir dónde vive cada regla
(§5 y ADR-0002/0003). Ese es el problema central de esta fase.

---

## 2. Decisión de arquitectura de la interfaz

**Django Templates server-rendered + `ModelForm`/formularios de Django + CSS propia.**
Sin SPA, sin JavaScript obligatorio, sin CDN, sin build.

Justificación (criterios del laboratorio, no preferencias):

1. **Cero dependencias nuevas.** `requirements.txt` sigue con 4 líneas. Una SPA exige
   `node`, bundler, `package.json`, artefactos de build y una cadena de herramientas que
   el repositorio no tiene ni necesita para un laboratorio de servidor local.
2. **La referencia ya lo demuestra.** `dae-s07-orm-con-ia` resuelve CRUD completo con
   CBVs, `ModelForm`, parciales y una hoja CSS propia. Es el patrón del curso.
3. **Accesibilidad por teclado y `role="status"`** funcionan de forma nativa; una UI
   mayoritariamente estática no depende de foco gestionado por JavaScript.
4. **Consola y agente siguen siendo clientes de verdad.** La UI no sustituye a `quizctl.py`
   ni a `agent/`: sigue habiendo una API headless que es el contrato máquina.
5. **Anti‑sobreingeniería.** El estado de la UI es "el usuario miró algo y mineó algo".
   Un `ListView` + `Paginator` cubre el 100 % de las pantallas necesarias.

Desviación deliberada respecto a la referencia: **sin Bootstrap ni Google Fonts por CDN**.
En un aula el Wi‑Fi falla, y una interfaz que depende de un tercero externo no es funcional.
Se escribe CSS propio con custom properties (el mismo sistema de diseño que ya usa la
referencia, pero autocontenido). Iconos: SVG inline o etiquetas de texto; **sin emojis**.

Detalle completo en [`docs/adr/0001-arquitectura-de-la-interfaz-web.md`](adr/0001-arquitectura-de-la-interfaz-web.md).

### 2.1 Decisión conexa: sin `django.contrib.admin`

El admin sería una **segunda vía de escritura** que no pasa por
`QuestionSerializer.validate_choices`, es decir, un camino donde se pueden guardar preguntas
con cero o con dos opciones correctas. No es lo que pide el objetivo, cuesta
`staticfiles` + plantillas de admin, y `manage.py createsuperuser` / `changepassword` ya
resuelven la gestión de usuarios sin él. **Consecuencia de ADR-0001.**

---

## 3. Capas y estructura de directorios

### 3.1 Capas

```
                  ┌────────────────────┐        ┌────────────────────┐
  navegador ─────►│  Presentación web  │        │  Presentación API  │◄─── quizctl.py
                  │  (web_views/forms) │        │  (views/serializ.)│◄─── agent/
                  └─────────┬──────────┘        └─────────┬──────────┘
                            │                            │
                            ▼                            ▼
                  ┌──────────────────────────────────────────────┐
                  │  DOMINIO:  services.py (invariantes,       │
                  │             escrituras atómicas)            │
                  │             permissions.py (tabla de acciones)│
                  └──────────────────────┬───────────────────────┘
                                         ▼
                          models.py · queries.py (lecturas)
                                         ▼
                                    SQLite (dev)
```

Regla de oro: **las flechas nunca se invierten.** Ni la API ni la UI llaman a la otra;
ambas consumen el dominio.

### 3.2 Estructura de archivos

```
config/
  settings.py            ← se amplía (§4); NO se toca el bloque REST_FRAMEWORK
  urls.py                ← se añade path("", include("quiz.web_urls"))  (§4.4)
quiz/
  models.py              sin cambios
  serializers.py         sin cambios de comportamiento (§3.3)
  views.py               sin cambios (API)
  urls.py                sin cambios (API) — no se toca el router
  permissions.py         REDISEÑADO (ADR-0003): tabla de acciones + adaptador DRF
  queries.py             NUEVO  · lecturas (select_related / prefetch_related / filtros)
  services.py            NUEVO  · invariantes + escrituras atómicas (ADR-0002)
  forms.py               NUEVO  · ModelForm de examen + formset de opciones
  web_views.py           NUEVO  · CBVs de la interfaz
  web_urls.py            NUEVO  · app_name = "quiz_ui", rutas HTML
  web_mixins.py          NUEVO  · LoginRequired + may() para la UI
  templates/quiz/
    base.html
    403.html · 404.html · 500.html
    login.html
    partials/  _navbar.html · _messages.html · _pagination.html
               _field.html · _choice_row.html · _exam_card.html · _question_card.html
    exam_list.html · exam_detail.html · exam_form.html · exam_confirm_delete.html
    question_list.html · question_detail.html · question_form.html
    question_confirm_delete.html
  static/quiz/css/style.css    NUEVO  · hoja propia, sin CDN
  tests/
    test_web.py           NUEVO  · recorridos CRUD por HTTP de la UI
    test_permissions.py   se amplía con la parte de UI
```

**Por qué la UI vive dentro de la app `quiz` y no en una app `web/` nueva:**
la UI y la API son *dos presentaciones del mismo dominio*. Separarlas en dos apps obligaría
a que `web/` importara internals de `quiz/` y a mantener un `INSTALLED_APPS` más, sin ganar
nada a esta escala. Dentro de la app, la separación se consigue por **módulos**
(`views.py` API vs `web_views.py` UI) y por **rutas** (`quiz/urls.py` vs `quiz/web_urls.py`),
que es separación real sin duplicar el dominio.

`web_urls.py` lleva `app_name = "quiz_ui"` y se incluye con su propio `include(...)`, de modo
que **el router de la API no se toca** y el contrato OpenAPI queda intacto.

### 3.3 Contrato entre componentes

| Consumidor | Entra por | Reglas que aplica | Identidad |
|---|---|---|---|
| `quizctl.py` | HTTP + `Authorization: Token` | serializadores | token |
| `agent/` | HTTP + token del agente | serializadores + `AgentPermission` + riesgo R0/R1/R2 | token |
| Swagger en `/api/docs/` | HTTP | — (documentación) | — |
| **Interfaz web** | **ORM en proceso** | **`services.py` + `permissions.py`** | **sesión de Django** |

Contrato de la UI con el dominio, tres reglas y ninguna más:

1. **La UI nunca escribe con `Model.objects.create()` ni con `.save()`** sobre
   `Question`/`Choice`. Escribe llamando a `quiz.services`, que es donde vive la invariante.
2. **La UI nunca decide permisos con `if user.is_staff:`**ramo suelto. Llama a
   `quiz.permissions.may(user, action)`.
3. **La UI nunca redefine los mensajes de error de negocio.** Los textos viven en
   `services.question_rules()` y el formulario los traduce a `ValidationError`.

`quiz/serializers.py` conserva su comportamiento público (mismos mensajes, mismos códigos
HTTP). Si extrae los mensajes a `services.py`, **el texto debe ser idéntico carácter a
carácter**: `quiz/tests/test_api.py:57` comprueba que la respuesta 400 contiene `"exactamente una"`.
Mover la regla no puede cambiar la redacción.

---

## 4. Cambios necesarios en `config/settings.py`

Todo lo que sigue es **adición**. No se modifica `DATABASES`, `REST_FRAMEWORK`,
`SPECTACULAR_SETTINGS`, `LANGUAGE_CODE`, `TIME_ZONE` ni `STATIC_URL`.

### 4.1 `INSTALLED_APPS` — añadir 3 apps

```python
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.sessions",      # NUEVO · cookie de sesión: login, logout, LoginRequiredMixin
    "django.contrib.contenttypes",
    "django.contrib.messages",      # NUEVO · avisos tras el POST/Redirect (patrón PRG)
    "rest_framework",
    "rest_framework.authtoken",
    "drf_spectacular",
    "django.contrib.staticfiles",   # NUEVO · {% static %} y el finder de apps
    "quiz",
]
```

| App | Por qué es obligatoria |
|---|---|
| `sessions` | `SessionMiddleware` falla al arrancar sin la app. Sin ella no hay login por sesión, y por tanto no hay identidad para la UI. |
| `messages` | `MessageMiddleware` falla sin la app. Es lo que permite decir «Pregunta creada» tras redirigir, sin reenviar el formulario. |
| `staticfiles` | Sin la app no existe el *finder* que resuelve `{% static 'quiz/css/style.css' %}` con `APP_DIRS`-style lookup, ni `collectstatic`. |
| `admin` | **No se añade** — ver §2.1. |
| `humanize`, `flatpages`, etc. | **No se añaden.** No se usan. |

El **orden** importa solo por legibilidad; `auth` debe estar antes de `staticfiles`, pero Django
no lo exige para `auth`.

### 4.2 `MIDDLEWARE` — añadir 4 (el orden SÍ importa)

```python
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",   # NUEVO · 1.º: crea la sesión
    "django.middleware.common.CommonMiddleware",               # ya existía
    "django.middleware.csrf.CsrfViewMiddleware",              # NUEVO · protege los POST de la UI
    "django.contrib.auth.middleware.AuthenticationMiddleware",  # NUEVO · pone request.user desde la sesión
    "django.contrib.messages.middleware.MessageMiddleware",   # NUEVO · consume/guarda mensajes
]
```

El orden es obligatorio y es el canónico de Django:
`Security → Sessions → Common → Csrf → Authentication → Messages`.
Si `CsrfViewMiddleware` va antes de `AuthenticationMiddleware`, un 403 que intente usar
`request.user` se evalúa sin usuario. Si `MessageMiddleware` va antes de `Authentication`,
los mensajes se guardan antes de que exista la sesión que los soporta.

`MESSAGE_STORAGE` (nuevo, coherente con `sessions`):

```python
MESSAGE_STORAGE = "django.contrib.messages.storage.session.SessionStorage"
```

### 4.3 `TEMPLATES` — bloque nuevo (hoy no existe; bloquea cualquier UI)

```python
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]
```

- `DIRS: []` a propósito: las plantillas viven en `quiz/templates/`, y `APP_DIRS: True` las
  encuentra. No se crea un `templates/` raíz que después nadie mantiene.
- `APP_DIRS: True` **no** puede combinarse con el loaders explícito; por eso el `OPTIONS` va vacío.
- Los tres context processors son los mínimos: `request` (CSRF y `request.resolver_match`),
  `auth` (`user` en `base.html` para la barra de navegación) y `messages` (el partial `_messages.html`).

### 4.4 Rutas y estáticos

```python
# config/urls.py
urlpatterns = [
    path("", include("quiz.web_urls")),            # NUEVO · UI HTML
    path("api/", include("quiz.urls")),            # sin cambios
    path("api/schema/", ...), path("api/docs/", ...),   # sin cambios
]

LOGIN_URL = "quiz_ui:login"
LOGIN_REDIRECT_URL = "quiz_ui:exam_list"
LOGOUT_REDIRECT_URL = "quiz_ui:login"
```

Sin estos tres settings, `LoginRequiredMixin` redirige a `/accounts/login/` (valor por defecto
de Django) y el usuario recibe un 404 tras escribir bien su contraseña.

**Estáticos — precisión importante:**

```python
STATIC_URL = "static/"                             # ya existía; no se toca
# STATICFILES_DIRS = [BASE_DIR / "quiz" / "static"]   # NO hace falta
```

`quiz/static/` **ya se sirve** porque `django.contrib.staticfiles` instalado + `quiz` en
`INSTALLED_APPS` activan `AppDirectoriesFinder`. Añadir `STATICFILES_DIRS` apuntando a la
misma carpeta sería redundante. Si en el futuro se crea un `static/` **a nivel de proyecto**
(por ejemplo `static/admin-custom.css`), entonces sí se añade
`STATICFILES_DIRS = [BASE_DIR / "static"]`. Decisión: **una sola raíz de estáticos, la de la app.**

### 4.5 La frontera de confianza: token (API) y sesión (UI) conviven

Este es el punto que más revisa `seguridad`. Las dos autenticaciones **no se mezclan**:

| | API `/api/*` | Interfaz `/` |
|---|---|---|
| Autenticación | `TokenAuthentication` (cabecera `Authorization`) | cookie `sessionid` |
| Quién decide quién es el usuario | DRF (`rest_framework.request.Request.user`) | `AuthenticationMiddleware` (`HttpRequest.user`) |
| CSRF | No aplica | Sí, obligatorio en todo POST |
| Permisos | `AgentPermission` | `may(user, action)` — la misma tabla |
| Migración de sesión a datos | — | `django.contrib.auth.migrations` |

Cuatro garantías comprobables, que el equipo **debe verificar con pruebas**, no con
suposiciones:

1. **La API no acepta la cookie de sesión.** `AuthenticationMiddleware` solo rellena
   `HttpRequest.user`; DRF construye su propia `Request` y la autentica con sus
   `authentication_classes`. Un token de sesión **no** autentica `/api/*`.
   → Prueba: `client.force_login(agente)` y luego `GET /api/questions/` **sin** cabecera
   `Authorization` debe seguir respondiendo **401**.
2. **La UI no acepta el token.** `AgentPermission` no se ejecuta en vistas Django normales.
   → Prueba: `GET /` con `Authorization: Token <x>` y sin sesión debe dar 302 al login.
3. **CSRF no rompe la API.** `APIView.as_view()` aplica `csrf_exempt` a la vista, de modo que
   `CsrfViewMiddleware` **no** se aplica a `/api/*`. Los POST de la API siguen funcionando sin
   token CSRF. → Prueba: los cuatro entregables (`test_api`, `test_agent`, `test_quizctl`,
   `test_permissions`) deben seguir en verde **después** de tocar `settings.py`.
4. **La UI sí exige CSRF.** Cada `<form method="post">` lleva `{% csrf_token %}`. Una prueba
   de la UI debe comprobar que un POST sin token da 403, no 200.

**Punto de seguridad a confirmar por el equipo (no verificado por mí):** `/api/schema/` y
`/api/docs/` son vistas de `drf-spectacular`, y depende de si sobrescriben
`permission_classes`. Si **no** lo sobrescriben, quedan bajo `DEFAULT_PERMISSION_CLASSES`
(→ requieren token) y `/api/schema/` deja de ser legible sin token; `agent/gateway.load_catalog`
y `quizctl ops` siguen funcionando porque ambos mandan token, pero conviene confirmarlo con:

```bash
python manage.py shell -c "from drf_spectacular.views import SpectacularAPIView as V; print(V.authentication_classes, V.permission_classes)"
```

Mientras no se confirme, la postura segura es considerar el contrato **público** (es un
documento, no un dato) y no apoya ninguna decisión de seguridad en él.

---

## 5. Sistema de permisos (diseño de la Parte 3)

Detalle y justificación en [`docs/adr/0003-regla-de-permisos.md`](adr/0003-regla-de-permisos.md).

Idea central: **una tabla de acciones, dos adaptadores.** Ni la API ni la UI deciden nada;
preguntan.

```python
AGENT_GROUP = "agente"
READ, CREATE, UPDATE, DELETE = "read", "create", "update", "delete"

_BY_METHOD = {
    "GET": READ, "HEAD": READ, "OPTIONS": READ,
    "POST": CREATE, "PUT": UPDATE, "PATCH": UPDATE, "DELETE": DELETE,
}

def role_of(user): ...      # None | "person" | "agent" | "reader"
def action_for(request): ...  # None si el método HTTP no está en la tabla
def may(user, action): ...    # único lugar donde vive la regla
```

`AgentPermission.has_permission()` se reduce a tres líneas: traducir método → acción,
`may(...)`, y **denegar si la acción es `None`** (método desconocido). Ese último caso es lo
que hoy está implícito en `return True` y es el que la rúbrica pide explícito.

**Combinación con `LoginRequired` en la UI:**

| Situación | API | UI |
|---|---|---|
| Anónimo | 401 (`TokenAuthentication` falla antes de evaluar permisos) | 302 a `LOGIN_URL` (`LoginRequiredMixin`) |
| Autenticado sin rol | 403 | 403 con `templates/quiz/403.html` |
| Método desconocido | 403 | no aplica (el enrutador HTML no enruta verbos desconocidos) |

En la UI el orden es: `LoginRequiredMixin` primero (identidad), después la comprobación de rol
(autorización). Nunca al revés: un anónimo no es «un lector sin permiso», es «nadie».

Ocultar botones es **comodidad**, no seguridad: el enlace «Eliminar» solo se renderiza para
`is_staff`, y la comprobación se repite en `dispatch()`.

---

## 6. Revisión de la API frente a la rúbrica

### 6.1 Lo que ya cumple

| Elemento | Estado | Evidencia |
|---|---|---|
| Serializadores anidados | Cumple | `serializers.py:24` (`choices` anidadas, `exam` como id) |
| Validación de dominio | Cumple | `serializers.py:31-36` (≥2 opciones, exactamente 1 correcta) |
| Escritura atómica | Cumple | `serializers.py:40,47` (`transaction.atomic` + `bulk_create`) |
| `PATCH` parcial | Cumple | `test_api.py:70-74` (solo cambia lo enviado) |
| Vistas y router | Cumple | `views.py:9-31`, `urls.py:5-7` |
| Anotación sin N+1 en exámenes | Cumple | `views.py:11` (`annotate(Count)`) |
| Prefetch en preguntas | Cumple | `views.py:27` |
| Contrato OpenAPI | Cumple | `config/urls.py:7-8`; test de sincronía con la pasarela en `test_api.py:83-93` |
| Códigos HTTP | Cumple | 200/201/204/400/401/403/404, todos con prueba |

### 6.2 Tabla de la API (faltaba en el `README.md`)

| Operación | Método y ruta | Rol mínimo | Éxito | Errores |
|---|---|---|---|---|
| `exams_list` | `GET /api/exams/?page=` | lector | 200 (paginado) | 401, 403 |
| `exams_create` | `POST /api/exams/` | agente | 201 | 400, 401, 403 |
| `exams_retrieve` | `GET /api/exams/{id}/` | lector | 200 | 401, 403, 404 |
| `exams_update` | `PUT/PATCH /api/exams/{id}/` | agente | 200 | 400, 401, 403, 404 |
| `exams_destroy` | `DELETE /api/exams/{id}/` | persona | 204 | 401, 403, 404 |
| `questions_list` | `GET /api/questions/?exam=&search=&page=` | lector | 200 (paginado) | 401, 403 |
| `questions_create` | `POST /api/questions/` | agente | 201 | 400, 401, 403 |
| `questions_retrieve` | `GET /api/questions/{id}/` | lector | 200 | 401, 403, 404 |
| `questions_update` | `PUT/PATCH /api/questions/{id}/` | agente | 200 | 400, 401, 403, 404 |
| `questions_destroy` | `DELETE /api/questions/{id}/` | persona | 204 | 401, 403, 404 |
| raíz de la API | `GET /api/` (API root del router) | lector | 200 | 401 |
| contrato | `GET /api/schema/` | por verificar (§4.5) | 200 (JSON/YAML) | — |
| documentación | `GET /api/docs/` | por verificar (§4.5) | 200 (HTML) | — |

Prefijo de paginación: `{count, next, previous, results}`, `PAGE_SIZE = 5`
(`settings.py:52-53`). Filtros de `questions_list`: `exam` (id entero, filtra por examen) y
`search` (subcadena del enunciado).

### 6.3 Huecos reales (no wishes)

Ordenados por relación coste/beneficio en un laboratorio.

| # | Hueco | Evidencia | Riesgo | ¿Entra en esta fase? |
|---|---|---|---|---|
| H1 | **Sin tabla de la API** en el `README.md` | `README.md:33-42` | Rúbrica | **Sí** — §6.2 de este documento, el `documentador` lo copia al README |
| H2 | `AgentPermission` no implementada: el token del agente puede borrar | `permissions.py:19-20` | **Crítico** | **Sí** — ADR-0003 |
| H3 | La invariante de negocio solo existe en el serializador: la UI no podría reutilizarla | `serializers.py:31-36` | Alto al añadir UI | **Sí** — ADR-0002 |
| H4 | `?exam=` no numérico se **ignora en silencio** y devuelve la lista completa en lugar de un 400 | `views.py:29` (`exam.isdigit()`) | Medio: cliente que filtra por un id equiviso cree que no hay datos | **Sí** — parseo explícito en `get_queryset`, con prueba |
| H5 | `ExamViewSet` no tiene `filter_backends` mientras `QuestionViewSet` sí | `views.py:11` vs `views.py:23-24` | Bajo: asimetría, no bug | **No** — se deja constancia |
| H6 | Mensajes de error en español literales sin `gettext`, con `USE_I18N = True` | `serializers.py:33,35` + `settings.py:39` | Bajo: no se traduce nunca | **No** — se mantiene literal (cambiar el texto rompe `test_api.py:57`) |
| H7 | `DEBUG = True` y `SECRET_KEY` con valor por defecto | `settings.py:9-10` | Crítico **fuera del aula** | **No** — ya está en el riesgo R1 de `AGENTS.md` |
| H8 | Sin throttling; `POST /api/questions/` sin límite | `settings.py:44-55` | Bajo en local | **No** — sobredimensionado para el laboratorio |

Regla sobre H4 que quiero dejar escrita: **un filtro mal formado es un error del cliente y
debe verse como tal (400)**, no como una lista completa. Silenciar un parámetro equivocado es
la clase de defecto que más caro sale después, porque el cliente toma decisiones sobre datos
falsos.

---

## 7. Estrategia de pruebas para la UI

Se mantiene `python manage.py test` (no se adopta `pytest`: decisión ya abierta en
`AGENTS.md §9` y nada de lo que aquí se diseña la obliga a cambiar).

| Fichero | Qué cubre |
|---|---|
| `quiz/tests/test_web.py` | Login/logout, CRUD de examen y pregunta por HTTP, 302→login, 403 por rol, POST sin CSRF → 403 |
| `quiz/tests/test_permissions.py` (ampliado) | La misma matriz de roles en la UI: el agente edita, no ve «Eliminar»; el lector no crea |
| `quiz/tests/test_services.py` (nuevo) | La invariante **una sola vez**, compartida: serializer y formset dan el mismo veredicto |
| `quiz/tests/test_api.py` (sin tocar) | El contrato no se rompe: la API sigue igual tras añadir la UI |

Criterio de cierre de la fase: `test_api` y `test_agent` **no cambian**; `test_quizctl` y
`test_permissions` pasan; `test_web` pasa. Si añadir la UI obliga a tocar `test_api`, es
señal de que se ha roto el contrato.

---

## 8. Plan de trabajo por fases

| Fase | Responsable | Entregable | Puerta de salida |
|---|---|---|---|
| B (esta) | Arquitecto | `docs/arquitectura.md` + 3 ADR | Diseño aprobado |
| C1 | Backend | `permissions.py` (ADR-0003) | `test_permissions` verde |
| C2 | Backend | `quizctl.py` (2 funciones) | `test_quizctl` verde |
| C3 | Backend | `services.py` + `queries.py`; `serializers.py` delega | `test_services` verde, `test_api` intacto |
| C4 | Backend | `settings.py` (§4) + `web_urls` mínimo + login | `test_api` sigue verde tras tocar settings |
| C5 | Backend + Revisor | Formularios, CBVs, plantillas, CSS | `test_web` verde |
| C6 | Seguridad + Documentador | Revisión de frontera (§4.5) · README con tabla de API | Sin hallazgos críticos |

Orden C1→C4 respects las dependencias: los permisos van primero porque son el entregable que
hoy deja al agente con capacidad de borrado; los servicios van antes que la UI porque la UI
no tiene a quién preguntar si no existen.

---

## 9. Riesgos y preguntas pendientes

**Riesgos**

| # | Riesgo | Mitigación |
|---|---|---|
| R-A | Que la UI se convierta en una segunda API improvisada (validaciones propias, ORM directo) | ADR-0002 + prohibición explícita de `objects.create()` en las vistas web |
| R-B | Que añadir `CsrfViewMiddleware` rompa la API | `APIView` es `csrf_exempt`; comprobación en la puerta C4 con los cuatro entregables |
| R-C | Que la sesión se cuele en la API (o al revés) | Las 4 pruebas de §4.5 |
| R-D | Cambiar el texto de un error de negocio rompa `test_api.py:57` | Al extraer a `services.py`, copiar las cadenas **carácter a carácter** |
| R-E | Sobreingeniería: aparecer un `front/` con JSON, un endpoint `/api/web/`, o un `forms.py` gigante con 400 líneas | El alcance son 8 plantillas; si una vista pasa de ~60 líneas, sobra |

**Preguntas pendientes (para el usuario, no se inventan)**

1. **Interpretación del objetivo.** El enunciado dice «una interfaz que consuma la API real».
   Mi diseño hace que la UI consuma el **mismo dominio en proceso**, no la API por HTTP
   (§10 / ADR-0002). Es la opción que evita doble validación, tokens para el usuario web y
   un agujero CSRF. Si la lectura literal es obligatoria, el cambio está **confinado** a
   `quiz/services.py`: sus funciones pasarían a hablar HTTP por detrás de la misma interfaz,
   y ni las vistas ni las plantillas se tocarían. **Decisión del cliente del proyecto.**
2. ¿Se quiere **alta de usuarios** en la UI? Mi recomendación es **no**: los usuarios se crean
   con `manage.py createsuperuser` y `manage.py changepassword profe`. Una alta abierta crea
   identidades sin auditar, y los roles se definen por staff/grupo.
3. ¿Hay una rúbrica oficial del campus que exija algún endpoint, vista o prueba concreta que
   no esté aquí contemplado?
4. ¿Se acepta **no** entregar `django.contrib.admin`, asumiendo que no habrá pantalla de
   administración de datos (§2.1)?

**Nota operativa:** `seed_quiz` crea `profe` y `agente` con contraseña inservible
(`seed_quiz.py:17-22`). Para que la UI tenga con quién entrar hay que ejecutar
`python manage.py changepassword profe` (comando nativo, sin código nuevo) o crear usuarios con
`createsuperuser`. No se guardan contraseñas en el repositorio.
