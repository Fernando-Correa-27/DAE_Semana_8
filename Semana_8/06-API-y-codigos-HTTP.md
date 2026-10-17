# 06 · API y códigos HTTP

Volver al [[00-Indice]] · Anterior: [[05-Modelos-y-datos]] · Siguiente: [[07-Interfaz-grafica]]

> La tabla completa, con cuerpos JSON de ejemplo y parámetros, está en el `README.md`. Esta nota es el
> resumen operativo y la **matriz verificada**.

## Autenticación

Cabecera `Authorization: Token <clave>`. Dos capas de permisos: `IsAuthenticated` primero (por eso sin
token es **401**, no 403) y después `quiz.permissions.AgentPermission`, que decide por rol.

## Los dos recursos

| Recurso | Ruta | Verbo mínimo | DELETE |
|---|---|---|---|
| `exams` | `/api/exams/` | agente | solo la persona (204) |
| `questions` | `/api/questions/` | agente | solo la persona (204) |
| raíz del router | `/api/` | cualquiera autenticado | — |
| contrato | `/api/schema/` | **público** | — |
| documentación | `/api/docs/` | **público** | — |

## Endpoints

| Operación | Método y ruta | Rol mínimo | Éxito | Errores |
|---|---|---|---|---|
| `exams_list` | `GET /api/exams/?page=` | lector | 200 | 401, 403 |
| `exams_create` | `POST /api/exams/` | agente | 201 | 400, 401, 403 |
| `exams_retrieve` | `GET /api/exams/{id}/` | lector | 200 | 401, 403, 404 |
| `exams_update` | `PUT`/`PATCH /api/exams/{id}/` | agente | 200 | 400, 401, 403, 404 |
| `exams_destroy` | `DELETE /api/exams/{id}/` | persona | 204 | 401, 403, 404 |
| `questions_list` | `GET /api/questions/?exam=&search=&page=` | lector | 200 | 400, 401, 403, 404 |
| `questions_create` | `POST /api/questions/` | agente | 201 | 400, 401, 403 |
| `questions_retrieve` | `GET /api/questions/{id}/` | lector | 200 | 401, 403, 404 |
| `questions_update` | `PUT`/`PATCH /api/questions/{id}/` | agente | 200 | 400, 401, 403, 404 |
| `questions_destroy` | `DELETE /api/questions/{id}/` | persona | 204 | 401, 403, 404 |

**Parámetros de `questions_list`:** `exam` (id de examen), `search` (subcadena del enunciado,
no distingue mayúsculas), `page`.

**Respuesta paginada:** `{count, next, previous, results}` con **5 elementos por página**
(`settings.PAGE_SIZE = 5`, la misma constante que usa la interfaz web).

## Matriz de códigos verificada en vivo

| Escenario | Código |
|---|---|
| `GET` a listados | **200** |
| `GET` de un recurso inexistente | **404** |
| `POST` válido | **201** |
| `PATCH` válido | **200** |
| `PUT` válido | **200** |
| `DELETE` de la persona | **204** |
| `PUT` con el cuerpo incompleto | **400** |
| Campo obligatorio ausente | **400** |
| Tipo de campo incorrecto | **400** |
| Pregunta con 0 opciones correctas | **400** |
| Pregunta con 2 opciones correctas | **400** |
| Pregunta con una sola opción | **400** |
| `exam` que no existe | **400** |
| `?exam=` con un valor que no es entero | **400** |
| `?page=999` (fuera de rango) | **404** |
| `DELETE` del agente | **403** |
| `POST` o `DELETE` de un lector | **403** |
| Sin token | **401** |
| `/api/schema/` y `/api/docs/` sin token | **200** |

## Tabla de códigos de error

| Código | Causa |
|---|---|
| **400** | Regla del dominio rota, campo obligatorio ausente, tipo incorrecto, `exam` inexistente, `?exam=` no entero. El cuerpo **nombra el campo**. |
| **401** | Sin cabecera `Authorization` o con token inválido. |
| **403** | Autenticado sin permiso: el agente o el lector escriben o borran; verbo desconocido. |
| **404** | El recurso no existe, o `?page=` fuera de rango. |
| **405** | Método HTTP no implementado en esa ruta. |
| **500** | Fallo interno. Con `DEBUG = True` la página técnica de Django muestra detalles internos. |

## Semántica de la actualización

| Operación | Efecto sobre las opciones |
|---|---|
| `PATCH` **sin** `choices` | **No se tocan** |
| `PATCH` **con** `choices` | **Las reemplazan** enteras, de forma atómica |
| `PUT` | Exige el cuerpo completo: falta `exam` o `choices` → **400** |

## El contrato manda

`quiz/views.py` declara el parámetro `exam` en el esquema con `@extend_schema_view` + `OpenApiParameter`,
así que aparece en Swagger UI con su tipo y su descripción. Además, `ALLOWED` de la pasarela del agente es
un **subconjunto de los `operationId` del contrato**: si una operación desaparece del contrato, el agente
deja de ofrecerla. Es una prueba de sincronía, no una convención. Ver [[08-Seguridad]].

## Códigos de salida del cliente de consola

| Código | Significa |
|---|---|
| 0 | funcionó |
| 1 | otro error o mal uso |
| 2 | validación (400) |
| 3 | no permitido (401, 403) |
| 4 | no existe (404) |
| 5 | error del servidor (5xx) |
| 6 | no hay conexión |

## Diferencia con la interfaz web

| Parámetro de búsqueda | API | Interfaz |
|---|---|---|
| Búsqueda por texto | `?search=` | `?q=` |
| Filtro por examen | `?exam=` (no entero → **400**) | `?exam=` (no entero → **404**) |
| Paginación | `?page=` | `?page=` |

La diferencia de comportamiento ante un valor inválido es **intencionada**: son dos contratos distintos.
Ver [[07-Interfaz-grafica]].