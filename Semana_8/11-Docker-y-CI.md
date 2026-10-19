# 11 · Docker y CI

Volver al [[00-Indice]] · Anterior: [[10-Git-y-commits]] · Siguiente: [[12-Limitaciones-y-pendientes]]

## Decisión

**No se incorporan contenedores (Docker) ni integración continua (CI) en esta entrega.** Se deja
constancia escrita para que la ausencia sea una decisión y no un olvido.

Documento completo: `docs/decisiones-docker-ci.md`.

## Por qué NO

### 1. El entorno ya permite desarrollar, probar y entregar sin ellos

- **Cuatro dependencias** en `requirements.txt`. Instalación: `python -m venv` + `pip install -r`.
- **SQLite**, que viene con Python. Sin servidor de base de datos, sin credenciales, sin migración
  inicial.
- **Plantillas y CSS servidos por `runserver`**: sin `node`, sin bundler, sin artefactos de compilación.
- **Una suite, un comando**: `python manage.py test` → **`Ran 365 tests ... OK`**.

Docker no añade nada que falte para hacer el trabajo del laboratorio.

### 2. El alcance es académico

Los cuatro entregables son el contrato, el cliente de consola, los permisos y la frontera del agente, más
la interfaz de gestión. Reproducir una imagen o mantener un runner es trabajo de **infraestructura**, que
no puntúa en el objetivo del laboratorio. Sería tiempo robado a los entregables.

### 3. La CI exigiría operar sobre un remoto

Una canalización solo existe si hay:

1. un repositorio remoto,
2. credenciales de despliegue,
3. un servicio de integración continua que mantener.

**La misión prohíbe hacer `push` sin autorización.** Una CI sin esa autorización no podría ejecutar sus
integraciones sin incumplir la norma: quedaría **declarada pero sin ejecutar**, que es peor que no
declararla.

### 4. Ninguna dependencia nueva

Ni `docker`, ni `pytest`, ni `coverage`. `requirements.txt` sigue con **4 líneas**.

## Qué asumimos como coste

- **La calidad depende de que alguien lance las pruebas.** No hay red de seguridad automática: si nadie
  ejecuta `python manage.py test`, nadie detecta una regresión. Es el riesgo R5 de `AGENTS.md`, asumido de
  forma consciente.
- **El entorno no es reproducible por imagen.** Quien clone el repositorio necesita Python 3.14 y las
  cuatro dependencias; no basta con `docker run`.
- **No hay despliegue**, y el laboratorio **arranca en modo desarrollo por defecto** (`DJANGO_DEBUG=1`), sin
  HTTPS y sin servidor estático. Desde `a82978e` ya no hay secretos en el código ni valores fijos de
  `DEBUG`: ambos salen del entorno y el arranque falla cerrado sin ellos. Es correcto en un aula e
  incorrecto fuera de ella (ver [[08-Seguridad]] y [[12-Limitaciones-y-pendientes]]).

## Mitigaciones sin infraestructura

| En vez de CI | Se hizo |
|---|---|
| Ejecución automática en cada commit | Un **único comando** protege todo el conjunto |
| Comprobación de configuración | `python manage.py check` |
| Detección de cambios de contrato | El contrato es **regenerable y comparable**: `python manage.py spectacular --file schema.yml` |
| Entorno limpio de pruebas | `python manage.py test` crea su propia base de datos |

## Mejora posible, si el alcance crece

| Propuesta | Qué exigiría |
|---|---|
| Pruebas automáticas en cada commit | Un remoto **autorizado** y un runner |
| Imagen de contenedor | `Dockerfile` + composición para SQLite y un lugar donde publicarla |
| Medición de cobertura | `coverage` como dependencia de desarrollo |

**Condición de activación:** que el proyecto salga del aula (servidor, despliegue o más personas) **y** que
exista autorización explícita para operar sobre el remoto. Mientras no se den las dos, la decisión se
mantiene.

## Agentes afectados

Los agentes **DevOps** e **infraestructura** (y el de **rendimiento**, por la misma ausencia de SLA)
quedaron declarados en [[02-Equipo-de-agentes]] como **opcionales y sin uso**, precisamente porque este
proyecto no tiene despliegue, ni contenedores, ni objetivo de escala. Ver
[[12-Limitaciones-y-pendientes]] para el resto de lo que queda abierto.