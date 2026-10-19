# Matriz de trazabilidad — requisito → implementación prevista → prueba

> **Autor:** Analista de requisitos y producto · **Fecha:** 2026-10-16 · **Fase:** A/B (análisis y documentación)
> Documento gemelo de `docs/requisitos.md`. Los **ID de requisito** son los de ese documento.
>
> **Estado de verificación:** en esta fase **no se ha ejecutado ninguna prueba** (no se dispone de terminal).
> Por tanto la columna *Estado* refleja **la cobertura documental y de código**, no una ejecución:
>
> | Marca | Significado |
> |---|---|
> | `✅ cubierto` | Existe prueba **en el repositorio** que demuestra el requisito. Ejecución pendiente de fase C. |
> | `🟡 parcial` | El requisito está implementado pero **ninguna prueba** lo fija, o la prueba cubre menos de lo que el requisito exige. |
> | `🔴 pendiente` | El requisito **no está implementado** (`TODO`) o falta la prueba. |
> | `⚪ decisión` | El requisito no puede implementarse hasta que alguien decida (ver `docs/requisitos.md` §14). |
> | `➖ fuera` | Requisito declarado fuera de alcance. |

> ---
>
> ## ⚠️ Actualización de estado — 2026-10-16 (cierre de la implementación)
>
> **Lo que sigue debajo es la matriz tal como se escribió en la fase de análisis.** No se reescribe: las
> filas **que cambiaron de estado** están corregidas una a una y las demás se conservan para no perder la traza.
>
> **Evidencia de referencia (verificada por el coordinador sobre el repositorio actual):**
>
> - `python manage.py test` → **`Ran 365 tests ... OK`** (era 61 pruebas con 21 fallos al empezar; 324 antes de los arreglos de seguridad de `a82978e`).
> - Línea base: **61 pruebas, 21 fallando** — 18 errores en `test_quizctl` y 3 fallos en
>   `test_permissions`, por las Partes 2 y 3 sin implementar.
> - `python manage.py check` → sin problemas.
> - Versiones: Django 5.2.18, djangorestframework 3.18.3, drf-spectacular 0.30.0, requests 2.34.2,
>   Python 3.14.4. `requirements.txt` **intacto**: 4 líneas.
>
> **Cambios de estado:**
>
> | Bloque | Cambio |
> |---|---|
> | Parte 2 (`quizctl.py`) | R-API-21…29 🔴 → ✅ (implementado y con la suite en verde) |
> | Parte 3 (`quiz/permissions.py`) | R-API-47…51 🔴 → ✅; R-API-53 🟡 → ✅; R-API-54 ⚪ → ✅ (decidido en ADR-0003) |
> | Validación del filtro | R-VIE-08 ⚪ → ✅ (`?exam=` no numérico ahora da **400**, no se ignora) |
> | Repositorio | R-REP-01 🟡 → ✅ (README reescrito), R-REP-07 🔴 → ✅ (365 OK), R-REP-13 🟡 → ✅ (existen `docs/` y 3 ADR) |
> | Interfaz web | R-UI-01…R-UI-12, R-UI-14 y R-UI-T1…T7 🔴 → ✅ o 🟡, con la interfaz implementada y verificada en vivo |
> | **Endurecimiento de configuración (`a82978e`)** | R-REP-03 🔴 → 🟡 **parcial**: ya **no** hay `SECRET_KEY` ni `DEBUG=True` fijos en el código (entorno → `.secret_key` generado; con `DEBUG` apagado el arranque falla cerrado), pero el laboratorio **sigue arrancando en desarrollo por defecto** y sin HTTPS. R-REP-05 🟡 → ✅ (`seed_quiz` solo imprime tokens con `--show-tokens`). R-API-20 🟡 → 🟡 **parcial**: el 500 con detalle técnico desaparece cuando `DJANGO_DEBUG=0` |
> | **Cabeceras de seguridad** | `X_FRAME_OPTIONS = "DENY"` + CSP `default-src 'self'; frame-ancestors 'none'` solo en HTML (SUI-05 cerrado), con el `<script>` inline movido a `quiz/static/quiz/js/app.js` |
> | **Cobertura nueva** | `quiz/tests/test_config_hardening.py` (15 pruebas): clave no publicada y generada, arranque que falla cerrado, cabeceras y salida de `seed_quiz` |
> | **Pendientes que siguen abiertos** | R-SER-08 (`question_count` en escrituras), R-SER-32/33/34, R-VIE-17/19/20/21, R-REP-05 (rotación de tokens), R-REP-12, R-REP-14, R-UI-11 (contraste, revisado a ojo sin herramienta), R-UI-07 (matriz por rol completa en la UI), **SUI-03** (login sin límite de intentos, riesgo aceptado) |
>
> **Marcas añadidas:** 🟢 = implementado **y verificado con ejecución** (suite en verde o comprobación en
> vivo). No se marca nada 🟢 sin esa evidencia.

**Documentos relacionados del equipo** (escritos por otros agentes en el mismo repositorio):

| Documento | Qué aporta a esta matriz |
|---|---|
| `docs/arquitectura.md` | Decisión de arquitectura de la UI, cambios en `settings.py`, tabla de permisos (Parte 3) y tabla de la API |
| `docs/adr/0001-arquitectura-de-la-interfaz-web.md` | ADR aprobado de la UI: server-rendered, sin CDN, sin `admin` |
| `docs/adr/0002-consumicion-del-dominio-desde-la-interfaz.md` | La interfaz consume el dominio en proceso, a través de `quiz/services.py` |
| `docs/adr/0003-regla-de-permisos.md` | Una tabla de roles, dos adaptadores; **resuelve Q-06** (el agente modifica exámenes, nunca borra) |
| `docs/frontera-ia.md` | Auditoría de la frontera del agente (R0/R1/R2) y del texto hostil |
| `docs/revision-codigo.md` | Revisión de los commits de implementación: B1, I1–I9 y menores, con su evidencia |
| `docs/decisiones-docker-ci.md` | Por qué no hay contenedores ni CI (cierra R-REP-14 como *fuera de alcance por decisión*) |
| `docs/seguridad-interfaz.md` | Auditoría de la interfaz (22 hallazgos SUI) y el estado tras `a82978e`: SUI-01/02/04/05 cerrados, SUI-03 abierto |
| `docs/seguridad.md` | Auditoría de seguridad inicial (SEC-01…SEC-22), de la que algunos hallazgos se cerraron en `a82978e` |

> Cuando una decisión de arquitectura responda a una **pregunta abierta** de `docs/requisitos.md` §14,
> esta matriz debe actualizarse en lugar de abrir una segunda vía. Hoy: **Q-02 y Q-03 están respondidas**
> (ADR-0001 y ADR-0002), **Q-06 está resuelta** (ADR-0003) y **Q-11 está cerrada**: `/api/schema/` y
> `/api/docs/` responden **200 sin token**, comprobado en vivo y cubierto por `test_api.py`. **Q-04
> (`question_count` en las escrituras) sigue abierta.**

---

## 1. Resumen de cobertura

> **Instantánea de la fase de análisis.** Los números de la tabla de abajo **ya no describen el
> repositorio**: el resumen real de esta entrega es la suite en verde (**365 pruebas**) más las filas
> corregidas de §2 a §6. La tabla se conserva como registro del punto de partida.

| Bloque | Requisitos | ✅ cubierto | 🟡 parcial | 🔴 pendiente | ⚪ decisión |
|---|---|---|---|---|---|
| C1 · Serializadores y validaciones | 34 | 9 | 18 | 2 | 1 (+4 PENDIENTE) |
| C2 · Vistas y enrutadores | 21 | 11 | 5 | 0 | 2 (+3 PENDIENTE) |
| C3 · Operaciones HTTP y códigos de estado | 54 | 28 | 12 | 14 | 1 |
| C4-A · Repositorio | 14 | 5 | 7 | 2 | — |
| C4-B · Tabla de API / UI | 14 (+7 técnicas) | 1 | 0 | 20 | — |
| **Total** | **≈ 142 (+4 técnicos)** | **53** | **42** | **38** | **4** |

**Lectura del resumen:** el bloque que bloquea la entrega es **C3**, y casi todo el hueco está en los
`TODO(team)` de la **Parte 2** (`quizctl.py`) y la **Parte 3** (`quiz/permissions.py`).

---

## 2. Criterio 1 — Serializadores y validaciones

### 2.1 `ExamSerializer`

| Req | Implementación prevista / actual | Prueba que lo demuestra | Estado |
|---|---|---|---|
| R-SER-01 | `quiz/serializers.py:13-19` (`ExamSerializer`) | `quiz/tests/test_api.py:23` `test_exams_are_listed_with_their_question_count` | ✅ cubierto |
| R-SER-02 | `ModelSerializer` + `title` requerido por el modelo | `test_api.py:23` comprueba la clave; **falta** prueba de POST sin `title` → `test_permissions.py:25` solo prueba el camino válido | 🟡 parcial |
| R-SER-03 | `models.py:5` `max_length=120` | *ninguna* → crear en `test_api.py` | 🟡 parcial |
| R-SER-04 | `blank` por defecto en `CharField` | *ninguna* → crear en `test_api.py` | 🟡 parcial |
| R-SER-05 | `serializers.py:19` `read_only_fields = ["created_at"]` | *ninguna* → crear en `test_api.py` | 🟡 parcial |
| R-SER-06 | `serializers.py:14` `IntegerField(read_only=True)` | *ninguna* → crear en `test_api.py` | 🟡 parcial |
| R-SER-07 | `quiz/views.py:11` `annotate(question_count=Count("questions"))` | `test_api.py:23-26` | ✅ cubierto |
| R-SER-08 | `serializers.py:14` + ausencia de atributo en la instancia creada | *ninguna*; requiere **decisión** (Q-04) antes de escribir la prueba | ⚪ decisión |

### 2.2 `ChoiceSerializer`

| Req | Implementación prevista / actual | Prueba que lo demuestra | Estado |
|---|---|---|---|
| R-SER-09 | `serializers.py:7-10` | `test_api.py:41-44` `test_choices_travel_nested_inside_the_question` | ✅ cubierto |
| R-SER-10 | `models.py:26` `text` requerido | *ninguna* → crear en `test_api.py` | 🟡 parcial |
| R-SER-11 | `models.py:26` `max_length=200` | *ninguna* → crear en `test_api.py` | 🟡 parcial |
| R-SER-12 | `models.py:27` `default=False` + `serializers.py:34` | *ninguna* para el caso «0 correctas»; el caso «2 correctas» sí: `test_api.py:52` | 🟡 parcial |
| R-SER-13 | `BooleanField` de DRF | *ninguna* → crear en `test_api.py` | 🟡 parcial |

### 2.3 `QuestionSerializer`

| Req | Implementación prevista / actual | Prueba que lo demuestra | Estado |
|---|---|---|---|
| R-SER-14 | `serializers.py:22-29` | `test_api.py:41` (parcial: fija `choices`); falta fijar las 5 claves | 🟡 parcial |
| R-SER-15 | `serializers.py:28` campo `exam` (PK related) | `test_api.py:60` (campo ausente); *falta* `exam` inexistente | 🟡 parcial |
| R-SER-16 | DRF `PrimaryKeyRelatedField` | `test_api.py:65` `test_a_wrong_type_is_400` | ✅ cubierto |
| R-SER-17 | `serializers.py:28` campo `text` | `test_api.py:60` `test_a_missing_required_field_is_400` | ✅ cubierto |
| R-SER-18 | `serializers.py:24` `choices = ChoiceSerializer(many=True)` (obligatorio) | *ninguna* → crear en `test_api.py` | 🟡 parcial |
| R-SER-19 (RN-01) | `serializers.py:32-33` | `test_api.py:52` cubre el caso de 2 correctas; **falta** el caso de 1 sola opción → crear en `test_api.py` | 🟡 parcial |
| R-SER-20 | misma rama (`len([]) == 0`) | *ninguna* → crear en `test_api.py` | 🟡 parcial |
| R-SER-21 (RN-02) | `serializers.py:34-35` | `test_api.py:52-58` `test_two_correct_choices_is_400_and_saves_nothing` | ✅ cubierto |
| R-SER-22 | misma rama (`!= 1`) | *ninguna* → crear en `test_api.py` | 🟡 parcial |
| R-SER-23 | `validate_choices` sobre campo anidado (`serializers.py:31`) | `test_api.py:57` comprueba el texto; **no** comprueba la clave `choices` | 🟡 parcial |
| R-SER-24 | `serializers.py:33,35` + `settings.py:37` `LANGUAGE_CODE="es"` | `test_api.py:57` (`"exactamente una"`); `test_quizctl.py:91` (`"exactamente una"` en consola) | ✅ cubierto |
| R-SER-25 | `serializers.py:40` `transaction.atomic()` | `test_api.py:58` `assertEqual(Question.objects.count(), 8)` | ✅ cubierto |
| R-SER-26 | `serializers.py:42` `bulk_create` + `test_api.py:48-49` | `test_api.py:46` `test_a_valid_question_is_created_with_201` | ✅ cubierto |
| R-SER-27 | `serializers.py:47` `transaction.atomic()` en `update` | *ninguna* → crear en `test_api.py` | 🟡 parcial |
| R-SER-28 | `serializers.py:46,49` (`choices = … or None`) | `test_api.py:70-74` `test_patch_changes_only_what_is_sent` | ✅ cubierto |
| R-SER-29 (RN-05) | `serializers.py:50-51` (`delete()` + `bulk_create`) | *ninguna* → crear en `test_api.py` | 🟡 parcial |
| R-SER-30 | Semántica `PUT` de DRF + `serializers.py:24` campo requerido | *ninguna* → crear en `test_api.py` | 🟡 parcial |
| R-SER-31 | `quiz/urls.py:6-7` (solo 2 registros) | *ninguna* → crear en `test_api.py` (`GET /api/choices/` → 404) | 🟡 parcial |
| R-SER-32 | **No existe** `validate` que compare textos de opción | *ninguna* → crear tras la decisión Q-07 | 🔴 pendiente |
| R-SER-33 | **No existe** `UniqueConstraint` en `models.py:4-7` | *ninguna* → crear tras la decisión Q-07 | 🔴 pendiente |
| R-SER-34 | **No existe** normalización | *ninguna* | 🔴 pendiente (opcional) |

---

## 3. Criterio 2 — Vistas y enrutadores

| Req | Implementación prevista / actual | Prueba que lo demuestra | Estado |
|---|---|---|---|
| R-VIE-01 | `quiz/urls.py:5-8` (`DefaultRouter`) + `config/urls.py:5` | `test_api.py:17,24,47,72,78` (las 5 rutas) | ✅ cubierto |
| R-VIE-02 | `quiz/urls.py:6-7` `basename="exam"/"question"` | `test_api.py:83-93` (lee `operationId` del contrato) + `test_quizctl.py:120-122` | ✅ cubierto |
| R-VIE-03 | `views.py:11` `annotate(question_count=Count("questions"))` | `test_api.py:23-26` | ✅ cubierto |
| R-VIE-04 | `models.py:17-18` `ordering = ["id"]`; `views.py:11` `order_by("id")` | *ninguna* sobre el orden → crear en `test_api.py` | 🟡 parcial |
| R-VIE-05 | `views.py:28-30` filtro manual por `exam` | `test_api.py:33-35` `test_questions_can_be_filtered_by_exam` | ✅ cubierto |
| R-VIE-06 | `views.py:23-24` `SearchFilter` + `search_fields=["text"]` | `test_api.py:37-39` `test_questions_can_be_searched_by_text` | ✅ cubierto |
| R-VIE-07 | misma `get_queryset` | *ninguna* → crear en `test_api.py` | 🟡 parcial |
| R-VIE-08 | `views.py:12-27` `exam_filter_id()`: un `exam` que no es un id **se rechaza con 400** nombrando el parámetro (decisión H4 del arquitecto) | `test_services.py::ExamFilterTests` + verificado en vivo: `?exam=` no entero → **400** | 🟢 cubierto |
| R-VIE-09 | `settings.py:52-53` `PageNumberPagination` / `PAGE_SIZE=5` | `test_api.py:28-31` `test_questions_are_paginated_five_at_a_time` | ✅ cubierto |
| R-VIE-10 | `settings.py:52` | *ninguna* → crear en `test_api.py` (`?page=2`, `?page=999`) | 🟡 parcial |
| R-VIE-11 | `views.py:27` `select_related("exam").prefetch_related("choices")` | *ninguna* con `assertNumQueries` → crear en `test_api.py` | 🟡 parcial |
| R-VIE-12 | `config/urls.py:7-8`; `settings.py:61` `SERVE_INCLUDE_SCHEMA=False` | `test_api.py:86` `GET /api/schema/?format=json` | ✅ cubierto |
| R-VIE-13 | `views.py:14-20` `@extend_schema_view` con `OpenApiParameter("exam", int, …)` | *ninguna* que lo verifique directamente → crear en `test_api.py` (leer el esquema) | 🟡 parcial |
| R-VIE-14 | `settings.py:46` `TokenAuthentication` + `DEFAULT_SCHEMA_CLASS` | `test_api.py:95-97` `test_the_contract_declares_token_authentication` | ✅ cubierto |
| R-VIE-15 | `agent/gateway.py:143-145` (comprueba el catálogo) | `test_api.py:83-93` `test_every_operation_the_gateway_offers_exists_in_the_contract` + `test_agent.py:121-125` | ✅ cubierto |
| R-VIE-16 | `views.py:11,27` — sin filtro por usuario | *ninguna* → crear en `test_api.py` con el usuario `lector` (`helpers.py:17-20`) | 🟡 parcial |
| R-VIE-17 | **No existe** `OrderingFilter` | — | 🔴 pendiente (recomendado) |
| R-VIE-18 | `config/urls.py:7` (`SpectacularAPIView`) — **el arquitecto lo marca sin verificar** (`docs/arquitectura.md:301-312`) | *ninguna*; el comando de comprobación está en ese documento → Q-11 | ⚪ decisión |
| R-VIE-19 | **No existe** throttling | — | 🔴 pendiente (opcional) |
| R-VIE-20 | `settings.py:54` `AutoSchema` sin `extend_schema` de respuestas | — | 🔴 pendiente (opcional) |
| R-VIE-21 | `settings.py:57-62` sin `SWAGGER_UI_DIST` (CDN por defecto) | — | 🔴 pendiente (informativo) |

---

## 4. Criterio 3 — Operaciones HTTP y códigos de estado

### 4.1 Matriz endpoint → implementación → prueba

| Req | Endpoint / método | Implementación | Prueba | Estado |
|---|---|---|---|---|
| R-API-01 | `GET /api/exams/` | `ExamViewSet` (`views.py:9-11`) + `ExamSerializer` | `test_api.py:23` | ✅ cubierto |
| R-API-02 | `POST /api/exams/` | `ModelViewSet` (`views.py:10`) | `test_permissions.py:40` solo prueba el DELETE del agente; **no** hay prueba de POST válido de examen | 🟡 parcial |
| R-API-03 | `GET /api/exams/{id}/` | `ModelViewSet.retrieve` | *ninguna* → crear (`test_quizctl.py:70` cubre list) | 🟡 parcial |
| R-API-04 | `GET /api/exams/{id}/` inexistente | DRF `get_object` | `test_quizctl.py:101` `test_a_missing_question_exits_four` (pregunta, no examen) | 🟡 parcial |
| R-API-05 | `PUT`/`PATCH /api/exams/{id}/` | `ModelViewSet` | *ninguna* → crear | 🟡 parcial |
| R-API-06 | `DELETE /api/exams/{id}/` (persona) | `ModelViewSet.destroy` + cascada `models.py:13` | *ninguna* de éxito; `test_permissions.py:41` prueba el 403 del agente | 🟡 parcial |
| R-API-07 | `DELETE` por agente/lector | `quiz/permissions.py:22-23` → `services.may(role_of(user), method_of(request, view))`; la tabla `METHODS_BY_ROLE` no incluye `DELETE` para el agente | `test_permissions.py` + `test_http_matrix.py::VerbAndRoleMatrixTests`; verificado en vivo: agente DELETE → **403** | 🟢 cubierto |
| R-API-08 | `GET /api/questions/` | `QuestionViewSet` (`views.py:21-31`) | `test_api.py:28,41` | ✅ cubierto |
| R-API-09 | `GET /api/questions/?exam=&search=&page=` | `views.py:26-31` + `settings.py:52` | `test_api.py:33,37,28` + `test_quizctl.py:75-79` (`--exam` + `--json` + `count==4`) | ✅ cubierto |
| R-API-10 | `POST /api/questions/` | `QuestionSerializer.create` (`serializers.py:38-43`) | `test_api.py:46` + `test_permissions.py:25` (agente) + `test_agent.py:50` + `test_quizctl.py:81` | ✅ cubierto |
| R-API-11 | `GET /api/questions/{id}/` | `ModelViewSet.retrieve` | `test_api.py:79` (404 tras borrar) + `test_agent.py:32` (`questions_list`) | 🟡 parcial |
| R-API-12 | `PATCH /api/questions/{id}/` | `QuestionSerializer.update` (`serializers.py:45-52`) | `test_api.py:70` + `test_permissions.py:29` | ✅ cubierto |
| R-API-13 | `PUT /api/questions/{id}/` | `update` + campos requeridos | *ninguna* → crear (incompleto → 400; completo → 200) | 🟡 parcial |
| R-API-14 | `DELETE /api/questions/{id}/` (persona) | `ModelViewSet.destroy` | `test_api.py:76-79` + `test_permissions.py:43` + `test_agent.py:64-70` | ✅ cubierto |
| R-API-15 | `GET /api/schema/`, `/api/docs/` | `config/urls.py:7-8` | `test_api.py:86,96` + `test_quizctl.py:120-122` + `agent/gateway.py:52` | ✅ cubierto |
| R-API-16 | Sin token / token inválido → **401** | `settings.py:46-51` (`TokenAuthentication` + `IsAuthenticated`) | `test_api.py:15,19` + `test_permissions.py:53` + `test_quizctl.py:110` | ✅ cubierto |
| R-API-17 | Autenticado sin permiso → **403** | `quiz/permissions.py` (delegando en la tabla de `quiz/services.py:20-25`) | `test_permissions.py` + `test_http_matrix.py`; verificado en vivo: lector POST/DELETE → **403** | 🟢 cubierto |
| R-API-18 | Método no permitido → **405** | `ModelViewSet` de DRF | *ninguna* → crear (`POST /api/exams/{id}/`) | 🟡 parcial |
| R-API-19 | `Content-Type` no soportado → **415** | Parsers por defecto de DRF | *ninguna* → crear (`text/plain`) | 🟡 parcial |
| R-API-20 | Fallo interno → **5xx** sin filtrar datos | `DJANGO_DEBUG=0` deja de usar la página técnica de Django (con el valor por defecto `1` sigue mostrándola: es el modo laboratorio) | `test_config_hardening.py::StartupGuardTests` (el arranque depende de `DJANGO_DEBUG`) | 🟡 parcial |

### 4.2 Códigos de salida de `quizctl` (Parte 2 — implementada en `cf61a11`)

| Req | Implementación | Prueba que lo demuestra | Estado |
|---|---|---|---|
| R-API-21 | `quizctl.py:48-63` `exit_code_for` — `200 <= s < 300 → 0` | `test_quizctl.py:17-19` `test_success_is_zero` | 🟢 cubierto |
| R-API-22 | `400 → EXIT_VALIDATION (2)` | `test_quizctl.py:21-22` | 🟢 cubierto |
| R-API-23 | `401, 403 → EXIT_FORBIDDEN (3)` | `test_quizctl.py:24-26` | 🟢 cubierto |
| R-API-24 | `404 → EXIT_NOT_FOUND (4)` | `test_quizctl.py:28-29` | 🟢 cubierto |
| R-API-25 | `5xx → EXIT_SERVER (5)` | `test_quizctl.py:31-33` | 🟢 cubierto |
| R-API-26 | resto → `EXIT_OTHER (1)` | `test_quizctl.py:35-37` | 🟢 cubierto |
| R-API-27 | `quizctl.py:66-91` `build_question_payload` + `_choice` con `rsplit` del `:ok` final | `test_quizctl.py:41-46` `test_ok_marks_the_correct_choice` | 🟢 cubierto |
| R-API-28 | misma función (solo el `:ok` final) | `test_quizctl.py:48-51` `test_only_the_final_ok_counts` | 🟢 cubierto |
| R-API-29 | misma función (sin validación local) | `test_quizctl.py:53-55` + `test_quizctl.py:87-91` | 🟢 cubierto |
| R-API-30 | `quizctl.py:73-74` sin `QUIZ_TOKEN` → `Result(status=-1)` → `main` devuelve `EXIT_OTHER` | `test_quizctl.py:114-115` | 🟢 cubierto |
| R-API-31 | `quizctl.py:83-84` `except requests.RequestException` → `status=0` → `EXIT_NETWORK` | `test_quizctl.py:117-118` | 🟢 cubierto |
| R-API-32 | `quizctl.py:76-77` `if dry_run and method != "GET"` | `test_quizctl.py:93-99` `test_dry_run_describes_and_creates_nothing` | 🟢 cubierto |
| R-API-33 | `quizctl.py:146-150` `render` con `--json` | `test_quizctl.py:75-79`, `81-85`, `87-91` | 🟢 cubierto |
| R-API-34 | `quizctl.py:134-143` `ops` lee `/api/schema/?format=json` | `test_quizctl.py:120-122` `test_ops_lists_the_contract` | 🟢 cubierto |
| R-API-35 | 403 del servidor → salida 3 | `test_quizctl.py:104-108` (`CliLiveTests`), depende de la Parte 3, **ya implementada** | 🟢 cubierto |
| R-API-36 | 404 → salida 4 | `test_quizctl.py:101-102` | 🟢 cubierto |

### 4.3 Frontera del agente (Parte 4 — implementada; no tocar sin `arquitecto-ia`)

| Req | Implementación | Prueba | Estado |
|---|---|---|---|
| R-API-37 | `gateway.py:162-164` (`R0/R1` → `_send`) | `test_agent.py:32-35` | ✅ cubierto |
| R-API-38 | `gateway.py:32-40` riesgo `R1` + token del agente | `test_agent.py:50-54` | ✅ cubierto |
| R-API-39 | `gateway.py:166-177` (plan + `plan_hash`, no ejecuta) | `test_agent.py:43-48` | ✅ cubierto |
| R-API-40 | `gateway.py:178-180` exige `human_token` | `test_agent.py:72-78` | ✅ cubierto |
| R-API-41 | `gateway.py:110-112` `plan_hash` sobre el estado actual | `test_agent.py:80-87` | ✅ cubierta |
| R-API-42 | `gateway.py:140-142` `ALLOWED.get(op)` + `gateway.py:145` | `test_agent.py:102-104` + `test_agent.py:99-100` | ✅ cubierto |
| R-API-43 | `gateway.py:62-97` (`_is_int`, `_fill_path`, `_valid_query`, `_valid_body`) | `test_agent.py:106-119` | ✅ cubierto |
| R-API-44 | `gateway.py:143-145` `load_catalog` + comprobación | `test_agent.py:121-125` | ✅ cubierto |
| R-API-45 | `gateway.py:164` envuelve en `untrusted_data`; `seed_data.py:7-10` | `test_agent.py:37-41` | ✅ cubierto |
| R-API-46 | `gateway.py:115-121` `_audit` + `gateway.py:127-129` | `test_agent.py:130-136` | ✅ cubierto |

### 4.4 Reglas de roles (Parte 3 — implementada en `cf61a11`, tabla en `quiz/services.py`)

| Req | Implementación | Prueba que lo demuestra | Estado |
|---|---|---|---|
| R-API-47 | `services.role_of()` → `person` si `is_staff`/`is_superuser`; `METHODS_BY_ROLE[PERSON]` = verbos conocidos | `test_permissions.py`; verificado en vivo: persona DELETE → **204** | 🟢 cubierto |
| R-API-48 | `METHODS_BY_ROLE[AGENT]` = lectura + `POST`/`PUT`/`PATCH` | `test_permissions.py` | 🟢 cubierto |
| R-API-49 | `DELETE` ausente de `METHODS_BY_ROLE[AGENT]` | `test_permissions.py`; verificado en vivo: agente DELETE → **403**, el recurso sobrevive | 🟢 cubierto |
| R-API-50 | misma tabla, aplicada a `ExamViewSet` | `test_permissions.py`; verificado en vivo: agente borra examen → **403** | 🟢 cubierto |
| R-API-51 | `METHODS_BY_ROLE[READER]` = solo lectura | `test_permissions.py`; verificado en vivo: lector POST/DELETE → **403** | 🟢 cubierto |
| R-API-52 | `settings.py` `IsAuthenticated` antes de `AgentPermission` | `test_permissions.py`; verificado en vivo: sin token → **401** | 🟢 cubierto |
| R-API-53 | `services.may()` deniega todo verbo fuera de la tabla | `test_services.py::DenyByDefaultTests` (era I6 de la revisión) | 🟢 cubierto |
| R-API-54 | **Decidido en ADR-0003:** el agente lee, crea y modifica (**también exámenes**), nunca borra | `test_permissions.py` + `test_http_matrix.py::VerbAndRoleMatrixTests` | 🟢 cubierto |

---

## 5. Criterio 4-A — Repositorio

| Req | Implementación / evidencia | Cómo se demuestra | Estado |
|---|---|---|---|
| R-REP-01 | `README.md` **reescrito**: puesta en marcha con `seed_quiz --password`, variables de entorno por nombre, las 4 partes, la interfaz, la **tabla de la API** y la tabla de códigos de error | Revisión documental; sigue los comandos en una máquina limpia | 🟢 cubierto (huedo I9 de la revisión corregido) |
| R-REP-02 | `requirements.txt:1-4` (4 líneas, **intacto**) | Lectura del archivo + `pip install -r` | 🟢 cubierto |
| R-REP-03 | **Endurecido en `a82978e`**: no hay `SECRET_KEY` ni `DEBUG` fijos en el código. Orden: `DJANGO_SECRET_KEY` → si no, `.secret_key` generado (ignorado por git) → con `DJANGO_DEBUG=0`, arranque con `ImproperlyConfigured`; `ALLOWED_HOSTS` viene de `DJANGO_ALLOWED_HOSTS` y también falla cerrado | `test_config_hardening.py::SecretKeyTests` + `::StartupGuardTests` | 🟡 **parcial**: el riesgo de la clave publicada está cerrado; sigue vigente que el laboratorio **arranca en desarrollo por defecto** y que con `DEBUG=0` falta servidor estático (ver `docs/decisiones-docker-ci.md` y el aviso del `README.md`) |
| R-REP-04 | `.gitignore` incluye ahora también `.secret_key` | Lectura del archivo + `test_config_hardening.py::SecretKeyTests::test_secret_key_file_is_not_tracked_by_git` | 🟢 cubierto |
| R-REP-05 | `seed_quiz.py` **ya no imprime** los tokens por defecto: solo con `--show-tokens`, y **nunca** la contraseña | `test_config_hardening.py::SeedOutputTests` (3 pruebas: sin flag, con flag, contraseña nunca impresa); revisión de `README.md`, `docs/` y notas: solo aparecen **nombres** de variables | 🟢 cubierto (la impresión es ahora opt-in) |
| R-REP-06 | `config/`, `quiz/`, `agent/`, `quizctl.py`, `quiz/tests/` | Estructura del árbol | 🟢 cubierto |
| R-REP-07 | `python manage.py test` | Ejecución real: **`Ran 365 tests ... OK`** (línea base: 61 pruebas, 21 fallando; 324 antes de `a82978e`) | 🟢 cubierto |
| R-REP-08 | `README.md` (comando `spectacular`); `.gitignore:7` excluye `schema.yml`. **Contrato legible sin token: confirmado** | `test_api.py` (esquema) + verificado en vivo: `/api/schema/` y `/api/docs/` → **200 sin token**. **Q-11 queda cerrada** | 🟢 cubierto |
| R-REP-09 | `AGENTS.md` §7; `README.md` (sección final) | Revisión de estilo | 🟢 cubierto |
| R-REP-10 | `AGENTS.md`, `opencode.json:1-4` | Lectura | 🟢 cubierto |
| R-REP-11 | `seed_quiz.py:11-34` (`get_or_create`), `:52-59` (borra y recarga) | `helpers.py:8-13` (`call_command("seed_quiz")` en varias clases de prueba) | 🟢 cubierto |
| R-REP-12 | `quiz/migrations/0001_initial.py`; datos en `seed_quiz.py` | `python manage.py migrate` en BD vacía | 🟡 parcial (la base de datos de desarrollo existe y las pruebas pasan, pero no hay prueba que fije el esquema) |
| R-REP-13 | `docs/` con 10 documentos + **`docs/adr/0001`, `0002`, `0003`** + `docs/seguridad-interfaz.md` | Existencia de los ADR y de los informes | 🟢 cubierto |
| R-REP-14 | Sin CI ni script de verificación | Decisión documentada en `docs/decisiones-docker-ci.md` | ➖ **fuera de alcance por decisión** (no es un fallo) |

---

## 6. Criterio 4-B — Tabla de API / interfaz gráfica

**Actualizado.** En la fase de análisis esta capa **no existía**; hoy **está implementada**
(`quiz/web_views.py`, `quiz/web_urls.py`, `quiz/web_mixins.py`, `quiz/forms.py`, `quiz/templates/quiz/`,
`quiz/static/`) y verificada en vivo por el coordinador: login 200; panel, listados, formularios,
búsqueda/filtros y borrado 200; anónimo **302** al login; usuario no `is_staff` **403**.

**Decisiones vigentes:** ADR-0001 (server-rendered, sin CDN, sin JS obligatorio, sin `admin`), ADR-0002 (la
UI usa el ORM a través de `quiz/services.py`, no habla HTTP con su propia API), ADR-0003 (una sola tabla
de roles).

**Nota sobre el nombre de los módulos de prueba:** en la fase de análisis se previó
`quiz/tests/test_ui.py`. Los ficheros reales son `test_web.py`, `test_web_review.py`, `test_web_gaps.py`
y `test_services.py`.

| Req | Implementación | Prueba | Estado |
|---|---|---|---|
| R-UI-01 | `ExamListView` + `quiz/templates/quiz/exam_list.html` | `test_web.py::DashboardAndListTests`, `test_web_review.py::OnePageSizeTests` | 🟢 cubierto |
| R-UI-02 | `web_views.py:109-151` `QuestionListView` + `quiz/question_list.html` | `test_web_review.py::QuestionListingTests` | 🟢 **completado** (verificado en vivo: `/preguntas/` → 200) |
| R-UI-03 | `paginate_by = settings.PAGE_SIZE` (`web_views.py:27`) + `partials/_pagination.html` | `test_web_gaps.py::PaginationGapTests`, `test_web_review.py::OnePageSizeTests` | 🟢 cubierto (la desviación I8, «10 en la UI», ya no existe: **una sola constante `PAGE_SIZE = 5`**) |
| R-UI-04 | `web_views.py:120-130` `get_exam()` y `:132-134` `get_text()`, con filtros en la URL | `test_web_review.py::QuestionListingTests`, `test_web_gaps.py::PaginationGapTests` | 🟢 **completado** (verificado en vivo; un `exam` no numérico da 404) |
| R-UI-05 | `QuestionForm` + `inlineformset` de `Choice`; el POST inválido conserva texto y opción marcada | `test_web.py::QuestionCrudTests`, `test_web_review.py::ChoiceKeptTests` | 🟢 cubierto (huedos I2 de la revisión corregidos) |
| R-UI-06 | `ExamDeleteView` / `QuestionDeleteView` + `partials/_confirm_delete.html` | `test_web.py::ExamCrudTests`, `QuestionCrudTests` | 🟢 cubierto |
| R-UI-07 | `StaffRequiredMixin` consulta `services.may_use()`; la plantilla refleja la regla | `test_web.py::AccessTests` (403 por rol) | 🟡 parcial: hay un 403 global correctamente **probado**, pero no la matriz completa por rol que pedía ADR-0003 §verificación (el agente edita y no ve «Eliminar») |
| R-UI-08 | `templates/403.html`; el POST inválido vuelve al formulario con errores | `test_web.py::SecurityAndAssetTests`, `test_web_review.py::SingleAnnouncementTests` | 🟢 cubierto (I1 corregido: un solo `role="alert"`) |
| R-UI-09 | Estado vacío en los listados | `test_web_gaps.py::BrowserShapeTests` | 🟢 cubierto |
| R-UI-10 | `quiz/templates/quiz/base.html` + `partials/` + `quiz/static/quiz/css/app.css`, sin CDN. El `<script>` inline se movió a `quiz/static/quiz/js/app.js` para poder aplicar la CSP sin `unsafe-inline` | `test_web.py::SecurityAndAssetTests` (el activo se sirve desde la app) + `test_config_hardening.py::ResponseHeaderTests::test_no_inline_script_is_needed_by_the_policy` | 🟢 cubierto |
| R-UI-11 | CSS con tokens, `:focus-visible`, `prefers-reduced-motion`, responsive | `test_web_review.py::SingleAnnouncementTests` y revisión de la hoja | 🟡 parcial: el contraste ≥ 4.5:1 está **revisado a ojo**, sin herramienta ni prueba que lo verifique (así lo admite el propio requisito) |
| R-UI-12 | Sin JS obligatorio; los radios funcionan por `name` común | `test_web.py::QuestionCrudTests` | 🟢 cubierto |
| R-UI-13 | Pruebas de UI repartidas en `test_web.py`, `test_web_review.py`, `test_web_gaps.py` | Los propios módulos | 🟢 cubierto |
| R-UI-14 | **Sin** `django.contrib.admin` | `test_web.py::SecurityAndAssetTests` (`/admin/` → 404) | 🟢 cubierto |
| R-UI-T1 | `settings.TEMPLATES` con `APP_DIRS` y los context processors de auth y messages | Pruebas de renderizado | 🟢 cubierto |
| R-UI-T2 | `django.contrib.staticfiles` instalado; los estáticos salen de la app | `test_web.py::SecurityAndAssetTests` | 🟢 cubierto |
| R-UI-T3 | **Frontera de confianza** intacta | `test_web.py::FrontierTests`, `test_http_matrix.py::SessionTokenFrontierTests` | 🟢 cubierto: la sesión no abre la API (401), el token no abre la UI (302), la UI exige CSRF (403) |
| R-UI-T4 | La UI usa el **ORM**, no la API por HTTP (ADR-0002) | `test_query_counts.py::QueryLayerTests` | 🟢 decidido y verificado |
| R-UI-T5 | **Validador único** compartido por serializador y formset | `test_services.py::SameVerdictTests` (era I5: el fichero **no existía**) | 🟢 cubierto |
| R-UI-T6 | La UI no expone acciones R2 ni borrados masivos | `test_web.py::AccessTests` | 🟢 cubierto |
| R-UI-T7 | **Regresión:** los cuatro entregables siguen verdes tras tocar `settings.py` | Suite completa: `Ran 365 tests ... OK` | 🟢 cubierto |

---

## 7. Huecos de prueba detectados (agenda del `tester`)

> **Actualización:** esta agenda nació de la fase de análisis. La mayoría de sus huecos está cerrada —
> los cubrieron `test_services.py`, `test_http_matrix.py`, `test_http_client.py`, `test_persistence.py`,
> `test_query_counts.py`, `test_web_gaps.py` y `test_web_review.py` (`7992f2a`). **Se conserva como
> registro**, marcando qué punto sigue abierto. Lo que queda abierto está en
> [[12-Limitaciones-y-pendientes]] (`Semana_8/12-Limitaciones-y-pendientes.md`).

| # | Prueba a añadir | Módulo | Requisitos que cierra | Estado |
|---|---|---|---|---|
| 1 | `PUT` incompleto → 400 y completo → 200 | `test_http_matrix.py` | R-SER-30, R-API-13 | ✅ cerrada |
| 2 | `POST` con `choices: []` → 400 | `test_persistence.py` | R-SER-20 | ✅ cerrada |
| 3 | `POST` con 3 opciones, 0 correctas → 400 | `test_persistence.py` / `test_http_matrix.py` | R-SER-22, R-SER-12 | ✅ cerrada |
| 4 | `POST` con 1 sola opción → 400 | idem | R-SER-19 | ✅ cerrada |
| 5 | `POST` sin `choices` → 400 | idem | R-SER-18 | ✅ cerrada |
| 6 | `POST` con `exam` inexistente → 400 | idem | R-SER-15 | ✅ cerrada |
| 7 | `POST /api/exams/` sin `title` → 400; campos de solo lectura ignorados | `test_http_matrix.py` | R-SER-02…06, R-API-02 | ✅ cerrada |
| 8 | `?exam=abc` → 400 | `test_services.py::ExamFilterTests` | R-VIE-08 | ✅ cerrada |
| 9 | `?exam=&search=` combinados | `test_api.py` / `test_http_matrix.py` | R-VIE-07 | ✅ cerrada |
| 10 | `?page=2` y `?page=999` → 404 | `test_http_matrix.py` | R-VIE-10 | ✅ cerrada |
| 11 | `assertNumQueries` en el listado de preguntas | `test_query_counts.py` | R-VIE-11 | ✅ cerrada |
| 12 | `POST /api/exams/{id}/` → 405; `text/plain` → 415 | `test_http_matrix.py::VerbAndRoleMatrixTests` | R-API-18, R-API-19 | ✅ cerrada |
| 13 | `GET /api/choices/` → 404 | `test_http_matrix.py` | R-SER-31 | ✅ cerrada |
| 14 | Orden estable por `id` | `test_api.py` | R-VIE-04 | ✅ cerrada |
| 15 | El lector ve todos los exámenes | `test_http_matrix.py` | R-VIE-16 | ✅ cerrada |
| 16 | `question_count` en la respuesta de `POST /api/exams/` | — | R-SER-08 | 🔴 **abierta** (depende de Q-04, sin decidir) |
| 17 | `PATCH`/`PUT` **con** `choices` las reemplaza y es atómico | `test_persistence.py` | R-SER-27, R-SER-29 | ✅ cerrada |
| 18 | El parámetro `exam` aparece en el esquema OpenAPI | `test_api.py` | R-VIE-13 | ✅ cerrada |
| 19 | El esquema es accesible sin token | `test_api.py` + verificado en vivo | R-VIE-18, R-REP-08 | ✅ cerrada |
| 20 | Método desconocido → denegado por defecto | `test_services.py::DenyByDefaultTests` | R-API-53 | ✅ cerrada |
| 21 | El agente puede/no puede modificar exámenes | `test_http_matrix.py::VerbAndRoleMatrixTests` | R-API-54, A-06 | ✅ cerrada (ADR-0003) |
| 22 | Arranque con `DEBUG=False` y sin `DJANGO_SECRET_KEY` (y sin `DJANGO_ALLOWED_HOSTS`) | `test_config_hardening.py::StartupGuardTests` | R-REP-03 | ✅ **cerrada** (`a82978e`: el arranque falla con `ImproperlyConfigured`; antes dependía de una decisión sin tomar) |
| 23 | `SpectacularAPIView` acepta o no token → fijar la postura del contrato | `test_api.py` + verificado en vivo | R-VIE-18, R-REP-08, Q-11 | ✅ cerrada |
| 24 | **Frontera de confianza** (sesión ↔ API, token ↔ UI, CSRF) | `test_web.py::FrontierTests`, `test_http_matrix.py::SessionTokenFrontierTests` | R-UI-T3 | ✅ cerrada |
| 25 | **Regresión:** los 4 entregables siguen verdes tras tocar `settings.py` | Suite completa (365 OK) | R-UI-T7 | ✅ cerrada |
| 26 | Veredicto RN-01/RN-02 compartido: la misma pregunta inválida se rechaza por API **y** por formulario | `test_services.py::SameVerdictTests` | R-UI-T5 | ✅ cerrada |
| 27 | Matriz completa por rol **en la interfaz** (el agente edita y no ve «Eliminar») | `test_permissions.py` | R-UI-07, ADR-0003 §verificación | 🔴 **abierta** (parcial: hoy hay un 403 global probado) |
| 28 | Contraste ≥ 4.5:1 verificado con herramienta | `test_web.py` | R-UI-11 | 🔴 **abierta** (hoy es revisión a ojo) |
| 29 | Ninguna credencial en el código: clave no publicada, generada y fuera de git | `test_config_hardening.py::SecretKeyTests` | R-REP-03, R-REP-05 | ✅ **cerrada** (`a82978e`) |
| 30 | `seed_quiz` sin tokens en claro salvo `--show-tokens`, y nunca la contraseña | `test_config_hardening.py::SeedOutputTests` | R-REP-05, SUI-04 | ✅ **cerrada** (`a82978e`) |
| 31 | Cabeceras de seguridad de la interfaz: `X-Frame-Options: DENY` y CSP, **solo** en HTML | `test_config_hardening.py::ResponseHeaderTests` | SUI-05, R-UI-10 | ✅ **cerrada** (`a82978e`) |
| 32 | El login de la interfaz limita los intentos fallidos | — | SUI-03 | 🔴 **abierta** (riesgo aceptado del laboratorio; no hay enumeración de usuarios) |

---

## 8. Flujo recomendado (quien lo ejecute)

> **Actualización: los pasos 1 a 6 están ejecutados.** Se conserva el plan original como registro; el
> estado real de cada punto está en las filas de §2 a §7.

1. ~~`backend-django` implementa `quizctl.exit_code_for` + `build_question_payload`~~ → **hecho** (`cf61a11`).
2. ~~`seguridad` + `backend-django` implementan `AgentPermission`~~ → **hecho** (`cf61a11`, tabla compartida en ADR-0003).
3. ~~`tester` ejecuta `python manage.py test` y confirma **R-REP-07**~~ → **hecho**: `Ran 365 tests ... OK`.
4. `tester` cubre los huecos de §7 → **hecho en su mayor parte** (ficheros nuevos en `7992f2a`); quedan
   cuatro abiertos, listados al final de §7.
5. `arquitecto` decide Q-04, Q-05, Q-06 → **Q-05 y Q-06 resueltas** (400 en `?exam=` no entero; el agente
   puede modificar exámenes pero no borrar). **Q-04 sigue abierta** (`question_count` en las escrituras).
6. `documentador` actualiza el README → **hecho** (README reescrito con la tabla de la API y la interfaz).
7. `revisor-codigo` revisa los cambios → **hecho** (`docs/revision-codigo.md`: veredicto CAMBIOS, 1
   bloqueante, 9 importantes, 20 menores) y **corregido** (`7992f2a`).
8. Cierre: criterios de aceptación cumplidos y sin hallazgos críticos abiertos → **alcanzado**, con las
   salvedades de [[12-Limitaciones-y-pendientes]].

---

## 9. Nota de honestidad

- **Fase A/B (lo que sigue):** no se había ejecutado ninguna prueba en el momento de escribir el
  documento; los estados `✅ cubierto` significaban *prueba presente*, no *prueba verde*.
- **Estado actual (añadido al cerrar la implementación):** `python manage.py test` se ejecutó de verdad
  y devolvió **`Ran 365 tests ... OK`**, y la matriz HTTP y la interfaz se comprobaron en vivo contra el
  servidor. Ese es el fundamento de las marcas 🟢 de las filas corregidas.
- Las citas `archivo:línea` se obtuvieron **leyendo** el repositorio; son verificables.
- **No se ha inventado ningún requisito del campus**: el texto oficial de la rúbrica no está en el
  repositorio. Los 4 criterios proceden del enunciado de la misión. **Esto sigue vigente.**
- **No hay secretos** en este documento. `seed_quiz` ya **no** imprime los tokens salvo que se pida con
  `--show-tokens` (`a82978e`); aquí solo se menciona el mecanismo, nunca un valor. Lo mismo con
  `DJANGO_SECRET_KEY`: solo se nombra la variable, nunca su valor ni la clave generada en `.secret_key`.
- El proyecto de referencia S07 se ha usado **solo como lectura** para describir el patrón de UI del curso
  (`blog/views.py`, `blog/templates/…`, `blog/static/css/style.css`, `config/settings.py`). **No se ha
  escrito en él.**
