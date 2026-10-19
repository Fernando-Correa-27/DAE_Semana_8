# 08 · Seguridad

Volver al [[00-Indice]] · Anterior: [[07-Interfaz-grafica]] · Siguiente: [[09-Pruebas-y-resultados]]

Informe completo: `docs/seguridad.md` (agente de seguridad), `docs/seguridad-interfaz.md` (agente de
seguridad, auditoría de la interfaz) y `docs/frontera-ia.md` (arquitecto de IA).

## Estado tras la corrección (`a82978e`)

| # | Hallazgo | Estado |
|---|---|---|
| SEC-01 | `quiz/permissions.py` devolvía `True`: **cualquier token autenticado podía borrar**, con borrado en cascada `Exam → Question → Choice` | ✅ **Resuelto** en `cf61a11` |
| SEC-02 / SEC-03 | `DEBUG = True` con `SECRET_KEY` de reserva: con la interfaz por sesión, filtrar la clave permite **falsificar cookies** | ✅ **Resuelto** en `a82978e` (SUI-01 y SUI-02 cerrados) |
| SEC-04 | Sin cabeceras anti-clickjacking | ✅ **Resuelto** en `a82978e` (SUI-05 cerrado) |
| SEC-17 / SUI-04 | `seed_quiz` imprimía los tokens por terminal | ✅ **Resuelto** en `a82978e`: la impresión es opt-in (`--show-tokens`) |
| **SUI-03** | **Login de la interfaz sin límite de intentos** | 🟠 **ABIERTO, riesgo aceptado.** No corregido. Mitigante parcial ya presente: **no hay enumeración de usuarios** (mensaje genérico e idéntico exista o no la cuenta) |

### Qué cambió exactamente en `a82978e`

- **Ninguna credencial en el código.** Orden de resolución de la clave: `DJANGO_SECRET_KEY` del entorno →
  si no hay, se lee o se **genera una clave aleatoria** en `.secret_key` (ignorado por git) → si
  `DJANGO_DEBUG` está apagado y no hay variable de entorno, arranque con `ImproperlyConfigured`. La clave
  **nunca se imprime**.
- **`DEBUG` y `ALLOWED_HOSTS` salen del entorno** (`DJANGO_DEBUG`, por defecto `"1"` para que el
  laboratorio siga igual, y `DJANGO_ALLOWED_HOSTS` separada por comas). Con `DEBUG` apagado y sin la
  variable, el arranque **falla cerrado**.
- **Cabeceras de seguridad en la interfaz**: `X-Frame-Options: DENY` y una CSP
  `default-src 'self'; frame-ancestors 'none'` emitida **solo** en respuestas HTML por el nuevo
  `config/middleware.py` (la API JSON y `/static/` no la llevan). Para poder aplicar la CSP sin
  `unsafe-inline`, el `<script>` inline de `base.html` se movió a `quiz/static/quiz/js/app.js`.
- **`seed_quiz` ya no imprime los tokens** sin `--show-tokens`; sin ese flag resume los datos y explica
  cómo obtenerlos. `--password` nunca imprime la contraseña.
- **15 pruebas nuevas** en `quiz/tests/test_config_hardening.py` que fijan todo lo anterior ante
  regresión. Suite: `Ran 365 tests ... OK`.

Informe y detalle: `docs/seguridad-interfaz.md` (§«Estado tras la corrección») y
`docs/trazabilidad.md` §5 y §7.

## Los dos hallazgos que bloqueaban el cierre — y su estado final

> Tabla original del cierre, conservada como registro. El estado vigente está en
> «Estado tras la corrección» (arriba).

| # | Hallazgo | Estado |
|---|---|---|
| SEC-01 | `quiz/permissions.py` devolvía `True`: **cualquier token autenticado podía borrar**, con borrado en cascada `Exam → Question → Choice` | ✅ **Resuelto** en `cf61a11` |
| SEC-02/03 | `DEBUG = True` con `SECRET_KEY` de reserva: cualquier 500 muestra código, configuración y variables locales. Con la interfaz por sesión, filtrar la clave permite **falsificar cookies** | ✅ **Resuelto** en `a82978e` (antes: «sigue vigente»). Ver [[12-Limitaciones-y-pendientes]] |

## Qué se resolvió

### La regla de roles en el servidor

`quiz/services.py` — una tabla, funciones puras, sin dependencia de DRF:

| Rol | read | create | update | delete |
|---|:--:|:--:|:--:|:--:|
| `person` (`is_staff` o `is_superuser`) | sí | sí | sí | **sí** |
| `agent` (grupo `agente`) | sí | sí | sí | **no** |
| `reader` (autenticado sin rol) | sí | no | no | no |
| anónimo | no | no | no | no |
| **verbo desconocido** | — | — | — | **no** |

`quiz/permissions.py::AgentPermission` es un adaptador de tres líneas. La interfaz web usa **la misma**
tabla a través de `services.may_use()`: cambiar «quién puede borrar» se cambia **una vez**.

**Verificado en vivo:** agente DELETE → **403** (el recurso sobrevive); lector POST/DELETE → **403**;
sin token → **401**; persona DELETE → **204**.

**Denegar por defecto:** un verbo fuera de la tabla se devuelve como `False` — es el requisito literal de
la rúbrica y la defensa contra un método nuevo que se añada sin que nadie repase la tabla. Cubierto por
`quiz/tests/test_services.py::DenyByDefaultTests`.

### La frontera del agente

`agent/gateway.py` es una **pasarela cerrada**, verificada contra el contrato OpenAPI:

| Riesgo | Qué hace |
|---|---|
| **R0** — lectura | Se ejecuta con el token del **agente** y la respuesta vuelve envuelta como **`untrusted_data`** |
| **R1** — creación | Se ejecuta, también con el token del agente |
| **R2** — destructivo | **No se ejecuta.** Devuelve `plan` + `plan_hash` y exige aprobación con el token de **la persona** |

Medidas concretas:

- **Lista cerrada `ALLOWED`**: cualquier `op` fuera de ella (por ejemplo `run_sql`) es `denied`.
- **El contrato manda**: `ALLOWED` es un subconjunto de los `operationId` de `/api/schema/`. Si una
  operación desaparece del contrato, la pasarela deja de ofrecerla.
- **Validación estricta de argumentos**: claves y tipos se comprueban antes de enviar nada.
- **El hash caduca**: si el objetivo cambia entre el plan y la aprobación, el hash deja de valer y se
  vuelve a pedir aprobación.
- **Auditoría**: cada decisión deja una línea en `agent_audit.jsonl` con actor, operación, riesgo y
  resultado (el fichero está ignorado por git).
- **El texto hostil es dato, no orden**: la pregunta del seed que contiene `IGNORA TUS INSTRUCCIONES` se
  devuelve como texto y no cambia el comportamiento de la frontera.
- **El servidor tiene la última palabra**: la pasarela no decide permisos, los aplica.

### La frontera de confianza con la interfaz

| Situación | API | Interfaz |
|---|---|---|
| Anónimo | **401** | **302** al login |
| Autenticado sin permiso | **403** | **403** |
| Token válido usado en la interfaz | No autentica | **302** |
| CSRF ausente en un POST de la interfaz | — | **403** |

Ninguna de las dos capas se salta la comprobación. Cubierto por `test_web.py::FrontierTests` y
`test_http_matrix.py::SessionTokenFrontierTests`.

### Lo que se hizo bien desde el principio

- **Sin XSS**: ni `|safe` ni `mark_safe` en todo el proyecto; todo el HTML se escapa.
- **Sin `except` amplio**: solo `QuizRuleError`, `requests.RequestException` y `ValueError`, encadenados
  con `from exc`.
- **Sin sesión en la API**: token en cabecera, sin cookies ni superficie de CSRF.
- **El cliente no decide nada**: la regla vive en el servidor.
- **Sin secretos en el código**: `DJANGO_SECRET_KEY` por entorno; si no hay, la clave se **genera** en
  `.secret_key` (ignorado por git) y nunca se imprime; `seed_quiz` **solo** imprime los tokens si se pide
  con `--show-tokens`; `.env`, `db.sqlite3`, `.secret_key` y `agent_audit.jsonl` ignorados por git.

## Qué sigue vigente (fuera del aula)

| Riesgo | Estado | Qué habría que hacer |
|---|---|---|
| **Login sin límite de intentos** (SUI-03) | 🟠 **Abierto, riesgo aceptado del laboratorio** | Contar intentos por `(IP, usuario)` con `django.core.cache` y devolver **429** tras 5 fallos. No hay enumeración de usuarios: el mensaje de fallo es genérico |
| `DEBUG = True` **por defecto** | Mitigado | Arrancar con `DJANGO_DEBUG=0` + `DJANGO_SECRET_KEY` + `DJANGO_ALLOWED_HOSTS`; hoy el arranque **aún no** trae servidor estático ni HTTPS |
| Sin throttling en la API | Vigente | `DEFAULT_THROTTLE_CLASSES` si el servicio se expone |
| Cabeceras de cookies sin `Secure`, sin HSTS, sesión de 14 días | Vigente | Bloque `SECURE_*` / `SESSION_COOKIE_AGE` solo fuera de desarrollo |
| `Cache-Control: private` en las vistas con sesión | Vigente | Un middleware o `@never_cache` |
| `is_correct` visible para cualquier token autenticado en la API | Vigente (SEC-08 / SUI-09) | Serializadores de lectura separados, o documentarlo como decisión consciente. **En la interfaz está cerrado** (403 a no `is_staff`) |
| Auditoría sin atribución de la persona | Vigente | El log del agente registra el rol, no una identidad nominal |
| Swagger UI carga de un CDN | Vigente | Fijar `SWAGGER_UI_DIST` a un asset local si se exige funcionar sin internet |

**Conclusión honesta:** este proyecto es **una configuración de laboratorio**. Sirve para un aula, con
`runserver`, en `127.0.0.1`. Desplegarlo tal cual sería incorrecto. El `README.md` lo advierte en la
primera línea y en la sección de configuración.

## Dependencias

Cuatro, todas justificadas: Django (framework), djangorestframework (API), drf-spectacular (contrato
OpenAPI) y requests (cliente y pasarela). **Ninguna añadida durante el trabajo**; `requirements.txt`
sigue con 4 líneas. Sin CDN, sin `package.json`, sin bundler. Ver [[11-Docker-y-CI]].