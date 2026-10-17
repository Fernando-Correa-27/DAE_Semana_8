# 04 · Arquitectura y ADR

Volver al [[00-Indice]] · Anterior: [[03-Requisitos-y-aceptacion]] · Siguiente: [[05-Modelos-y-datos]]

## Mapa de la arquitectura

```
Navegador (persona, «profe»)
   │  cookie de sesión + CSRF
   ▼
quiz/web_urls.py → web_views.py ──► quiz/forms.py ─┐
                       │                          │
                       └──────► quiz/queries.py   │  (lecturas)
                                              ▼
                                          quiz/services.py   ◄── LA REGLA, escrita una vez
                                            │        ▲
                          ┌─────────────────┘        │
                          ▼                          │
              quiz/serializers.py ──────────► DRF: quiz/views.py + quiz/urls.py  (/api/…)
                          │                          ▲
                          │  token en cabecera       │ HTTP + token
                          ▼                          │
                   base de datos (SQLite)      quizctl.py   ·   agent/gateway.py → modelo de IA
```

**Dos presentaciones, un suelo.** La API y la interfaz web **no se llaman entre sí**. Las tres piezas que
comparten son: la invariante de negocio, la tabla de roles y la base de datos.

## Las tres decisiones (ADR)

Los ADR completos, con contexto y alternativas descartadas, están en `docs/adr/` (fuera de esta bóveda):

- `docs/adr/0001-arquitectura-de-la-interfaz-web.md`
- `docs/adr/0002-consumicion-del-dominio-desde-la-interfaz.md`
- `docs/adr/0003-regla-de-permisos.md`

### ADR-0001 · Arquitectura de la interfaz web

**Server-rendered**: plantillas de Django + `ModelForm` + `formset` en línea + CBVs + **una única hoja
CSS propia**. Sin JavaScript de aplicación, **sin CDN**, sin paso de compilación y **sin
`django.contrib.admin`**.

- *Descartado:* SPA (React/Vue/Svelte) — exige `node`, bundler y transpilación que el repositorio no
  tiene, duplica la validación y añade un segundo sitio donde la invariante puede equivocarse.
- *Descartado:* server-rendered **con** Bootstrap/Google Fonts por CDN (copia literal de la referencia
  S07) — con el aula sin internet la interfaz no se degrada, **se rompe**.
- *Consecuencia:* `requirements.txt` sigue con **4 líneas**.

### ADR-0002 · Cómo consume la interfaz el dominio

La interfaz **usa el ORM en proceso**, a través de servicios compartidos (`quiz/services.py`).

- *Descartado:* que las vistas web llamen por HTTP a su propia API — obligaría a inventar una identidad
  (un token persistente guardado en el servidor), a depender de que el servidor esté levantado, a
  marcar `csrf_exempt` en la única superficie de escritura por sesión, y a traducir errores JSON a algo
  legible. Y si reutilizara el token fijo de `seed_quiz`, **la frontera de la Parte 3 se desharía**: el
  agente podría borrar desde el navegador con el token de la persona.
- *Descartado:* que cada vista escriba con el ORM por su cuenta — la invariante deja de existir para la
  interfaz y la escritura deja de ser atómica.
- *Consecuencia obligatoria:* **un único validador** compartido por serializador y `formset`
  (R-UI-T5), verificado por `quiz/tests/test_services.py::SameVerdictTests`.

### ADR-0003 · Una sola regla de permisos, dos adaptadores

La regla se expresa con **funciones puras** (`role_of`, `method_of`, `may` en `quiz/services.py`).
Ni DRF ni Django saben cuál es la regla: solo la aplican.

- `quiz/permissions.py::AgentPermission` — adaptador delgado para DRF.
- `quiz/web_mixins.py::StaffRequiredMixin` — adaptador delgado para las CBVs de Django.
- **Un verbo desconocido se deniega a todo el mundo** (deny by default).
- *Consecuencia:* cambiar «quién puede borrar» se cambia **una vez**.

## La tabla de roles

| Rol | read | create | update | delete |
|---|:--:|:--:|:--:|:--:|
| `person` (`is_staff` o `is_superuser`) | sí | sí | sí | **sí** |
| `agent` (grupo `agente`) | sí | sí | sí | **no** |
| `reader` (autenticado sin rol) | sí | no | no | no |
| anónimo | no | no | no | no |
| verbo desconocido | — | — | — | **no** |

`role_of` mira **`is_staff` primero**: un `profe` que además estuviera en el grupo `agente` sigue siendo
persona. El orden de las comprobaciones **es** la regla.

## Dos contratos distintos, a propósito

| Situación | API (`/api/*`) | Interfaz (`/`) |
|---|---|---|
| Anónimo | **401** (falla `TokenAuthentication` antes de evaluar permisos) | **302** al login |
| Autenticado sin permiso | **403** (`AgentPermission`) | **403** con plantilla propia |

Que el anónimo reciba 401 en un sitio y 302 en el otro es correcto: son contratos distintos con clientes
distintos. Lo que no puede pasar es que una de las dos capas se salte la comprobación.

## Decisiones que se tomaron durante la implementación

| Decisión | Resultado |
|---|---|
| `?exam=` con un valor que no es un id | **400** nombrando el parámetro, en vez de ignorarse en silencio y devolver la lista completa |
| ¿Puede el agente modificar exámenes? | **Sí** (crear y modificar), **nunca borrar**. Cierra la ambigüedad de la rúbrica |
| Paginación de la interfaz | **La misma constante** `settings.PAGE_SIZE = 5` que la API |
| `django.contrib.admin` | **No**: sería una segunda vía de escritura que esquivaría RN-01/RN-02 |
| Docker y CI | **No**, por decisión justificada — ver [[11-Docker-y-CI]] |

## Revisión de código

`docs/revision-codigo.md` dio veredicto **CAMBIOS**: 1 bloqueante, 9 importantes y 20 menores. Lo
bloqueante era que la interfaz **reimplementaba** la tabla de roles, prohibido por ADR-0002 y ADR-0003;
se corrigió dejando que `web_mixins.py` pregunte a `services.may_use()`. Los detalles están en
[[09-Pruebas-y-resultados]] y [[12-Limitaciones-y-pendientes]].