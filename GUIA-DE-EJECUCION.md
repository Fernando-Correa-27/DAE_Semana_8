# Guía de ejecución — API de cuestionarios con Django REST Framework

Guía completa para que otra persona instale, configure, ejecute y pruebe el proyecto
sin necesitar instrucciones adicionales. Todo lo que sigue se ha ejecutado y verificado
en este repositorio.

---

## 0. Requisitos previos

| Requisito | Versión verificada |
|---|---|
| Python | 3.14.4 (funciona desde 3.10) |
| Django | 5.2.18 |
| djangorestframework | 3.18.3 |
| drf-spectacular | 0.30.0 |
| requests | 2.34.2 |

No hace falta ningún servidor de base de datos: el proyecto usa **SQLite**.

## 1. Preparar el entorno

```bash
# Windows PowerShell
python -m venv .venv
.venv\Scripts\Activate.ps1

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

## 2. Aplicar migraciones

```bash
python manage.py migrate
```

Crea `db.sqlite3` y las tablas `quiz_exam`, `quiz_question`, `quiz_choice`, más las
tablas de autenticación y de sesión. Es idempotente: se puede repetir sin miedo.

## 3. Cargar los datos de prueba

```bash
python manage.py seed_quiz
```

Crea 2 exámenes con 8 preguntas y sus opciones. **Por seguridad, los tokens ya no se
imprimen en pantalla.** Si los necesitas:

```bash
python manage.py seed_quiz --show-tokens
```

Obtendrás los tokens de `profe` (la persona, puede borrar) y de `agente` (el agente,
nunca puede borrar). Guárdalos en variables de entorno:

```powershell
$env:QUIZ_URL        = "http://127.0.0.1:8000"
$env:QUIZ_TOKEN_HUMANO = "<pega aquí el token de profe>"
$env:QUIZ_TOKEN_AGENTE = "<pega aquí el token de agente>"
```

El comando es **idempotente**: al repetirlo conserva los mismos tokens.

### 3.1 Habilitar el acceso a la interfaz web

El usuario `profe` nace con contraseña inservible. Para entrar en la interfaz:

```bash
python manage.py seed_quiz --password "TU_CLAVE"
```

## 4. Iniciar el servidor

```bash
python manage.py runserver
```

| URL | Qué es |
|---|---|
| `http://127.0.0.1:8000/` | Interfaz web de gestión |
| `http://127.0.0.1:8000/acceso/` | Inicio de sesión de la interfaz |
| `http://127.0.0.1:8000/api/` | Índice del enrutador |
| `http://127.0.0.1:8000/api/exams/` | API de exámenes |
| `http://127.0.0.1:8000/api/questions/` | API de preguntas |
| `http://127.0.0.1:8000/api/options/` | API de opciones |
| `http://127.0.0.1:8000/api/docs/` | Documentación navegable (Swagger UI) |
| `http://127.0.0.1:8000/api/schema/` | Contrato OpenAPI en JSON |

> `api/docs/` carga Swagger UI desde un CDN, por lo que **necesita conexión a
> Internet** para verse. `api/schema/` y toda la API funcionan sin Internet.

## 5. Probar la API

### 5.1 Con la API navegable

1. Abre `http://127.0.0.1:8000/api/docs/`.
2. Pulsa **Authorize**, pega el token y acepta.
3. Ejecuta cada operación con *Try it out* + *Execute*.

### 5.2 Con un cliente HTTP externo

**cURL (Windows PowerShell):**

```powershell
curl.exe -H "Authorization: Token $env:QUIZ_TOKEN_HUMANO" `
         -H "Content-Type: application/json" `
         http://127.0.0.1:8000/api/exams/
```

**Postman / Insomnia:**
1. Nueva petición, método `GET`, URL `http://127.0.0.1:8000/api/exams/`.
2. Pestaña **Headers** → `Authorization` → `Token` → pega el token.
3. Para `POST`/`PUT`/`PATCH`: pestaña **Body** → *raw* → *JSON*, y escribe el cuerpo.

**Python:**

```python
import os, requests
B = "http://127.0.0.1:8000"
H = {"Authorization": f"Token {os.environ['QUIZ_TOKEN_HUMANO']}"}

requests.get(f"{B}/api/exams/", headers=H)
requests.post(f"{B}/api/questions/", headers=H, json={
    "exam": 1,
    "text": "¿Qué es una API REST?",
    "choices": [
        {"text": "Un estilo de arquitectura sobre HTTP", "is_correct": True},
        {"text": "Un lenguaje de programación", "is_correct": False},
    ],
})
```

## 6. Ejecutar las pruebas

```bash
python manage.py test                    # todo
python manage.py test quiz.tests.test_api
python manage.py test quiz.tests.test_options_api
```

Resultado verificado en la última ejecución:

```
Ran 365 tests in 17.885s

OK
```

## 7. Comprobar la configuración

```bash
python manage.py check                   # debe salir sin avisos
python manage.py spectacular --file schema.yml   # regenera el contrato OpenAPI
```

## 8. Variables de entorno

Todas son opcionales en desarrollo.

| Variable | Para qué | Por defecto |
|---|---|---|
| `QUIZ_URL` | Base URL para `quizctl.py` y el agente | `http://127.0.0.1:8000` |
| `QUIZ_TOKEN` | Token con el que llama `quizctl.py` | — |
| `QUIZ_TOKEN_HUMANO` | Token de la persona (aprueba borrados) | — |
| `QUIZ_TOKEN_AGENTE` | Token del agente | — |
| `DJANGO_SECRET_KEY` | Clave de Django | se genera en `.secret_key` |
| `DJANGO_DEBUG` | `1` activa depuración, `0` la apaga | `1` |
| `DJANGO_ALLOWED_HOSTS` | Hosts permitidos, separados por comas | `localhost,127.0.0.1,testserver` |
| `LLM_URL` | Endpoint OpenAI-compatible para el agente | — |
| `LLM_MODEL` | Nombre del modelo local | `local` |

> `.secret_key` se crea solo en el primer arranque, en la raíz del proyecto, y está
> en `.gitignore`. No hay que hacer nada ni copiarlo a ninguna parte.

### 8.1 Ejecutar fuera de desarrollo

```powershell
$env:DJANGO_DEBUG = "0"
$env:DJANGO_SECRET_KEY = "<clave larga y aleatoria>"
$env:DJANGO_ALLOWED_HOSTS = "127.0.0.1,localhost"
python manage.py runserver
```

Si faltan `DJANGO_SECRET_KEY` o `DJANGO_ALLOWED_HOSTS` con `DJANGO_DEBUG=0`, Django
se niega a arrancar con `ImproperlyConfigured`. Es intencionado.

> **Limitación conocida:** con `DEBUG=0`, `runserver` deja de servir `/static/`.
> Haría falta `python manage.py collectstatic` y un servidor estático.

## 9. Cliente de consola `quizctl.py`

```bash
python quizctl.py exams list
python quizctl.py questions list --exam 1 --search orm --json
python quizctl.py questions create --exam 1 --text "¿Qué es REST?" --choice "Un estilo:ok" --choice "Un lenguaje"
python quizctl.py --dry-run questions delete 3
python quizctl.py ops
```

| Código de salida | Significado |
|---|---|
| 0 | funcionó |
| 1 | otro error o mal uso |
| 2 | validación (HTTP 400) |
| 3 | no permitido (HTTP 401 o 403) |
| 4 | no existe (HTTP 404) |
| 5 | error del servidor (5xx) |
| 6 | no hay conexión |

## 10. Frontera del agente (opcional)

```bash
python -m agent --intent '{"op": "exams_list"}'
python -m agent --intent '{"op": "exams_destroy", "path": {"id": 1}}'
```

Operaciones destructivas (R2) nunca se ejecutan por decisión del modelo: devuelven un
plan con hash que debe aprobar una persona supplying su propio token:

```bash
python -m agent --intent '{"op": "exams_destroy", "path": {"id": 1}}' --approve <hash>
```

Requiere `QUIZ_TOKEN_AGENTE` y, para aprobar, `QUIZ_TOKEN_HUMANO`.

## 11. Problemas frecuentes

| Síntoma | Causa y solución |
|---|---|
| `401` en cualquier llamada | Falta la cabecera `Authorization: Token <token>` |
| `403` al borrar | El token es el del agente o el de un usuario sin rol: solo `profe` borra |
| `404` en `/acceso/` con contraseña correcta | Falta ejecutar `seed_quiz --password "CLAVE"` |
| `/api/docs/` en blanco | Sin conexión a Internet: Swagger UI usa un CDN |
| `ImproperlyConfigured` al arrancar | Con `DEBUG=0` faltan `DJANGO_SECRET_KEY` o `DJANGO_ALLOWED_HOSTS` |
| CSS sin estilos | Con `DEBUG=0` hace falta `collectstatic` y un servidor estático |

---

**Documento relacionado:** `Entregable.md` contiene el informe técnico completo con
evidencias reales de todas las operaciones.