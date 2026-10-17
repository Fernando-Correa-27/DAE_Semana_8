# ADR-0001 · Arquitectura de la interfaz web

- **Estado:** aceptada
- **Fecha:** 2026-10-16
- **Decide:** el Arquitecto de software
- **Ámbito:** interfaz gráfica de gestión de exámenes, preguntas y opciones

## Contexto

El objetivo del trabajo es añadir una **interfaz gráfica funcional** a un repositorio que hoy
es deliberadamente *headless*: no hay plantillas, ni estilos, ni formularios, ni admin
(`config/settings.py` no tiene bloque `TEMPLATES`; `INSTALLED_APPS` solo trae `auth`,
`contenttypes`, `rest_framework`, `authtoken`, `drf_spectacular` y `quiz`).

La pregunta de diseño es si esa interfaz se construye como una **SPA con JavaScript**
(React, Vue, Svelte…) o con el **patrón server‑rendered de Django**. El enunciado pide que no
se introduzcan frameworks sin justificación sólida.

Hay un antecedente directo en el curso: el proyecto de la S07 (`blog`) resuelve CRUD completo
—19 plantillas, CBVs, `ModelForm`, parciales, paginación— sin una sola línea de JavaScript de
aplicación. La referencia demuestra por construcción que el patrón server‑rendered basta para
este alcance.

Restricciones reales del entorno de laboratorio:

- `requirements.txt` tiene 4 líneas y no hay `package.json`, ni bundler, ni artefactos de build.
- El aula puede no tener Wi‑Fi.
- La API sigue siendo el contrato máquina de `quizctl.py` y de `agent/`: la UI no la sustituye.
- Requisitos de UI: en español, responsive, navegable solo con teclado, **sin emojis**.

## Alternativas consideradas

**A. SPA con React/Vue (Svelte, Alpine, HTMX…)**
Descartada. Exige una cadena de herramientas (`node`, bundler, transpilación, `node_modules`)
que el repositorio no tiene y que nadie del equipo ha declarado. Duplica la validación: el
formulario del navegador y el serializador del servidor. Añade un segundo lugar donde la
invariante de negocio puede vivir y equivocarse. Con un estado de UI tan trivial
("listar, ver, crear, editar, borrar"), el coste no se devuelve nunca.

**B. Server‑rendered con Bootstrap/Google Fonts por CDN (copia literal de la referencia)**
Descartada. El `base.html` de la referencia depende de `cdn.jsdelivr.net` y
`fonts.googleapis.com` (`dae-s07/.../blog/templates/blog/base.html:9-14`). Si el aula está sin
internet, la interfaz **no funciona**: no se degrada con elegancia, se rompe. Además obliga a
mantener hashes SRI de terceros y es un vector de suministro externo para un laboratorio que
no lo necesita.

**C. Server‑rendered con CSS propia, sin dependencias externas** ← **elegida**

## Decisión

La interfaz se implementa con **plantillas de Django + formularios de Django + CBVs +
una única hoja CSS propia**, sin JavaScript de aplicación, sin CDN y sin paso de compilación.

Elementos concretos:

1. **Plantillas.** `quiz/templates/quiz/` con un `base.html`, un directorio `partials/` para
   los fragmentos reutilizables (`_navbar`, `_messages`, `_pagination`, `_field`,
   `_choice_row`, `*_card`) y una plantilla por pantalla. Plantillas de error propias
   (`403.html`, `404.html`, `500.html`).
2. **Formularios.** `ModelForm` para `Exam` y `Question` + **`formset` en línea** para `Choice`
   (`inlineformset_factory`), que es la forma canónica de Django para "una pregunta con sus
   opciones". El formset es lo que permite validar "≥2 opciones, exactamente 1 correcta"
   con los errores por campo y un `ValidationError` no‑de‑campo.
3. **Vistas.** CBVs genéricas (`ListView`, `DetailView`, `CreateView`, `UpdateView`,
   `DeleteView`) con `paginate_by` y `LoginRequiredMixin`, en un módulo aparte
   (`quiz/web_views.py`) que no toca `quiz/views.py`.
4. **Estilos.** Un único `quiz/static/quiz/css/style.css` con custom properties
   (`:root { --bg-primary: …; --accent: … }`), tal como hace la referencia, pero
   autocontenido: **sin Bootstrap, sin Google Fonts, sin CDN**. La identidad visual la
   escriben esas variables; no hace falta una librería para tener una interfaz cuidada.
5. **Iconos.** SVG inline (como ya hace la referencia en su marca) o etiquetas de texto.
   **Prohibidos los emojis**, por requisito explícito del enunciado.
6. **Responsive y accesibilidad** como parte del CSS, no como plugin: una única hoja con
   `clamp()` para la tipografía, `grid` con `auto-fit/minmax` para las tarjetas, `:focus-visible`
   con anillo visible en todo elemento interactivo, `prefers-reduced-motion` respetado,
   `prefers-color-scheme` para el tema, contraste ≥ 4.5:1 y navigation por tabulador sin
   trampas de foco. Los estados de foco **nunca** se quitan.
7. **JavaScript: solo opcional y progresivo.** El requisito es que la interfaz **funcione sin
   JavaScript**. Si más adelante se añade algo (por ejemplo, añadir dinámicamente una fila de
   opción sin recargar), debe ser un añadido: la página ha de ser usable con el JS desactivado.

## Consecuencias

**A favor**

- `requirements.txt` no crece. Ni una dependencia nueva.
- Sin build: `runserver` y listo, que es exactamente el flujo del `README.md`.
- Funciona sin internet.
- Accesible y navegable por teclado «gratis», porque el HTML lo genera Django.
- Errores de validación por campo y no‑de‑campo, que una SPA tiene que reimplementar.
- La UI sigue siendo HTML accessible: `curl` devuelve algo legible.

**En contra / costes asumidos**

- Cada interacción es un viaje completo al servidor. Es aceptable: el volumen del laboratorio
  es pequeño y no hay requisito de latencia.
- Sin estado en el cliente: la paginación y los filtros son parámetros `GET`, lo que además
  hace que cada vista sea compartible por URL.
- La formularios dinámicos (añadir una opción sin recargar) requerirán un poco de JS
  opcional en el futuro. Está asumido y no se resuelve ahora.

### Consecuencia derivada: **no se añade `django.contrib.admin`**

El admin de Django sería una **segunda vía de escritura** sobre el mismo dominio que no pasa
por la validación de opciones, es decir, un camino donde se pueden guardar preguntas con cero
o con dos opciones correctas sin que nadie se entere. No es lo que pide el objetivo, y cuesta
`staticfiles`, plantillas de admin y superficie de mantenimiento.

La gestión de usuarios no se resiente: `manage.py createsuperuser` y
`manage.py changepassword` ya existen en Django y son suficientes. **No hay alta de usuarios
en la interfaz**, por el mismo motivo: un registro público crea identidades sin auditar en un
dominio donde los roles se definen por `is_staff` y por pertenencia al grupo.

**Si más adelante se quiere el admin**, la condición es que `quiz/admin.py` dele la
validación de opciones al servicio de dominio (`quiz/services.py`, ADR‑0002) mediante un
`ModelForm` con `clean()` propio, para que no exista una cuarta redacción de la invariante.

## Verificación

La decisión se considera correcta si:

1. `python manage.py test` pasa **sin cambiar `test_api.py`, `test_agent.py`, `test_quizctl.py`
   ni las aserciones de `test_permissions.py`**.
2. `python manage.py runserver` sirve la UI con la red desconectada (se comprueba deshabilitando
   la red o viendo que no hay peticiones salientes en la pestaña *Network*).
3. Con JavaScript deshabilitado en el navegador se pueden completar los cinco flujos: listar
   exámenes, ver un examen, crear una pregunta, editarla y borrarla.
4. Todo el recorrido se hace con `Tab`/`Shift+Tab`/`Enter` y el foco siempre es visible.
5. `requirements.txt` sigue teniendo 4 líneas.
