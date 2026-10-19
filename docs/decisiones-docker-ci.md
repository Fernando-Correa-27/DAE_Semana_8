# Decisión: por qué NO hay Docker ni CI en este laboratorio

- **Autor:** Documentador
- **Fecha:** 2026-10-16
- **Estado:** decisión cerrada, registrada como mejora posible
- **Ámbito:** alcance del proyecto `dae-s08-api-headless`

## Decisión

**No se incorporan contenedores (Docker) ni integración continua (CI) en esta entrega.** Se deja
constancia escrita para que la ausencia sea una decisión y no un olvido.

## Justificación

1. **El entorno ya permite desarrollar, probar y entregar sin ellos.** El proyecto tiene cuatro
   dependencias (`requirements.txt`), una base de datos **SQLite** que viene con Python, plantillas de
   Django servidas por `runserver` y una suite que se ejecuta con un único comando:
   `python manage.py test` → **`Ran 365 tests ... OK`**. Docker no añade nada que falte para
   desarrollar, probar ni entregar en el aula.
2. **El alcance es académico.** El objetivo son cuatro entregables del laboratorio (contrato, cliente
   de consola, permisos y frontera del agente) más una interfaz de gestión. Reproducir una imagen de
   contenedor o un runner es trabajo de infraestructura que no puntúa en el objetivo del laboratorio.
3. **La CI exigiría operar sobre un remoto.** Una canalización solo existe si hay un repositorio
   remoto, credenciales de despliegue y un servicio de integración continua que mantener. **La misión
   prohíbe hacer `push` sin autorización**, así que una CI ni siquiera podría ejercitar sus
   integraciones sin romper esa norma: quedaría declarada pero sin ejecutar, que es peor que no
   declararla.
4. **`requirements.txt` no crece.** Ninguna de las dos tecnologías exige una dependencia nueva: ni
   `docker`, ni `pytest`, ni `coverage`. La instalación real es `python -m venv` +
   `pip install -r requirements.txt`.

## Consecuencias asumidas

- **La calidad depende de que alguien ejecute las pruebas.** No hay red de seguridad automática: si
  nadie lanza `python manage.py test`, nadie detecta una regresión. Es el riesgo R5 de `AGENTS.md` y
  lo asume de forma consciente.
- **El entorno no es reproducible por imagen.** Quien clone el repositorio necesita Python 3.14 y las
  cuatro dependencias; no basta con `docker run`.
- **No hay despliegue.** El laboratorio **arranca en modo desarrollo por defecto** (`DJANGO_DEBUG=1`), sin
  HTTPS y sin servidor estático. Desde `a82978e` ya no hay secretos en el código ni valores fijos de
  `DEBUG`: ambos salen del entorno y el arranque falla cerrado sin ellos. Es correcto en un aula e
  incorrecto fuera de ella (ver `docs/seguridad.md` y `docs/seguridad-interfaz.md`).

## Cómo se mitiga hoy, sin infraestructura

- Un **único comando** protege todo el conjunto: `python manage.py test`.
- `python manage.py check` valida la configuración en segundos.
- El contrato OpenAPI es **regenerable y comparable**: `python manage.py spectacular --file schema.yml`.

## Mejora posible, si algún día el alcance crece

| Propuesta | Qué exigiría |
|---|---|
| Ejecución automática de las pruebas en cada commit | Un remoto autorizado y un runner. Hoy no hay ninguna de las dos cosas. |
| Imagen de contenedor para reproducir el entorno | Dockerfile + `docker-compose` para SQLite y un lugar donde publicarla. |
| Medición de cobertura | `coverage` como dependencia de desarrollo. |

**Condición de activación:** que el proyecto salga del aula (equipo con servidor, despliegue o
personas adicionales) **y** que exista autorización explícita para operar sobre el remoto. Mientras no
se den las dos, la decisión se mantiene.