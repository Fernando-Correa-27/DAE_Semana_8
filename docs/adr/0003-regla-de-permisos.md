# ADR-0003 · Una sola regla de permisos, dos adaptadores

- **Estado:** aceptada
- **Fecha:** 2026-10-16
- **Decide:** el Arquitecto de software
- **Ámbito:** Parte 3 del laboratorio (`quiz/permissions.py`) y su reutilización por la interfaz
- **Depende de:** [ADR-0001](0001-arquitectura-de-la-interfaz-web.md),
  [ADR-0002](0002-consumicion-del-dominio-desde-la-interfaz.md)

## Contexto

La Parte 3 del laboratorio pide una regla, hoy sin implementar
(`quiz/permissions.py:19-20` devuelve `True`):

> - una persona (`is_staff`) puede hacer cualquier cosa;
> - el grupo «agente» puede leer, crear y modificar, pero **nunca** borrar;
> - cualquier otro usuario autenticado solo puede leer;
> - **un método desconocido se deniega** (deny por default).

La consecuencia de no implementarla no es teórica: con el token del agente se puede borrar
(`quiz/tests/test_permissions.py:34-41`).

Al añadir la interfaz (ADR-0001) aparece un problema nuevo: la UI autentica por **sesión**, no
por token, y sus vistas son CBVs de Django, no `APIView`. Si el permiso vive en una clase de
DRF, la UI tiene que reimplementar la regla — dos redacciones, dos sitios donde olvidarse de
exigir el «nunca borrar». Si la regla vive en una función, ambos adaptadores son tres líneas.

## Decisión

**Una tabla de acciones, dos adaptadores finos.** La regla se expresa con funciones puras de
Python (usuario → acción → sí/no). Ni DRF ni Django saben cuál es la regla; solo la aplican.

```python
# quiz/permissions.py
from rest_framework.permissions import BasePermission

AGENT_GROUP = "agente"

READ, CREATE, UPDATE, DELETE = "read", "create", "update", "delete"

# The only table that maps an HTTP verb to a domain action. A verb that is not
# here is unknown, and an unknown verb is denied.
_BY_METHOD = {
    "GET": READ, "HEAD": READ, "OPTIONS": READ,
    "POST": CREATE, "PUT": UPDATE, "PATCH": UPDATE, "DELETE": DELETE,
}


def role_of(user):
    """None (anonymous) | "person" (is_staff) | "agent" (group «agente») | "reader"."""


def action_for(request):
    """The domain action of a request, or None when the verb is not in the table."""


def may(user, action) -> bool:
    """THE rule. One place. Both the API and the web UI ask this and nothing else."""


class AgentPermission(BasePermission):
    """Thin adapter: HTTP verb -> action -> may(). Denies by default."""

    def has_permission(self, request, view):
        action = action_for(request)
        if action is None:
            return False          # unknown verb: deny by default
        return may(request.user, action)
```

### La regla, escrita una vez

| Rol (`role_of`) | `read` | `create` | `update` | `delete` |
|---|:--:|:--:|:--:|:--:|
| `person` (`is_staff` o `is_superuser`) | sí | sí | sí | **sí** |
| `agent` (grupo «agente») | sí | sí | sí | **no** |
| `reader` (autenticado, sin rol) | sí | no | no | no |
| `None` (anónimo) | no | no | no | no |
| acción `None` (verbo desconocido) | — | — | — | **no** |

`role_of` distingue por **`is_staff` primero**: un `profe` que además estuviera en el grupo
«agente» sigue siendo persona y puede borrar. El orden de las comprobaciones **es** la regla.

### Deny by default, explícitamente

`action_for` devuelve `None` para un verbo fuera de la tabla, y `AgentPermission` traduce
`None` a `False`. No es un detalle de estilo: es el requisito literal de la rúbrica y la
defensa contra un método nuevo que se añada a una vista sin que nadie repase la tabla. Con
`return True` implícito, el fallo es silencioso; con `None`, el fallo es un 403.

### Combinación con `LoginRequired` en la interfaz

Dos capas, en este orden:

1. **Identidad** — `LoginRequiredMixin`: si no hay sesión, `handle_no_permission()` redirige
   a `LOGIN_URL` (**302**). Un anónimo no es «un lector al que se le niega algo»: es nadie.
2. **Autorización** — un mixin propio (`quiz/web_mixins.py`) que llama a `may(request.user,
   action)` y lanza `PermissionDenied` (**403** con `templates/quiz/403.html`) si toca.

| Situación | API (`/api/*`) | Interfaz (`/`) |
|---|---|---|
| Anónimo | **401** — `TokenAuthentication` falla antes de evaluar permisos | **302** al login |
| Autenticado sin permiso | **403** — `AgentPermission` | **403** con plantilla propia |
| Verbo desconocido | **403** — `action_for` → `None` | no aplica: el enrutador HTML no enruta verbos desconocidos |

Que el anónimo reciba **401** en la API y **302** en la UI es correcto: son contratos distintos
con clientes distintos. Lo que no puede pasar es que una de las dos capas se salte la
comprobación.

### La interfaz refleja la regla, no la inventa

La plantilla decide **qué mostrar** con el mismo `may()`, de modo que el agente simplemente no
ve el botón «Eliminar» y el lector no ve «Nueva pregunta». **Eso es comodidad, no seguridad:**
ocultar un enlace no impide nada. La comprobación se repite en `dispatch()`, y lo que manda es
esa. Un formulario oculto sigue siendo una petición POST que el servidor debe rechazar — y por
eso el mixin es el que protege, no el `{% if %}` de la plantilla.

## Consecuencias

**A favor**

- `test_permissions.py` pasa sin modificar (no se toca ninguna aserción del entregable).
- La UI hereda la regla sin escribirla: cambiar «quién puede borrar» se cambia **una vez**.
- Las funciones son puras y se prueban sin HTTP ni base de datos, lo que hace que la clase de
  permiso sea trivialmente auditable por un revisor.
- `agent/gateway.py` puede seguir contando con «el servidor tiene la última palabra»
  (`gateway.py:18-19`): la pasarela R2 sigue siendo necesaria para la *intención*, pero el
  permiso ya no depende solo de ella.

**En contra / costes asumidos**

- Una comprobación de grupo por petición (`user.groups.filter(name=...).exists()`). Se mitiga
  con `prefetch_related("groups")` si un perfil midiera; en el laboratorio es irrelevante y no
  se optimiza.
- `AGENT_GROUP` ya lo exportaba `seed_quiz.py:8`; se conserva el nombre para no romperlo.
- `OPTIONS` se clasifica como `read`. No hay prueba que lo exija; si en el futuro se activa
  `AllowAny` en la raíz del router o MetadataClass, hay que revisarlo explícitamente.
- La comprobación por acción vive en `permissions.py`, que es un módulo de DRF. Se importa
  desde la UI; es aceptable porque es código de Python puro, sin dependencia de DRF en las
  funciones.

## Verificación

1. `python manage.py test quiz.tests.test_permissions` verde **sin editar el fichero**.
2. Las 8 pruebas de la matriz de roles se satisfacen: agente lee/crea/modifica y recibe **403**
   al borrar examen y pregunta; la persona recibe **204** al borrar; el lector lee y recibe
   **403** al crear; sin token hay **401**.
3. Prueba de borde obligatoria: un verbo fuera de la tabla (por ejemplo invocar
   `has_permission` con un `request` de método `"TRACE"`) devuelve `False`. Es el «método
   desconocido denegado» de la rúbrica, y no está cubierto por las pruebas entregadas.
4. Pruebas de UI: el agente **no** recibe 200 en la vista de borrado (403) aunque la plantilla
   oculte el botón; el lector recibe 302/403 según el caso.
5. `quizctl.py questions delete` con `QUIZ_TOKEN_AGENTE` sigue saliendo con **3**.
