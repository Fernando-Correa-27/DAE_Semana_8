# 09 · Pruebas y resultados

Volver al [[00-Indice]] · Anterior: [[08-Seguridad]] · Siguiente: [[10-Git-y-commits]]

## Resultado

```bash
python manage.py test
```

**`Ran 324 tests ... OK`** · y `python manage.py check` → sin problemas.

| Momento | Resultado |
|---|---|
| Antes de empezar | **61 pruebas, 21 fallando**: 18 errores en `test_quizctl` y 3 fallos en `test_permissions` (Partes 2 y 3 sin implementar) |
| Después de `cf61a11` | Partes 2 y 3 implementadas |
| Después de `7c87fd9` | Interfaz web |
| Después de `7992f2a` | Revisión corregida y cobertura ampliada → **324 OK** |

Runner: **`python manage.py test`**. El repositorio no adopta `pytest` ni `pytest-django`, y nada de lo
implementado obliga a cambiarlo.

## Qué cubre cada fichero

| Fichero | Qué prueba |
|---|---|
| `test_api.py` | **El contrato del laboratorio, sin tocar**: serializadores, validaciones, paginación, filtros, `question_count`, sincronía entre el contrato y la pasarela, autenticación declarada |
| `test_agent.py` | Frontera R0/R1/R2, lista cerrada, validación de argumentos, aprobación humana y caducidad del hash, texto hostil, auditoría, adaptador de modelo |
| `test_quizctl.py` | Códigos de salida (0–6), construcción del cuerpo de pregunta (`:ok` final), `--dry-run`, `--json`, `ops`, y el cliente contra un **servidor vivo** |
| `test_permissions.py` | La matriz de roles de la Parte 3 |
| `test_services.py` | **La invariante una sola vez**: el mismo cuerpo inválido recibe el mismo veredicto por el serializador y por el `formset`; resolución de verbos; denegación por defecto; el filtro `?exam=` |
| `test_http_matrix.py` | Matriz de códigos por endpoint, método y rol; verbos no permitidos; raíz del navegador de DRF; frontera sesión/token |
| `test_http_client.py` | El cliente de consola y la pasarela hablando con un servidor real |
| `test_persistence.py` | Un 400 **no persiste nada**, atomicidad del servicio, borrado en cascada |
| `test_query_counts.py` | Número de consultas de API e interfaz — protege contra N+1 y es **contrato** |
| `test_web.py` | Login/logout, CRUD completo por HTTP, 302 del anónimo, 403 por rol, POST sin CSRF, activos servidos sin CDN |
| `test_web_review.py` | Anuncio único del error (un solo `role="alert"`), opción correcta conservada tras un POST inválido, orden de los últimos exámenes, listado de preguntas con filtros, una sola página de 5 |
| `test_web_gaps.py` | Objetos inexistentes, paginación, verbos, sesión, límites de campo, usuario no staff, contenido del detalle |

## Matriz de códigos verificada en vivo

| Escenario | Código |
|---|---|
| `GET` a listados | **200** |
| `GET` de recurso inexistente | **404** |
| `POST` válido | **201** |
| `PATCH` válido | **200** |
| `PUT` válido | **200** |
| `DELETE` de la persona | **204** |
| `PUT` incompleto | **400** |
| Campo obligatorio ausente | **400** |
| Tipo incorrecto | **400** |
| 0 opciones correctas | **400** |
| 2 opciones correctas | **400** |
| Una sola opción | **400** |
| `exam` inexistente | **400** |
| `?exam=` no entero | **400** |
| `?page=999` | **404** |
| `DELETE` del agente | **403** |
| `POST`/`DELETE` de lector | **403** |
| Sin token | **401** |
| `/api/schema/` y `/api/docs/` sin token | **200** |

## Interfaz verificada en vivo

| Escenario | Resultado |
|---|---|
| Login | **200** |
| Panel, listados, formularios, búsqueda/filtros, borrado | **200** |
| Anónimo | **302** al login |
| Usuario no `is_staff` | **403** |

## Lo que las pruebas cubrieron de la revisión de código

| Prueba | Cierra |
|---|---|
| `test_services.py::SameVerdictTests` | La invariante es **una sola** (I5: el fichero no existía) |
| `test_services.py::DenyByDefaultTests` | El verbo desconocido se deniega (I6, requisito de ADR-0003) |
| `test_web_review.py::ChoiceKeptTests` | El POST inválido conserva la opción marcada (I2) |
| `test_web_review.py::SingleAnnouncementTests` | El mensaje de negocio se anuncia una sola vez (I1) |
| `test_query_counts.py` | Número de consultas constante (m6) |
| `test_web_review.py::RecentExamsTests` | Los últimos exámenes son los más nuevos (I4) |
| `test_web_review.py::OnePageSizeTests` | Una sola constante de paginación (I8) |
| `test_web_review.py::QuestionListingTests` | Tabla de preguntas con filtro y búsqueda (I7 / R-UI-02 y R-UI-04) |

## Lo que **no** está cubierto por prueba

Se declara explícitamente para no presentar como verde lo que es una revisión manual:

| Afirmación | Por qué no hay prueba |
|---|---|
| Contraste ≥ 4.5:1 en la hoja de estilos | Revisado a ojo sobre el CSS; el propio requisito (R-UI-11) admite revisión como criterio |
| Matriz completa por rol **en la interfaz** (el agente edita y no ve «Eliminar») | Hoy hay un 403 global correctamente probado; falta la matriz por rol que pedía ADR-0003 |
| `question_count` en las **respuestas de escritura** | Depende de Q-04, sin decidir. Ver [[12-Limitaciones-y-pendientes]] |

## Reglas de la estrategia de pruebas

1. Los cuatro entregables del laboratorio (`test_api`, `test_agent`, `test_quizctl`, `test_permissions`)
   son la base y no se tocan al añadir funcionalidad.
2. Toda regla de negocio necesita su caso inválido: mínimo 2 opciones, exactamente 1 correcta.
3. Todo permiso necesita su matriz: rol × método × recurso.
4. Todo filtro necesita su caso mal escrito (el `?exam=abc` es el ejemplo).
5. Regresión obligatoria tras tocar `settings.py`: **está cubierta** (324 OK).
6. Antes de cerrar un cambio: casos borde y de regresión.

## Verificaciones manuales que complementan las pruebas

| Comando | Para qué |
|---|---|
| `python manage.py check` | Validar la configuración |
| `python manage.py spectacular --file schema.yml` | Regenerar el contrato y compararlo |
| `python manage.py test quiz.tests.test_permissions` | Solo la matriz de roles |
| `python manage.py runserver` | Comprobación en vivo de la interfaz y de la matriz de códigos |

Sin linter instalado en el entorno: **no hay `flake8`, `ruff` ni `pycodestyle`**. El estilo se ha
revisado a mano (PEP 8, nombres en inglés, mensajes en español).