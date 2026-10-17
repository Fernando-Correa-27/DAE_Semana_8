# Revisión final de confirmación

- **Rol:** agente `revisor-codigo`
- **Alcance:** estado final del working tree tras `7992f2a` y `a82978e` (más tres documentos modificados sin commitear)
- **Fecha:** 2026-10-16
- **Runner:** `python manage.py test` · `python manage.py check`
- **Método:** lectura de código + ejecución de la suite completa + sondas externas temporales (fuera del repositorio, en `%TEMP%\opencode`) para el bloqueante B1 y para las cabeceras. No se editó código, no se arrancó servidor y no se hizo commit.

---

## 1. Veredicto

**APROBADO CON OBSERVACIONES.** No queda ningún bloqueante: el bloqueante B1 está cerrado de
verdad, los nueve importantes están cerrados y los arreglos de seguridad de `a82978e` son
correctos y están cubiertos por pruebas. La suite está en verde (339/339) y el contrato
OpenAPI no ha cambiado.

**Condición de entrega:** hay **1 hallazgo de severidad alta** (F-01): la CSP nueva **rompe
Swagger UI** (`/api/docs/`), que es la Parte 1 del laboratorio y está anunciada en el README.
No es una vulnerabilidad (falla cerrado, no abre nada) y son un arreglo de tres líneas, pero
si alguien abre `/api/docs/` en el aula verá la página **en blanco**. O se corrige F-01, o se
documenta como limitación; no recomiendo presentarlo sin decidirlo antes.

| Severidad | Cantidad | Estado |
|---|:--:|---|
| Bloqueante | 0 | — |
| Alta | 1 | F-01, corregir o documentar antes de presentar |
| Media | 1 | F-09, el README veraz está sin commitear |
| Baja | 5 | F-02 … F-06 |
| Informativa | 2 | F-07, F-08 |

---

## 2. Ejecutado por el revisor

### 2.1 `python manage.py test` (salida literal)

```
Creating test database for alias 'default'...
.........................................................................................................................................................................................................
...........................................................................................................................................
----------------------------------------------------------------------
Ran 339 tests in 18.473s

OK
Destroying test database for alias 'default'...

Found 339 test(s).
System check identified no issues (0 silenced).
```

`python manage.py check` no reporta problemas (lo confirma la línea `System check identified no
issues (0 silenced)` de la ejecución anterior).

### 2.2 Sondas externas (no forman parte del repositorio)

Ejecutadas con `PYTHONPATH` apuntando a `%TEMP%\opencode`, contra la base de datos de pruebas:

```
UI dashboard 200      UI exam_list 200      UI question_list 200      UI exam_detail 200
API DELETE 204
UI reader 403         UI anónimo 302 (redirección a /acceso/)
UI ?exam=abc -> 404   API ?exam=abc -> 400 {'exam': ErrorDetail(string='Expected the id of an exam, for example ?exam=1.', code='invalid')}
HTML CSP: default-src 'self'; frame-ancestors 'none' | XFO: DENY
JSON CSP present: False | type: application/vnd.oai.openapi; charset=utf-8
```

En la primera sonda, el superusuario se creó con `is_superuser=True, is_staff=False`. Las cuatro
pantallas de la interfaz devuelven **200** y su `DELETE /api/questions/1/` devuelve **204**: API
e interfaz coinciden. (El 404 que se ve en la sonda es el segundo `DELETE` sobre un recurso
ya borrado por la primera llamada: artefacto de la sonda, no del código.)

---

## 3. Los hallazgos de la revisión anterior

### 3.1 B1 — bloqueante: **CERRADO**

`quiz/services.py:46-54` decide el rol en un único sitio (`is_staff` **o** `is_superuser` → `PERSON`)
y `may_use` (`quiz/services.py:82-94`) solo compara ese rol. `quiz/web_mixins.py:24-28` no decide
nada: pregunta a `services.may_use`. Búsqueda de un `if user.is_staff` propio en el código de la
interfaz: **cero coincidencias** (solo aparecen en `docstring` y comentarios, que es lo que la
prohibición de ADR-0002 pide).

Comportamiento de un `is_superuser` sin `is_staff`, comprobado por HTTP (§2.2): **idéntico en API
y en interfaz**. Además hay regresión fijada en `quiz/tests/test_services.py:143-152`.

Salvedad menor: la prueba de B1 es de unidades (`services`/`AgentPermission`), no de HTTP. Mi sonda lo
cubrió, pero el repositorio no lo fija. No es bloqueante porque el mixin delega íntegramente.

### 3.2 Importantes

| # | Estado | Evidencia |
|---|---|---|
| **I1** un solo `role="alert"` | ✅ | `_error_summary.html:2` es el único anuncio; `question_form.html:35-39` **enlaza** al resumen en vez de repetir el texto. `test_web_review.py:60-79` |
| **I2** el radio se conserva al fallar | ✅ | `forms.py:115-126` (widget `chosen` desde el POST) + `widgets/correct_choice.html`. `test_web_review.py:85-117` cubre alta, edición y el caso sin marcar |
| **I4** los últimos exámenes son los más nuevos | ✅ | `queries.py:20-22` (`order_by("-id")[:limit]`). `test_web_review.py:120-140` |
| **I6** `ACTION_METHODS` sin código muerto y probado | ✅ | `services.py:27-30, 64-69`; la rama sin `request.method` se ejercita en `test_services.py:163-176` (los seis verbos, acción desconocida y `view=None`) |
| **I7** listado global de preguntas con búsqueda y filtro | ✅ | `web_views.py:109-151` (`?q=`, `?exam=` conservados por la paginación), `queries.py:33-40`, `question_list.html`. `?exam=` no entero → 404, medido |
| **I8** una sola constante de paginación | ✅ parcial | `settings.py:149` → `REST_FRAMEWORK.PAGE_SIZE` y `web_views.py:27,58,118`. Los tres listados usan la misma constante. Queda un número suelto: ver **F-04** |
| **m1** `MIN_CHOICES` | ✅ | `forms.py:159` usa `services.MIN_CHOICES` con `validate_min=False` y comentario explicando por qué |

### 3.3 Seguridad de `a82978e`

Revisado, buscando regresiones, efectos laterales y fugas:

- **`_secret_key()` (`settings.py:40-57`)**: entorno → `.secret_key` → (solo con `DEBUG`) clave en
  memoria. **No hay ninguna credencial en el código** y la clave no se imprime en ningún log,
  stdout ni respuesta de error (los dos `ImproperlyConfigured` no la incluyen). El orden es
  correcto: con `DEBUG=0` la clave de disco **no** cuenta.
- **Solo lectura**: no rompe. `_secret_key_from_file` captura el `OSError` (`settings.py:27-28,35-36`)
  y `_secret_key` cae a `get_random_secret_key()` en memoria (`settings.py:57`): el servidor
  arranca, pero las sesiones se invalidan en cada reinicio. Con `DJANGO_DEBUG=0` ni se intenta
  escribir. Ambos caminos están probados en `test_config_hardening.py:61-84`.
- **`DEBUG`/`ALLOWED_HOSTS` por entorno (`settings.py:16, 60-78`)**: fallan cerrados. Sin regresión:
  el valor por defecto `1` mantiene el laboratorio igual y la suite pasa entera con `DEBUG=False`
  (lo fuerza el runner).
- **`X-Frame-Options` + `config/middleware.py`**: `X_FRAME_OPTIONS = "DENY"` es el valor por defecto
  de Django, pero hasta ahora **no se emitía** porque faltaba el middleware (`docs/seguridad.md:133`
  lo documentaba). Ahora se emite, medido. La CSP se aplica **solo** a `text/html` y con `setdefault`,
  así que no pisa nada que venga puesto. Correcto.
- **`--show-tokens`**: opt-in, con las cuatro variantes cubiertas en `test_config_hardening.py:133-157`
  (sin flag, con flag, contraseña nunca impresa). La contraseña no sale ni con `--show-tokens`.
- **Fuga de clave en la página técnica**: Django limpia `SECRET_KEY` (`HIDDEN_SETTINGS`), así que
  el 500 con `DEBUG=True` no la filtra. Correcto.

**Efectos secundarios encontrados:** F-01 (Swagger) y F-02 (500 sin estilos).

### 3.4 Legibilidad, duplicación y complejidad

`services.py` (142 líneas) es la pieza más limpia del cambio: tabla de roles, invariante y
adaptadores, con docstrings que explican el porqué. `forms.py` no reescribe ninguna regla.
`queries.py` mantiene las lecturas sin N+1. `web_views.py` no pasa de 253 líneas y ninguna vista
supera las 60. Sin `except` amplio, sin `|safe`/`mark_safe` en todo el proyecto, sin `on*=` inline.
`base.html` sin salto de línea final y `app.css` sin `url()`/`@import` (627 líneas, sin CDN):
correcto.

Lo único que chirría es la constante suelta de F-04 y la documentación de F-05/F-06/F-09.

### 3.5 Rendimiento y seguridad

- Sin N+1: `test_query_counts.py` fija el número de consultas **con 8 y con 68 preguntas** y exige
  el mismo número, que es la forma correcta de fijarlo (un `> 0` no probaría nada).
- Sin XSS: `autoescape` intacto, cero `|safe`/`mark_safe`/`autoescape off`. El texto hostil del
  seed se escapa en las tres pantallas.
- CSRF en los cinco formularios POST, `LogoutView` solo por POST, frontera sesión/token intacta
  y probada.

### 3.6 Contrato del laboratorio y ADR

- **El contrato OpenAPI no ha cambiado** de forma no documentada: `config/urls.py` y `quiz/urls.py`
  intactos, `quiz/views.py` solo añade el 400 de `?exam=` (documentado en el `extend_schema` de
  `views.py:34-45` y en el README), `test_api.py` sin tocar.
- **La UI no duplica las reglas de negocio**: `forms.py:143-150` pregunta a
  `services.validate_question_choices` y traduce el error; `web_views.py` escribe solo a través de
  `services.create_question` / `update_question`. ADR-0002 se respeta.
- **Una sola regla de permisos**: ADR-0003 se cumple con `may_use` delegando en `role_of` +
  `METHODS_BY_ROLE`. La única regla propia de la interfaz (R-UI-07: privada, solo el profesorado)
  está escrita, justificada y en un solo sitio (`services.py:83-94`).

### 3.7 Veracidad de la documentación

| Afirmación | Veredicto |
|---|---|
| «las pruebas fallan» | **Falso y ya corregido**: `Semana_8/09:11` y `docs/requisitos.md:16` dicen 324 OK; el README del working tree dice 339 y `trazabilidad.md:26` 339. La línea base «61 pruebas, 21 fallando» es histórica y está etiquetada como tal |
| Número de pruebas | **Correcto en el working tree** (339, medido). **Falso en el commit `a82978e`** (decía 324) → F-09 |
| Cómo se obtienen los tokens | **Correcto**: `seed_quiz` sin flag + `--show-tokens` (`README.md:67-70, 110-111`, `seed_quiz.py:50-53, 75-82`) |
| Tabla de la API | **Correcta**: endpoints, métodos, parámetros (`?exam=`, `?search=`, `?page=`), cuerpos y códigos coinciden con `urls.py`, `views.py`, `serializers.py` y `quizctl.py:48-63` (códigos de salida 0-6) |
| `SECRET_KEY` de reserva | **Falso en el commit, cierto en el working tree** → F-09 |

---

## 4. Hallazgos

### F-01 · ALTA · La CSP bloquea Swagger UI (`/api/docs/`)

- **Archivo:línea** — `config/middleware.py:16-22` y `config/settings.py:83`
- **Qué pasa** — `SPECTACULAR_SWAGGER_UI_DIST` de drf-spectacular apunta por defecto a
  `https://cdn.jsdelivr.net/npm/swagger-ui-dist@latest`
  (`drf_spectacular/settings.py:83`). El HTML de `/api/docs/` lo referencia, y la respuesta ahora
  lleva `Content-Security-Policy: default-src 'self'; frame-ancestors 'none'`, que **bloquea** ese
  CDN. Medido en vivo con sonda:

  ```
  status 200
  CSP: default-src 'self'; frame-ancestors 'none'
  cdn en el HTML: True
  ['<link rel="stylesheet" href="https://cdn.jsdelivr.net/.../swagger-ui.css">',
   '<script src="https://cdn.jsdelivr.net/.../swagger-ui-bundle.js"></script>', ...]
  ```

  En un navegador real: **página en blanco**. Devuelve 200, por lo que ninguna prueba del repositorio
  lo detecta.
- **Por qué importa** — `/api/docs/` es la Parte 1 del laboratorio y el README lo anuncia
  (`README.md:148, 286`); `docs/trazabilidad.md:257` lo marca como «verificado en vivo». Quien abra
  esa URL en la demo ve una página vacía y concluirá que el contrato no funciona. No es una
  vulnerabilidad: la CSP falla cerrado.
- **Corrección propuesta** (no aplicada; elige una):
  1. *Recomendada* — en `ContentSecurityPolicyMiddleware.__call__`, saltar cuando
     `request.path.startswith("/api/docs/")` (o `resolver_match.view_class` es de spectacular).
     Mínimo privilegio: la interfaz conserva la CSP estricta y solo se relaja en la vista de
     documentación. Añadir la aserción contraria en
     `test_config_hardening.py::ResponseHeaderTests` (`assertNotIn("Content-Security-Policy", .../api/docs/)`).
  2. `SPECTACULAR_SETTINGS["SWAGGER_UI_DIST"]` a un asset local: cierra de paso R-VIE-21 / T-OP-2,
     pero es un asset que hay que servir (y con `DEBUG=0` `runserver` no sirve `/static/`: ver el
     aviso de `README.md:133-138`). Más trabajo.
  3. CSP con el CDN permitido **solo** en esa ruta: menos recomendable, abre a un tercero.

### F-02 · BAJA · La página de error 500 se queda sin estilos

- **Archivo:línea** — `quiz/templates/500.html:7-21`
- **Qué pasa** — lleva un `<style>` inline «standalone, on purpose». Con `DJANGO_DEBUG=0` esa
  plantilla sí se usa, es `text/html`, y la CSP `default-src 'self'` (sin `'unsafe-inline'`) bloquea
  el bloque: se ve el texto sin formato.
- **Por qué importa** — cosmético, y solo con `DEBUG=0`. Se cierra moviendo ese CSS a
  `quiz/static/` y usando `{% static %}`, o admitiendo `style-src 'self' 'unsafe-inline'` **solo**
  para esa plantilla.

### F-03 · BAJA · Ventana TOCTOU al crear `.secret_key`

- **Archivo:línea** — `config/settings.py:33-34`
- **Qué pasa** — `path.write_text(generated)` crea el fichero con los permisos por defecto (0644 con
  umask 022 en POSIX) y justo después se hace `os.chmod(path, 0o600)`. Durante ese instante el
  fichero es legible por otros usuarios del mismo equipo.
- **Por qué importa** — mínimo en un aula, pero es exactamente el tipo de detalle que esta revisión
  cerró en `a82978e`. Alternativa: `fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)`
  y escribir por el descriptor, sin ventana.
- **Lo que NO es un problema** — el escenario de solo lectura está bien resuelto (ver §3.3).

### F-04 · BAJA · Queda una constante de paginación suelta

- **Archivo:línea** — `quiz/queries.py:20` (`recent_exams(limit=5)`), `quiz/web_views.py:48`
- **Qué pasa** — I8 está cerrado para las dos paginaciones (`settings.PAGE_SIZE` → API y a las dos
  listas), pero el panel del dashboard llama a `recent_exams()` sin argumento y el `5` está escrito
  a mano en el módulo de lecturas. `test_web_review.py:130-135` fija ese 5 a mano también.
- **Por qué importa** — cambiar `settings.PAGE_SIZE` mueve API + interfaz y **deja el panel en 5**,
  exactamente la divergencia que I8 quería cerrar. Sugerencia: `from django.conf import settings` en
  `queries.py` y `def recent_exams(limit=None): limit = limit or settings.PAGE_SIZE`, o pasar
  `PAGE_SIZE` desde `DashboardView`.

### F-05 · BAJA · El README describe la puerta de la interfaz con `is_staff` cuando decide el rol

- **Archivo:línea** — `README.md:224-225`
- **Qué pasa** — «La interfaz **exige `is_staff`**», pero lo que exige es el rol `person`, es decir
  `is_staff` **o** `is_superuser` (la propia tabla de la Parte 3 lo dice bien en `README.md:179`).
  Medido: un superusuario sin `is_staff` entra (200 en las cuatro pantallas).
- **Mismo matiz** — `Semana_8/07-Interfaz-grafica.md:57` («Usuario autenticado que no es `is_staff`
  → 403») y `Semana_8/12-Limitaciones-y-pendientes.md:13` («La interfaz solo es para `is_staff`»).
  Sugerencia de redacción: «exige el rol *persona* (`is_staff` o `is_superuser`)».

### F-06 · BAJA · `docs/seguridad.md` quedó desfasado respecto al código

- **Archivo:línea** — `docs/seguridad.md:119-146` (SEC-03), `:133-146` (SEC-04), `:638`, `:1044-1046`
- **Qué pasa** — SEC-03 y SEC-04 siguen como «Abierto / VIGENTE» citando `config/settings.py:9` y
  «`SECRET_KEY` con reserva», que ya no existe. El estado real está en
  `docs/seguridad-interfaz.md:32-35` (SUI-01, SUI-02, SUI-05 CERRADOS). Además `docs/seguridad.md:1044`
  afirma que la página técnica de Django expone `SECRET_KEY`: Django la limpia (`HIDDEN_SETTINGS`),
  así que la afirmación es incorrecta.
- **Por qué importa** — es un documento del repositorio que afirma algo falso sobre el estado de
  seguridad; contradice a `seguridad-interfaz.md` y al README. Marcar SEC-03/SEC-04 como cerrados
  con remisión a SUI-01/SUI-05, y corregir la línea 1044.

### F-09 · MEDIA · Las correcciones documentales veraces están sin commitear

- **Archivo:línea** — `README.md` (todo el fichero), `docs/trazabilidad.md:26,40,256`, `docs/seguridad-interfaz.md:32-35`
- **Qué pasa** — el working tree tiene **tres documentos modificados y sin commit**
  (`git status`: `M README.md`, `M docs/seguridad-interfaz.md`, `M docs/trazabilidad.md`). En el
  **commit `a82978e`** el README sigue afirmando `Ran 324 tests` (`README.md:281` de ese commit)
  y que la `SECRET_KEY` es la reserva `dev-only-not-a-secret` en `config/settings.py:9`
  (`README.md:324` de ese commit) — **las dos afirmaciones son falsas** frente al código actual. En el
  working tree ya están corregidas (339, sin clave en el código, tabla de variables nueva).
- **Por qué importa** — la revisión se hace sobre el estado final, pero quien clonee el repositorio
  se queda con el README falso. Commitear estos tres ficheros (es un `docs`, no toca código) antes
  de presentar.

### F-07 · INFORMATIVA · `AGENTS.md` desfasado

- **Archivo:línea** — `AGENTS.md:14`
- Dice que el repositorio tiene «un único commit» y que `test_quizctl` y `test_permissions` «**fallan**».
  Hoy son 6 commits y 339/339 OK. Es el protocolo de equipo, no código: que lo actualice el
  orquestador.

### F-08 · INFORMATIVA · Enlace de Obsidian dentro del README

- **Archivo:línea** — `README.md:137`
- `[[Semana_8/12-Limitaciones-y-pendientes]]` es sintaxis de Obsidian: en GitHub se renderiza como
  texto plano. Un enlace relativo normal (`Semana_8/12-Limitaciones-y-pendientes.md`) o nada.

---

## 5. Lo que está bien (y conviene decir)

- **B1 cerrado de verdad**, no con parche: una sola decisión de rol, la del servidor, y la interfaz
  pregunta. Es la corrección de mayor calidad de las dos rondas.
- **Los arreglos de seguridad no introducen regresiones funcionales** salvo la de Swagger (F-01), y
  están fijados con pruebas que arrancan un intérprete aparte para comprobar el *fallo al arrancar*,
  que es la parte difícil de probar y aquí está bien resuelta.
- **La suite es un argumento, no un adorno**: 339 pruebas que fijan número de consultas con dos
  tamaños de datos, el mismo veredicto del validador por API y por formulario, la supervivencia del
  radio marcado, el anuncio único y la paridad persona/superusuario.
- **`test_api.py` (contrato entregado) no se ha tocado**: el laboratorio se amplía sin reinterpretar
  lo entregado.
- La documentación es **honesta en lo que dolió**: `trazabilidad.md` mantiene abiertos R-REP-03
  (parcial), R-UI-07, R-UI-11 y SUI-03, y el README declara la limitación de `/static/` con
  `DEBUG=0` en vez de esconderla.

## 6. Pruebas exigidas antes de cerrar

1. `python manage.py test` completo en verde (ya ejecutado: 339/339 OK).
2. Si se toca `config/middleware.py` o `config/settings.py` (F-01, F-02): suite completa **más**
   una aserción sobre `/api/docs/` y una comprobación en navegador de que Swagger UI carga.
3. Si se cambia `PAGE_SIZE` (F-04): la suite debe seguir en verde con otro valor, para demostrar
   que ya no hay constantes sueltas.
4. Ninguna prueba nueva obligatoria por F-03, F-05, F-06, F-08, F-09 (documentación y orden de
   llamadas al sistema de ficheros).

## 7. Riesgos

- **R1 (nuevo)** — presentar el laboratorio sin decidir F-01: el docente abre `/api/docs/` y ve un
  espacio en blanco en la Parte 1. Impacto alto, probabilidad alta.
- **R2** — el `.secret_key` se genera en el primer arranque de cada máquina; si alguien lo copia al
 portapapeles o lo versiona por descuido, la clave de esa máquina queda escrita. Mitigación:
  recordarlo en el README (ya está en `.gitignore` y hay prueba de regresión).
- **R3** — `SUI-03` (login sin límite de intentos) sigue abierto y aceptado como riesgo del
  laboratorio. No es de esta revisión, pero conviene que quien presente lo sepa.
- **R4** — sin CI (decisión documentada): la suite depende de que alguien la ejecute. Con 339
  pruebas y ~19 s, un `python manage.py test` antes de cada entrega es barato.

---

```
Rol: revisor-codigo
Tarea: revisión final de confirmación tras corregir el bloqueante B1 y los nueve importantes
Estado: completado
Hallazgos: B1 cerrado (verificado en código y por sonda HTTP); I1, I2, I4, I6, I7, m1 cerrados;
  I8 cerrado con un resto menor (F-04); seguridad de a82978e sin regresiones salvo Swagger UI (F-01);
  suite 339/339 OK; contrato OpenAPI sin cambios no documentados; README veraz en el working tree y
  falso en el commit (F-09)
Decisiones/Riesgos: veredicto APROBADO CON OBSERVACIONES, sin bloqueantes; F-01 debe corregirse o
  documentarse antes de presentar (R1)
Siguiente: backend-django (F-01, F-02, F-03, F-04) · documentador (F-05, F-06, F-08, F-09) ·
  tester (suite completa tras los cambios)
```
