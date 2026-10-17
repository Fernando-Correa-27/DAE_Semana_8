# 12 · Limitaciones y pendientes

Volver al [[00-Indice]] · Anterior: [[11-Docker-y-CI]]

## Limitaciones conocidas del proyecto

| # | Limitación | Por qué |
|---|---|---|
| L1 | **No es configuración de producción** | Arranca en modo desarrollo por defecto (`DJANGO_DEBUG=1`) y sin HTTPS. Ya no hay secretos en el código (ver [[08-Seguridad]]), pero es un laboratorio en `127.0.0.1` |
| L2 | **Base SQLite** | Sin servidor, sin concurrencia real. Las conclusiones de rendimiento y escala **no son extrapolables**. `runserver` no es concurrente. |
| L3 | **Sin CI** | La calidad depende de que alguien ejecute las pruebas. Decisión consciente: [[11-Docker-y-CI]]. |
| L4 | **Sin linter en el entorno** | No hay `flake8`, `ruff` ni `pycodestyle`: el estilo PEP 8 se ha revisado a mano. |
| L5 | **La interfaz solo es para `is_staff`** | No hay alta de usuarios ni gestión de roles desde la UI. Es deliberado: los roles se definen por `is_staff` y por el grupo `agente`. |
| L6 | **Sin i18n** | `USE_I18N = True` pero los mensajes de negocio están en **español literal**, sin `gettext`. Es intencionado: `test_api.py` comprueba el texto exacto del 400. |
| L7 | **Contrato sin examples de respuesta** | `drf-spectacular` genera el esquema pero `/api/docs/` no muestra cuerpos de ejemplo para 201 ni 400. |
| L8 | **Sin throttling** | `POST /api/questions/` no tiene límite de peticiones. Sobredimensionado para un aula. |
| L9 | **Swagger UI carga de un CDN** | Sin internet, `/api/docs/` se ve sin estilos. Solo afecta a la documentación del contrato, no a la interfaz. |
| L10 | **`/api/exams/` sin filtro de búsqueda** | Asimetría con `/api/questions/`, que sí tiene `?search=`. No es un defecto, se dejó constancia. |
| L11 | **Login de la interfaz sin límite de intentos** | `/acceso/` no aplica ninguna política de intentos: ni retardo, ni bloqueo, ni registro (SUI-03). **Riesgo aceptado para el laboratorio y documentado como abierto**, no resuelto. Mitigante parcial: **no hay enumeración de usuarios**, el mensaje de fallo es genérico e idéntico exista o no la cuenta |
| L12 | **Con `DEBUG=0` falta servidor estático** | Con `DJANGO_DEBUG=0`, `runserver` deja de servir `/static/` y la interfaz se ve sin su hoja de estilos. Harían falta `collectstatic` y un servidor estático real (y HTTPS), que es **despliegue**, no laboratorio. Es la razón por la que el aula se queda en `DJANGO_DEBUG=1` |
| L13 | **La API no tiene listado global; la UI sí** | Solo existen los recursos de exámenes y preguntas (`quiz/urls.py`): no hay un listado transversal de todo el dominio por la API, mientras que la interfaz **sí** ofrece panel, listado de exámenes, listado de preguntas y detalle. Asimetría entre las dos presentaciones |
| L14 | **`is_correct` visible para cualquier token autenticado en la API** | `ChoiceSerializer` expone `is_correct` y el rol `reader` puede leer: cualquier token autenticado ve la respuesta correcta de cada pregunta (SEC-08 / SUI-09). **Cerrado solo para la interfaz** (403 a no `is_staff`). Requiere decidir entre serializadores de lectura separados o documentarlo como decisión consciente |

## Pendientes con decisión del usuario

| ID | Pregunta | Impacto |
|---|---|---|
| **Q-01** | ¿Cuál es el texto oficial de la rúbrica del campus? («tabla de API» = tabla documentada o tabla en pantalla) | Se cubren **ambas** lecturas, pero no se puede cerrar sin el campus |
| **Q-04** | ¿`question_count` debe aparecer siempre, incluso en las respuestas de escritura (201/200)? | Hoy falta la clave: inconsistencia visible para cualquier consumidor |
| **Q-07** | ¿`Exam.title` debe ser único? | Se permiten títulos repetidos; en la tabla de la UI aparecen filas indistinguibles |
| **Q-08** | ¿Se mantiene `manage.py test` o se adopta `pytest`/`pytest-django`? | El repositorio usa `manage.py test` y nada obliga a cambiarlo |

Ver `docs/requisitos.md` §14 para la lista completa de preguntas del análisis.

## Pendientes técnicos, sin decisión pendiente

| # | Qué falta | Prioridad |
|---|---|---|
| P1 | **Matriz completa por rol en la interfaz**: el agente edita y no ve «Eliminar». Hoy hay un 403 global correctamente probado, que es otra cosa | Recomendada (lo pedía ADR-0003 en su verificación) |
| P2 | **Contraste ≥ 4.5:1 verificado con herramienta**, no a ojo | Recomendada (R-UI-11 admite revisión manual, pero una herramienta lo cierra) |
| P3 | **`Semana_8/` no está en `.gitignore`**: un `git add -A` metería la bóveda de notas en el repositorio | Alta, y es una decisión del **coordinador** |
| P4 | **`OrderingFilter`** con `?ordering=-id`, documentado en el contrato | Opcional |
| P5 | **`UniqueConstraint` de `Exam.title`** y normalización de espacios | Opcional, depende de Q-07 |
| P6 | **Ejemplos de respuesta** en el contrato (`extend_schema` para 201 y 400) | Opcional |
| P7 | **Swagger UI con assets locales**, sin CDN | Opcional, depende de si se exige funcionar sin internet |
| P8 | **Servidor estático y HTTPS** para poder arrancar con `DJANGO_DEBUG=0` (`collectstatic` + un servidor real) | Importante **solo** si el proyecto saliera del aula; el conmutador por entorno ya está hecho |
| P9 | **Medición de cobertura** con `coverage` | Opcional |
| P10 | Restricción de unicidad de los **textos de opción** dentro de una misma pregunta | Opcional, hoy no está en el modelo |
| P11 | **Límite de intentos en el login** de la interfaz (SUI-03) | Media. Aceptada como riesgo del laboratorio, pero queda abierta |
| P12 | **Política de `is_correct`** en la API: separadores de lectura o decisión documentada (SEC-08 / SUI-09) | Media. Necesita decisión del arquitecto |
| P13 | **Listado global del dominio en la API** (hoy solo exámenes y preguntas) | Baja, depende de si la rúbrica lo pide (Q-01) |

## Riesgos vivos

| # | Riesgo | Estado |
|---|---|---|
| R1 | `DEBUG = True` por defecto (ya **no** con `SECRET_KEY` de reserva en el código) | **Mitigado**: la clave sale del entorno o de `.secret_key` generado, y con `DJANGO_DEBUG=0` el arranque falla cerrado. Sigue siendo el modo por defecto |
| R2 | Permisos sin implementar (el agente podía borrar) | **Resuelto** |
| R3 | *Prompt injection* en la frontera del agente | **Mitigado**: lista cerrada, contrato verificado, texto tratado como dato |
| R4 | SQLite: sin conclusiones de escala | **Vigente**, aceptado para el laboratorio |
| R5 | Sin CI | **Vigente**, asumido: [[11-Docker-y-CI]] |
| R6 | Duplicación de la regla de roles entre API e interfaz | **Resuelto**: los dos adaptadores consultan la tabla de `quiz/services.py` |
| R7 | Filtrar la `SECRET_KEY` permite falsificar cookies de sesión | **Resuelto** en `a82978e` (SUI-01): no hay clave en el código y la del entorno es obligatoria con `DEBUG=0` |
| R8 | Swagger UI depende de un CDN externo | **Vigente**, menor, afecta solo a la documentación |
| R9 | Login de la interfaz **sin límite de intentos** (fuerza bruta contra la contraseña del profesorado) | **ABIERTO y aceptado** para el laboratorio. Sin enumeración de usuarios |
| R10 | `is_correct` expuesto a cualquier token autenticado por la API | **Vigente**: cerrado en la interfaz, no en la API. Requiere decisión |
| R11 | Con `DJANGO_DEBUG=0` la interfaz pierde los estilos (sin servidor estático) | **Vigente**: es la razón por la que el aula sigue en `DEBUG=1` |

## Qué **no** se afirma

- No se afirma que nada de esto esté desplegado, publicado ni accesible fuera del aula.
- No se afirma que exista un contenedor o una canalización: **no existen** ([[11-Docker-y-CI]]).
- No se afirma que el contraste de colores esté medido con una herramienta: está revisado a ojo (P2).
- No se afirma que haya una matriz completa de roles en la interfaz: hay un 403 global probado (P1).
- **No se afirma que el login esté protegido contra fuerza bruta**: no hay límite de intentos (L11, P11).
- **No se afirma que con `DJANGO_DEBUG=0` la interfaz se vea completa**: sin servidor estático pierde los
  estilos (L12).
- El texto oficial de la rúbrica **no está en el repositorio**: los cuatro criterios proceden del
  enunciado de la misión (Q-01).