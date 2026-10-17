# 08 · Seguridad

Volver al [[00-Indice]] · Anterior: [[07-Interfaz-grafica]] · Siguiente: [[09-Pruebas-y-resultados]]

Informe completo: `docs/seguridad.md` (agente de seguridad) y `docs/frontera-ia.md` (arquitecto de IA).

## Los dos hallazgos que bloqueaban el cierre

| # | Hallazgo | Estado |
|---|---|---|
| SEC-01 | `quiz/permissions.py` devolvía `True`: **cualquier token autenticado podía borrar**, con borrado en cascada `Exam → Question → Choice` | ✅ **Resuelto** en `cf61a11` |
| SEC-02/03 | `DEBUG = True` con `SECRET_KEY` de reserva: cualquier 500 muestra código, configuración y variables locales. Con la interfaz por sesión, filtrar la clave permite **falsificar cookies** | ⚠️ **Sigue vigente**, documentado como riesgo de laboratorio (ver abajo) |

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
- **Sin secretos en el código**: `DJANGO_SECRET_KEY` por entorno; `seed_quiz` **imprime** los tokens, no
  los versiona; `.env`, `db.sqlite3` y `agent_audit.jsonl` ignorados por git.

## Qué sigue vigente (fuera del aula)

| Riesgo | Qué habría que hacer |
|---|---|
| `DEBUG = True` | Poner `DEBUG = False` y servir estáticos con un servidor real |
| `SECRET_KEY` de reserva | `DJANGO_SECRET_KEY` **obligatoria** en el entorno; la de reserva es solo del aula |
| Sin throttling | `DEFAULT_THROTTLE_CLASSES` si el servicio se expone |
| `ALLOWED_HOSTS` mínimo |hoy es `localhost`, `127.0.0.1`, `testserver` |
| Cabecera anti-clickjacking | `X-Frame-Options` o `frame_options` |
| Auditoría sin atribución de la persona | El log del agente registra el rol, no una identidad nominal |
| Swagger UI carga de un CDN | Fijar `SWAGGER_UI_DIST` a un asset local si se exige funcionar sin internet |

**Conclusión honesta:** este proyecto es **una configuración de laboratorio**. Sirve para un aula, con
`runserver`, en `127.0.0.1`. Desplegarlo tal cual sería incorrecto. El `README.md` lo advierte en la
primera línea y en la sección de configuración.

## Dependencias

Cuatro, todas justificadas: Django (framework), djangorestframework (API), drf-spectacular (contrato
OpenAPI) y requests (cliente y pasarela). **Ninguna añadida durante el trabajo**; `requirements.txt`
sigue con 4 líneas. Sin CDN, sin `package.json`, sin bundler. Ver [[11-Docker-y-CI]].