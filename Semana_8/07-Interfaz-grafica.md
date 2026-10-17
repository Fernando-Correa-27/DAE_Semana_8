# 07 · Interfaz gráfica

Volver al [[00-Indice]] · Anterior: [[06-API-y-codigos-HTTP]] · Siguiente: [[08-Seguridad]]

## Qué es

Una capa **server-rendered** de gestión de exámenes, preguntas y opciones, para que el profesorado pueda
trabajar sin usar la API a mano. **No sustituye a la API**: las dos son presentaciones del mismo dominio
(ver [[04-Arquitectura-y-ADR]]).

## Decisiones de diseño

| Decisión | Por qué |
|---|---|
| **Server-rendered** (plantillas Django + `ModelForm` + `formset` en línea + CBVs) | El alcance es un CRUD. Una SPA exigiría `node`, bundler y transpilación, y añadiría un segundo sitio donde la invariante puede equivocarse. La referencia S07 demuestra por construcción que el patrón basta. |
| **Sin CDN** | El aula puede no tener Wi-Fi. El `base.html` de la referencia depende de `cdn.jsdelivr.net` y `fonts.googleapis.com`: sin internet **no se degrada, se rompe**. Aquí la hoja CSS es propia y autocontenida. |
| **Sin JavaScript obligatorio** | Todo el recorrido (listar, ver, crear, editar, borrar) se completa con el JS desactivado. Los radios de «opción correcta» funcionan por nombre común en el HTML, sin script. |
| **Sin `django.contrib.admin`** | Sería una **segunda vía de escritura** sobre el mismo dominio, capaz de guardar preguntas con cero o dos opciones correctas sin pasar por la validación. Sin admin no existe esa vía. |
| **Tokens CSS** | Custom properties en `:root` (`:root { --bg-primary: …; --accent: … }`) escriben la identidad visual. Ningún color literal fuera de `:root`. Una interfaz cuidada no necesita una librería. |
| **Accesible por CSS, no por plugin** | `:focus-visible` con anillo visible en todo elemento interactivo, contraste ≥ 4.5:1, `prefers-reduced-motion` respetado, `prefers-color-scheme`, `clamp()` para la tipografía, `grid` con `auto-fit/minmax` para las tarjetas, tabulación sin trampas de foco. **Los estados de foco nunca se quitan.** |
| **Sin emojis** | Requisito explícito del enunciado. Los iconos son SVG inline o etiquetas de texto. |
| **En español** | Consistente con los mensajes de la API (RN-08). |
| **Una sola constante de paginación** | `settings.PAGE_SIZE = 5` para API e interfaz: «Anterior/Siguiente» significa lo mismo en las dos. |

## Cómo entrar

| Dato | Valor |
|---|---|
| URL | `http://127.0.0.1:8000/acceso/` |
| Usuario | `profe` |
| Contraseña | la fijada con `python manage.py seed_quiz --password "CLAVE"`, o con `python manage.py changepassword profe` |

**Detalle importante:** `profe` nace con `set_unusable_password()`, porque la API no usa contraseñas. Si
no se ejecuta el seed con `--password`, **no hay nadie que pueda entrar en el navegador**.

## Pantallas

| Ruta | Qué hace |
|---|---|
| `/` | Panel: totales (exámenes, preguntas, opciones) y los cinco exámenes más recientes |
| `/acceso/` · `/salir/` | Entrar y salir (sesión, nunca token) |
| `/examenes/` | Tabla de exámenes con su número de preguntas |
| `/examenes/nuevo/` · `/examenes/{id}/editar/` · `/examenes/{id}/eliminar/` | Alta, edición y borrado con confirmación |
| `/examenes/{id}/` | Detalle de un examen con todas sus preguntas y opciones |
| `/preguntas/` | Tabla de preguntas, con filtro por examen y búsqueda por texto |
| `/examenes/{id}/preguntas/nuevo/` · `/preguntas/{id}/editar/` · `/preguntas/{id}/eliminar/` | Pregunta y sus opciones en un solo formulario |

## Verificación en vivo

Comprobado por el coordinador contra el servidor:

| Escenario | Resultado |
|---|---|
| Login | **200** |
| Panel, listados, formularios, búsqueda/filtros, borrado | **200** |
| Visitante anónimo | **302** al login |
| Usuario autenticado que **no** es `is_staff` | **403** |

La interfaz es **privada y solo para el profesorado**: `StaffRequiredMixin` exige sesión (302 si no la hay)
y consulta la tabla de roles (403 si el usuario no es la persona). El orden importa: un anónimo es nadie,
no «un lector al que se le niega algo».

## Filtros y URL compartible

En `/preguntas/` los filtros viajan en la URL:

- `?exam=<id>` — solo las preguntas de ese examen. Un valor que no es un id da **404**.
- `?q=<texto>` — búsqueda por el enunciado.

Que vivan en la URL es lo que hace que la vista sea **compartible, marcable y navegable**: «Anterior /
Siguiente» los conserva y el filtro sobrevive al retroceso del navegador.

## Errores de validación

Si una pregunta tiene menos de 2 opciones, o 0 o más de una correcta, el formulario **vuelve a la misma
pantalla con el error y sin perder lo escrito**: los textos de las opciones y la opción que se había
marcado como correcta se conservan. El mensaje de negocio se anuncia **una sola vez**, con un único
`role="alert"` (un lector de pantalla no debe oírlo dos veces).

## Frontera de confianza

**La sesión no abre la API y el token no abre la interfaz.**

| Situación | API | Interfaz |
|---|---|---|
| Anónimo | **401** | **302** al login |
| Token válido por la interfaz | No autentica | **302** al login |
| CSRF ausente en un POST de la interfaz | — | **403** |

Verificado por `quiz/tests/test_web.py::FrontierTests` y
`quiz/tests/test_http_matrix.py::SessionTokenFrontierTests`. Detalle en [[08-Seguridad]].

## Plantillas y activos

```
quiz/templates/
├── 403.html · 404.html · 500.html      (plantillas de error propias)
└── quiz/
    ├── base.html · dashboard.html · login.html
    ├── exam_list.html · exam_detail.html · exam_form.html · exam_confirm_delete.html
    ├── question_list.html · question_form.html · question_confirm_delete.html
    ├── widgets/correct_choice.html
    └── partials/ (_navbar · _messages · _pagination · _field · _error_summary
                   · _confirm_delete · _choice_row · _icon)
quiz/static/quiz/css/app.css             (una única hoja, tokens en :root)
```

Sin `|safe` ni `mark_safe` en todo el proyecto: todo el HTML se escapa.

> Nota: las plantillas `404.html` y `500.html` **no se usan con `DEBUG = True`** (Django sirve su propia
> página técnica). Son para el modo de producción, que este laboratorio no ejecuta.

## Estructura del código

| Fichero | Responsabilidad |
|---|---|
| `quiz/web_urls.py` | Rutas, en un módulo aparte: el router de la API no se toca |
| `quiz/web_views.py` | CBVs de Django. **No** importan DRF ni tocan `quiz/views.py` |
| `quiz/web_mixins.py` | `LoginRequiredMixin` + consulta a la tabla de roles; mensajes de éxito |
| `quiz/forms.py` | `ModelForm` de examen y pregunta + `formset` en línea de opciones |
| `quiz/queries.py` | Lecturas del dominio (sin N+1) |
| `quiz/services.py` | **Toda** la escritura de preguntas pasa por aquí |