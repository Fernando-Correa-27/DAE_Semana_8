# 01 · Auditoría inicial

Volver al [[00-Indice]] · Siguiente: [[02-Equipo-de-agentes]]

## Punto de partida

El repositorio `dae-s08-api-headless` llegó con **un único commit** (`5bdd1fa`) y **sin ningún
documento propio**: ni `AGENTS.md`, ni `opencode.json`, ni definiciones de agentes. Todo lo que hay en
`docs/` y en esta bitácora se escribió durante el trabajo.

## Hechos comprobados en la primera inspección

- **Alcance**: API REST headless de cuestionarios (exámenes / preguntas / opciones), sin interfaz de
  usuario. Laboratorio extra de la S08.
- **Stack**: Python + Django 5.2–6.x (`manage.py` fija `config.settings`), Django REST Framework,
  `drf-spectacular`, `requests`. Base de datos **SQLite** de desarrollo.
- **Autenticación**: token en la cabecera `Authorization` (`TokenAuthentication`), permisos por defecto
  `IsAuthenticated` + `quiz.permissions.AgentPermission`.
- **Paquetes**: `config/` (settings, urls), `quiz/` (modelos, serializadores, vistas, rutas, permisos,
  comando `seed_quiz`, pruebas), `agent/` (pasarela cerrada modelo↔API y adaptador LLM opcional).
- **Dos entregables sin hacer**: `quizctl.exit_code_for`, `quizctl.build_question_payload` (Parte 2) y
  `quiz.permissions.AgentPermission`, que devolvía `True` (Parte 3).
- **Artefactos ya ignorados por git**: `agent_audit.jsonl`, `schema.yml`, `db.sqlite3`.

## Línea base de pruebas

| Momento | Resultado |
|---|---|
| Antes de empezar | **61 pruebas, 21 fallando**: 18 errores en `test_quizctl` y 3 fallos en `test_permissions`, por las Partes 2 y 3 sin implementar |
| Al cierre | **`Ran 324 tests ... OK`** |

`test_api` y `test_agent` pasaban desde el principio; el hueco estaba íntegro en los dos entregables
pendientes.

## Riesgos que se detectaron al principio

| # | Riesgo |
|---|---|
| R1 | `SECRET_KEY` con valor de reserva y `DEBUG = True`: inviable fuera del aula |
| R2 | Permisos sin implementar: cualquier token autenticado podía **borrar** |
| R3 | Frontera del agente: riesgo de *prompt injection* si se relajaba la validación |
| R4 | SQLite: las conclusiones de rendimiento y escala son orientativas |
| R5 | Sin CI: la calidad depende de que alguien ejecute las pruebas |

## El proyecto de referencia: S07 (`dae-s07-orm-con-ia`)

> **Solo lectura. No se escribió ni un archivo en ese repositorio**, y su misión prohibía expresamente
> hacerlo.

Es el proyecto de la semana 7: un **blog Django con plantillas**. Se consultó para conocer el patrón de
interfaz del curso:

- CBVs (`ListView`, `DetailView`, `CreateView`, `UpdateView`, `DeleteView`).
- Plantillas con `base.html` más parciales.
- `ModelForm` para los formularios, admin de Django, paginación.
- Sesiones, `messages`, CSRF, `auth`, `STATICFILES_DIRS`.
- Pruebas por app.

## Qué se aprendió de S07 (y se aplicó)

1. **El patrón server-rendered basta** para un CRUD completo: 19 plantillas y cero líneas de JavaScript
   de aplicación. Eso justificó la decisión central de la interfaz (ver [[04-Arquitectura-y-ADR]]).
2. **Los tokens de CSS** (`--bg-primary`, `--accent`, …) dan una interfaz cuidada sin biblioteca: la
   identidad visual la escriben las variables.
3. **Lo que NO se copió, y por qué**: el `base.html` de la referencia depende de `cdn.jsdelivr.net` y
   `fonts.googleapis.com`. Con el aula sin internet eso **no se degrada, se rompe**. Aquí la hoja CSS es
   propia, autocontenida y sin CDN.
4. **Tampoco se copió el `admin`**: sería una segunda vía de escritura sobre el mismo dominio, capaz de
   guardar preguntas con cero o dos opciones correctas sin pasar por la validación.
5. **Se copió la disciplina de pruebas por app** y el patrón de `ModelForm` + `formset` en línea para
   «una pregunta con sus opciones».

## Lo que no se encontró en el repositorio

- Sin `Dockerfile`, sin CI, sin configuración de despliegue.
- Sin red de pruebas ejecutadas automáticamente.
- Sin el texto oficial de la rúbrica (está en el campus virtual). Los cuatro criterios del enunciado
  proceden de la misión, no de un documento leído. Ver [[03-Requisitos-y-aceptacion]].