# Documentación y guía de uso de la API

Guía completa para consumir la API de cuestionarios desde Postman, una aplicación
propia o un agente de inteligencia artificial. Todo lo descrito aquí está **verificado
contra el servidor real**; no se Documenta ningún endpoint, permiso o mecanismo que no
se haya comprobado.

---

## 1. Objetivo del proyecto

La API permite **consumir los datos de exámenes, preguntas y opciones desde cualquier
cliente o aplicación** sin necesidad de una pantalla. Cada petición se autentica con un
token y el servidor decide qué se permite según el **rol** que ese token representa.

Tres formas de consumirla:

| Consumidor | Cómo se conecta | Para qué |
|---|---|---|
| Persona (docente) | Token `profe` o la interfaz web | Gestionar todo, incluido borrar |
| Agente de IA | Token `agente` | Consultar y crear, **nunca borrar** |
| Cualquiera | Sin token | Solo el contrato público (`/api/schema/`, `/api/docs/`) |

## 2. Los dos tokens y por qué existen

`python manage.py seed_quiz --show-tokens` crea y muestra dos tokens:

| Token | Usuario | Grupo | Puede leer | Puede crear | Puede modificar | **Puede borrar** |
|---|---|---|---|---|---|---|
| `QUIZ_TOKEN_HUMANO` | `profe` (es *staff*) | — | sí | sí | sí | **sí** |
| `QUIZ_TOKEN_AGENTE` | `agente` | `agente` | sí | sí | sí | **no** |

**Por qué la diferencia.** Es el principio de **mínimo privilegio**: un sistema
autónomo no debería poder ejecutar una acción irreversible. Si un agente de IA (o el
modelo que lo maneja) decide borrar un examen por un error de interpretación, el daño es
irreversible, porque `on_delete=CASCADE` arrastra preguntas y opciones. Por eso la
diferencia no está en el cliente —que podría falsearla— sino **en el servidor**, que la
impone aunque el cliente se comporte mal.

La regla se aplica en `quiz/services.py` y la consulta `AgentPermission`
(`quiz/permissions.py`). Un verbo HTTP desconocido se deniega para todos.

## 3. Configuración y conexión

### 3.1 Arrancar el proyecto

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_quiz --show-tokens      # guarda los tokens que imprime
python manage.py runserver
```

### 3.2 URL base

```
http://127.0.0.1:8000/api/
```

### 3.3 Variables de entorno

**PowerShell:**

```powershell
$env:QUIZ_URL          = "http://127.0.0.1:8000"
$env:QUIZ_TOKEN_HUMANO = "<token que imprimió seed_quiz>"
$env:QUIZ_TOKEN_AGENTE = "<token que imprimió seed_quiz>"
$env:QUIZ_TOKEN        = $env:QUIZ_TOKEN_HUMANO     # el que usa quizctl.py
```

**Bash:**

```bash
export QUIZ_URL="http://127.0.0.1:8000"
export QUIZ_TOKEN_HUMANO="<token>"
export QUIZ_TOKEN_AGENTE="<token>"
export QUIZ_TOKEN="$QUIZ_TOKEN_HUMANO"
```

> `QUIZ_TOKEN_HUMANO`, `QUIZ_TOKEN_AGENTE` y `QUIZ_TOKEN` los leen **`quizctl.py`** y la
> **pasarela del agente**. La API en sí **no lee variables de entorno**: el token viaja
> siempre en la cabecera de cada petición.

## 4. Autenticación

La API usa **`TokenAuthentication`** (cabecera `Authorization`), **no** cookies ni
sesión. Formato exacto:

```
Authorization: Token <valor_del_token>
```

Este detalle importa: **si el navegador ya tiene iniciada una sesión web, esa sesión no
da acceso a la API.** Comprobado:

```
GET /api/exams/ con cookie de sesión de profe  ->  401
```

La frontera está verificada en ambos sentidos:

| Prueba | Resultado |
|---|---|
| Cookie de sesión de la interfaz → `/api/exams/` | **401** (la API no acepta sesión) |
| Token de API → abrir la interfaz web | **no aplica**: la interfaz usa sesión |

El único detalle: **`/api/schema/` y `/api/docs/` son públicos** (200 sin token), porque
son la descripción de la API, no datos. El contrato es público; los datos no.

## 5. Envío de solicitudes HTTP

Todos los verbos disponibles, con su código real:

| Método | Recurso | Token humano | Token agente |
|---|---|---|---|
| `GET` | `/api/exams/` `/api/questions/` `/api/options/` | 200 | 200 |
| `POST` | `/api/exams/` `/api/questions/` `/api/options/` | 201 | 201 |
| `PUT` | `/api/{recurso}/{id}/` | 200 | 200 |
| `PATCH` | `/api/{recurso}/{id}/` | 200 | 200 |
| `DELETE` | `/api/{recurso}/{id}/` | **204** | **403** |

Ejemplo con `curl` (PowerShell):

```powershell
$headers = @{ "Authorization" = "Token $env:QUIZ_TOKEN_HUMANO" }

curl.exe -H "Authorization: Token $env:QUIZ_TOKEN_HUMANO" `
         "http://127.0.0.1:8000/api/exams/"
```

## 6. Uso de Postman

### 6.1 Preparar la colección

1. Abre Postman → **New Collection** → ponle nombre `API Quiz`.
2. **Variables de colección**: en el icono de la carpeta, pestaña *Variables*:

   | Variable | Valor inicial |
   |---|---|
   | `base_url` | `http://127.0.0.1:8000` |
   | `token_humano` | *(pega tu token humano)* |
   | `token_agente` | *(pega tu token de agente)* |

3. En **Authorization**, elige *Type: No Auth* en la colección (la cabecera se añade
   petición a petición, porque cambia según el token que quieras probar).

### 6.2 Crear una petición

1. **New → HTTP Request**.
2. **Method**: `GET` · **URL**: `{{base_url}}/api/exams/`
3. Pestaña **Headers** (manual, no el generador):
   - `Authorization` → `Token {{token_humano}}`
   - `Accept` → `application/json`
4. **Send**. Esperado: **200 OK**.

Para probar el token del agente, cambia solo el valor:
`Authorization: Token {{token_agente}}`.

### 6.3 Petición con cuerpo

1. Method `POST`, URL `{{base_url}}/api/questions/`
2. Headers: `Authorization` + `Content-Type: application/json`
3. Pestaña **Body** → *raw* → selector **JSON**:

```json
{
  "exam": 1,
  "text": "¿Qué es una API REST?",
  "choices": [
    {"text": "Un estilo de arquitectura sobre HTTP", "is_correct": true},
    {"text": "Un lenguaje de programación", "is_correct": false}
  ]
}
```

Esperado: **201 Created**.

### 6.4 Colección mínima recomendada

Crear estas peticiones dentro de la colección:

| Nombre | Método | URL | Token | Código esperado |
|---|---|---|---|---|
| Listar exámenes | GET | `{{base_url}}/api/exams/` | humano | 200 |
| Listar preguntas | GET | `{{base_url}}/api/questions/` | humano | 200 |
| Detalle de examen | GET | `{{base_url}}/api/exams/1/` | humano | 200 |
| Crear pregunta | POST | `{{base_url}}/api/questions/` | humano | 201 |
| Modificar parcial | PATCH | `{{base_url}}/api/questions/1/` | humano | 200 |
| Eliminar | DELETE | `{{base_url}}/api/questions/1/` | humano | 204 |
| **Intento de borrado** | DELETE | `{{base_url}}/api/questions/1/` | **agente** | **403** |
| Sin token | GET | `{{base_url}}/api/exams/` | *(ninguno)* | 401 |

Las dos últimas son las que demuestran que los permisos funcionan.

## 7. Permisos y restricciones

### 7.1 Cómo verificar que los permisos se aplican

Ejecuta **el mismo borrado con los dos tokens**. Es la comprobación decisiva:

```
DELETE /api/questions/155/   con token humano  ->  204  (borrado)
DELETE /api/questions/155/   con token agente  ->  403  (nada cambió)
DELETE /api/exams/34/        con token agente  ->  403
```

Y que el token del agente sí puede escribir:

```
POST  /api/questions/  con token agente  ->  201
PATCH /api/questions/155/ con token agente ->  200
PUT   /api/questions/155/ con token agente ->  200
```

Los cuatro casos están cubiertos además por pruebas automáticas
(`quiz/tests/test_permissions.py`), que **fallan** si la regla se rompe.

### 7.2 Limitaciones adicionales

- **El token no caduca** y no hay caducidad ni rotación implementada.
- **No hay límite de peticiones** (sin *throttling*).
- `is_correct` es visible para cualquier token autenticado, porque un cliente necesita
  saber qué respuestas son correctas para mostrar la solución.
- El token del agente **sí** puede crear contenido, incluido texto arbitrario. Trátalo
  como una escritura sin revisión humana.

## 8. Ejemplos prácticos (respuestas reales)

**Consultar**

```bash
curl.exe -H "Authorization: Token $env:QUIZ_TOKEN_HUMANO" \
  "http://127.0.0.1:8000/api/exams/"
```

```json
{"count": 2, "next": null, "previous": null,
 "results": [
   {"id": 1, "title": "Django · ORM", "created_at": "2026-10-18T22:24:31-05:00", "question_count": 4},
   {"id": 2, "title": "Django · Plantillas", "created_at": "2026-10-18T22:24:31-05:00", "question_count": 4}
 ]}
```

**Crear** (token del agente)

```
POST /api/questions/   ->  201
{"exam": 1, "text": "¿Qué es una API REST?",
 "choices": [{"text": "Un estilo de arquitectura sobre HTTP", "is_correct": true},
             {"text": "Un lenguaje de programación", "is_correct": false}]}
```

```json
{"id": 60, "exam": 1, "text": "¿Qué es una API REST?",
 "choices": [
   {"id": 226, "text": "Un estilo de arquitectura sobre HTTP", "is_correct": true},
   {"id": 227, "text": "Un lenguaje de programación", "is_correct": false}
 ],
 "created_at": "2026-10-18T22:24:40-05:00"}
```

**Modificar parcialmente** (solo cambia lo enviado)

```
PATCH /api/questions/60/   {"text": "¿Qué es una API REST? (v2)"}   ->  200
```

**Modificar por completo** (el conjunto enviado reemplaza al anterior)

```
PUT /api/questions/60/
{"exam": 1, "text": "¿Qué es una API REST? (v3)",
 "choices": [{"text": "Un estilo de arquitectura sobre HTTP", "is_correct": true},
             {"text": "Un lenguaje de programación", "is_correct": false}]}
 ->  200
```

**Eliminar** — solo con el token humano

```
DELETE /api/questions/60/   con token humano  ->  204  (sin cuerpo)
DELETE /api/questions/60/   con token agente  ->  403
```

## 9. Manejo de errores

| Código | Significado | Causa típica | Solución |
|---|---|---|---|
| **400** | Error de validación | Falta un campo, tipo incorrecto, o la regla de una sola respuesta correcta | Corrige el cuerpo; el mensaje dice qué campo falla |
| **401** | Sin credenciales | Falta la cabecera, o el token está mal escrito | Revisa `Authorization: Token <token>` |
| **403** | Sin permiso | El token es el del agente y la operación es `DELETE` | Usa el token humano |
| **404** | No existe | El `id` no existe, o la página está fuera de rango | Comprueba el `id` |
| **405** | Método no permitido | Verbo no implementado para ese recurso | Usa GET/POST/PUT/PATCH/DELETE según la tabla |
| **500** | Error del servidor | Fallo inesperado | Mira la traza en la terminal |

Ejemplos reales de mensaje:

```json
{"text": ["Este campo es requerido."]}
```

```json
{"exam": ["Tipo incorrecto. Se esperaba valor de clave primaria y se recibió str."]}
```

```json
{"choices": ["Debe haber exactamente una opción correcta."]}
```

```json
{"detail": "Las credenciales de autenticación no se proveyeron."}
```

```json
{"detail": "Usted no tiene permiso para realizar esta acción."}
```

> Los 400 **no guardan nada**: si la validación falla, no queda ninguna pregunta ni
> opción a medias, porque la escritura ocurre en una transacción atómica.

## 10. Uso y propósito de los tokens

### 10.1 Para qué sirve cada uno

- **`QUIZ_TOKEN_HUMANO`**: identidad de una persona con autoridad plena. Es la clave
  maestra de operación: si se filtra, alguien puede borrar todo el contenido.
- **`QUIZ_TOKEN_AGENTE`**: identidad de un sistema autónomo. Deliberadamente **no** puede
  borrar. Sirve para que un modelo pueda consultar y ampliar el banco de preguntas sin
  poder destruirlo.

### 10.2 ¿Acceden directamente a la API o necesitan una sesión?

**Directamente, y solo con el token.** No hay que combinarlos con una sesión de usuario
ni con cookies. El flujo es:

```
cliente  --[Authorization: Token X]-->  servidor
servidor  --valida X, deduce el rol, decide-->  200 / 201 / 403
```

La cookie de sesión **no** sirve para la API (comprobado: 401), y el token **no** sirve
para la interfaz web. Son dos mecanismos separados a propósito:

| | API | Interfaz web |
|---|---|---|
| Mecanismo | Token en cabecera | Cookie de sesión |
| Acceso | Desde scripts y agentes | Desde el navegador |
| Persona | sí | sí |
| Agente | sí (sin borrar) | **no** |

## 11. El problema del inicio de sesión

### 11.1 Lo que ocurre

Al intentar entrar en la interfaz web (`http://127.0.0.1:8000/acceso/`), solo `profe`
funciona. Con `agente`, el formulario no deja entrar.

### 11.2 Por qué ocurre: **no es un error, es el diseño**

Hay que distinguir dos cosas que se confunden:

| | Iniciar sesión (web) | Autenticarse con token (API) |
|---|---|---|
| Dónde | Navegador, en `/acceso/` | Cualquier cliente, en `/api/` |
| Mecanismo | Usuario + contraseña | Token en la cabecera |
| Identifica a | Una persona | Un programa o una persona |
| ¿El agente debe poder? | **No** | **Sí** |

La interfaz web es **la consola de gestión de la persona**. Por eso exige el rol
`persona` (`is_staff`). Un agente no tiene consola propia: se supone que opera por API,
que es justamente el canal restringido.

### 11.3 Las dos razones concretas, comprobadas

**Razón 1 — el usuario `agente` no tiene contraseña usable.**
`seed_quiz` lo crea con `set_unusable_password()`, así que no hay contraseña con la que
autenticarse. Comprobado: `password usable=False`.

**Razón 2 — aunque tuviera contraseña, sería rechazado.**
Se comprobó asignándole una contraseña temporal:

```
login agente CON clave  ->  403
/examenes/              ->  403
/preguntas/             ->  403
```

El login es aceptado (la identidad es válida), pero **todas las pantallas devuelven 403**,
porque `StaffRequiredMixin` exige el rol `persona`. Tras la prueba se restauró la cuenta
a «sin contraseña».

### 11.4 Qué configuración revisar

| Archivo | Qué mirar | Valor actual |
|---|---|---|
| `quiz/services.py` | Tabla de roles `METHODS_BY_ROLE` | `person` = todo; `agent` = sin `DELETE` |
| `quiz/permissions.py` | `AgentPermission`, que consulta esa tabla | aplica a la API |
| `quiz/web_mixins.py` | `StaffRequiredMixin`, que aplica la misma tabla | exige rol `persona` en la web |
| `quiz/management/commands/seed_quiz.py` | `set_unusable_password()` y el grupo `agente` | el agente no tiene clave |

**No hay que cambiar nada** para que el agente use la API: ya funciona, con GET, POST,
PUT y PATCH. Lo único que no puede es borrar, por diseño.

Si algún día se quisiera que el agente tuviera una sesión web, habría que revisar esas
cuatro filas del equipo de agentes (arquitecto y seguridad) y aceptar el riesgo: una
interfaz que borra queda accesible a una identidad autónoma.

## 12. Ejemplo completo desde una aplicación externa

```python
import os
import requests

BASE = os.environ.get("QUIZ_URL", "http://127.0.0.1:8000")
HUMANO = {"Authorization": f"Token {os.environ['QUIZ_TOKEN_HUMANO']}"}
AGENTE = {"Authorization": f"Token {os.environ['QUIZ_TOKEN_AGENTE']}"}

# El agente consulta y crea
print(requests.get(f"{BASE}/api/exams/", headers=AGENTE).status_code)          # 200
print(requests.get(f"{BASE}/api/questions/", headers=AGENTE).json()["count"])  # nº de preguntas

nueva = requests.post(f"{BASE}/api/questions/", headers=AGENTE, json={
    "exam": 1,
    "text": "¿Qué es una API REST?",
    "choices": [
        {"text": "Un estilo de arquitectura sobre HTTP", "is_correct": True},
        {"text": "Un lenguaje de programación", "is_correct": False},
    ],
})
print(nueva.status_code)          # 201
pregunta_id = nueva.json()["id"]

# El agente intenta borrar y no puede
print(requests.delete(f"{BASE}/api/questions/{pregunta_id}/", headers=AGENTE).status_code)  # 403

# La persona sí puede
print(requests.delete(f"{BASE}/api/questions/{pregunta_id}/", headers=HUMANO).status_code)  # 204
```

## 13. Desde un agente de IA

El proyecto incluye una **pasarela cerrada** (`agent/gateway.py`) que no deja que el modelo
haga peticiones directamente. El modelo solo emite una intención JSON y la pasarela
decide:

```bash
python -m agent --intent '{"op": "exams_list"}'
python -m agent --intent '{"op": "questions_list", "query": {"search": "prefetch"}}'
```

Operaciones destructivas **nunca** se ejecutan por decisión del modelo: devuelven un plan
con un hash que una persona debe aprobar con su propio token:

```bash
python -m agent --intent '{"op": "exams_destroy", "path": {"id": 1}}'
# -> {"status": "approval_required", "plan": {...}}

python -m agent --intent '{"op": "exams_destroy", "path": {"id": 1}}' --approve <hash>
# -> se aplica, usando el token de la persona
```

Esto es **una segunda barrera**, además de la del servidor. Aunque la pasarela tuviera un
fallo y dejara pasar un borrado, el token del agente recibiría **403**.

---

**Documentos relacionados:** `GUIA-DE-EJECUCION.md` (instalación y puesta en marcha),
`README.md` (uso diario), `Entregable.md` (informe técnico con la tabla de la API).