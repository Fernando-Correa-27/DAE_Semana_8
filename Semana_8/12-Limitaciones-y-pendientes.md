# 12 · Limitaciones y pendientes

Volver al [[00-Indice]] · Anterior: [[11-Docker-y-CI]]

## Limitaciones conocidas del proyecto

| # | Limitación | Por qué |
|---|---|---|
| L1 | **No es configuración de producción** | `DEBUG = True` y `SECRET_KEY` de reserva. Es un laboratorio en `127.0.0.1`. Ver [[08-Seguridad]]. |
| L2 | **Base SQLite** | Sin servidor, sin concurrencia real. Las conclusiones de rendimiento y escala **no son extrapolables**. `runserver` no es concurrente. |
| L3 | **Sin CI** | La calidad depende de que alguien ejecute las pruebas. Decisión consciente: [[11-Docker-y-CI]]. |
| L4 | **Sin linter en el entorno** | No hay `flake8`, `ruff` ni `pycodestyle`: el estilo PEP 8 se ha revisado a mano. |
| L5 | **La interfaz solo es para `is_staff`** | No hay alta de usuarios ni gestión de roles desde la UI. Es deliberado: los roles se definen por `is_staff` y por el grupo `agente`. |
| L6 | **Sin i18n** | `USE_I18N = True` pero los mensajes de negocio están en **español literal**, sin `gettext`. Es intencionado: `test_api.py` comprueba el texto exacto del 400. |
| L7 | **Contrato sin examples de respuesta** | `drf-spectacular` genera el esquema pero `/api/docs/` no muestra cuerpos de ejemplo para 201 ni 400. |
| L8 | **Sin throttling** | `POST /api/questions/` no tiene límite de peticiones. Sobredimensionado para un aula. |
| L9 | **Swagger UI carga de un CDN** | Sin internet, `/api/docs/` se ve sin estilos. Solo afecta a la documentación del contrato, no a la interfaz. |
| L10 | **`/api/exams/` sin filtro de búsqueda** | Asimetría con `/api/questions/`, que sí tiene `?search=`. No es un defecto, se dejó constancia. |

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
| P8 | **`DEBUG`/`SECRET_KEY` con conmutador por entorno** y arranque que falle sin `DJANGO_SECRET_KEY` | Importante **solo** si el proyecto saliera del aula |
| P9 | **Medición de cobertura** con `coverage` | Opcional |
| P10 | Restricción de unicidad de los **textos de opción** dentro de una misma pregunta | Opcional, hoy no está en el modelo |

## Riesgos vivos

| # | Riesgo | Estado |
|---|---|---|
| R1 | `DEBUG = True` + `SECRET_KEY` de reserva | **Vigente**, documentado. Crítico fuera del aula |
| R2 | Permisos sin implementar (el agente podía borrar) | **Resuelto** |
| R3 | *Prompt injection* en la frontera del agente | **Mitigado**: lista cerrada, contrato verificado, texto tratado como dato |
| R4 | SQLite: sin conclusiones de escala | **Vigente**, aceptado para el laboratorio |
| R5 | Sin CI | **Vigente**, asumido: [[11-Docker-y-CI]] |
| R6 | Duplicación de la regla de roles entre API e interfaz | **Resuelto**: los dos adaptadores consultan la tabla de `quiz/services.py` |
| R7 | Filtrar `SECRET_KEY` permite falsificar cookies de sesión | **Vigente**, consecuencia de R1 |
| R8 | Swagger UI depende de un CDN externo | **Vigente**, menor, afecta solo a la documentación |

## Qué **no** se afirma

- No se afirma que nada de esto esté desplegado, publicado ni accesible fuera del aula.
- No se afirma que exista un contenedor o una canalización: **no existen** ([[11-Docker-y-CI]]).
- No se afirma que el contraste de colores esté medido con una herramienta: está revisado a ojo (P2).
- No se afirma que haya una matriz completa de roles en la interfaz: hay un 403 global probado (P1).
- El texto oficial de la rúbrica **no está en el repositorio**: los cuatro criterios proceden del
  enunciado de la misión (Q-01).