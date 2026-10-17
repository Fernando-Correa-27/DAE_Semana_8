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

**Documentos relacionados del equipo** (escritos por otros agentes en el mismo repositorio):

| Documento | Qué aporta a esta matriz |
|---|---|
| `docs/arquitectura.md` | Decisión de arquitectura de la UI, cambios en `settings.py`, tabla de permisos (Parte 3) y tabla de la API |
| `docs/adr/0001-arquitectura-de-la-interfaz-web.md` | ADR aprobado de la UI: server-rendered, sin CDN, sin `admin` |
| `docs/frontera-ia.md` | Auditoría de la frontera del agente (R0/R1/R2) y del texto hostil |

> Cuando una decisión de arquitectura responda a una **pregunta abierta** de `docs/requisitos.md` §14,
> esta matriz debe actualizarse en lugar de abrir una segunda vía. Hoy: **Q-02 y Q-03 están respondidas**,
> y **Q-11 es un punto que el arquitecto marcó sin verificar y que este documento acepta como abierto**.

---

## 1. Resumen de cobertura

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
| R-VIE-08 | `views.py:29` guarda `if exam and exam.isdigit()` | *ninguna* → crear tras la decisión Q-05 | ⚪ decisión |
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
| R-API-07 | `DELETE` por agente/lector | **`quiz/permissions.py:20` `return True`** → hoy responde **204, no 403** | `test_permissions.py:40,43,49,50` (**fallan hoy**) | 🔴 pendiente |
| R-API-08 | `GET /api/questions/` | `QuestionViewSet` (`views.py:21-31`) | `test_api.py:28,41` | ✅ cubierto |
| R-API-09 | `GET /api/questions/?exam=&search=&page=` | `views.py:26-31` + `settings.py:52` | `test_api.py:33,37,28` + `test_quizctl.py:75-79` (`--exam` + `--json` + `count==4`) | ✅ cubierto |
| R-API-10 | `POST /api/questions/` | `QuestionSerializer.create` (`serializers.py:38-43`) | `test_api.py:46` + `test_permissions.py:25` (agente) + `test_agent.py:50` + `test_quizctl.py:81` | ✅ cubierto |
| R-API-11 | `GET /api/questions/{id}/` | `ModelViewSet.retrieve` | `test_api.py:79` (404 tras borrar) + `test_agent.py:32` (`questions_list`) | 🟡 parcial |
| R-API-12 | `PATCH /api/questions/{id}/` | `QuestionSerializer.update` (`serializers.py:45-52`) | `test_api.py:70` + `test_permissions.py:29` | ✅ cubierto |
| R-API-13 | `PUT /api/questions/{id}/` | `update` + campos requeridos | *ninguna* → crear (incompleto → 400; completo → 200) | 🟡 parcial |
| R-API-14 | `DELETE /api/questions/{id}/` (persona) | `ModelViewSet.destroy` | `test_api.py:76-79` + `test_permissions.py:43` + `test_agent.py:64-70` | ✅ cubierto |
| R-API-15 | `GET /api/schema/`, `/api/docs/` | `config/urls.py:7-8` | `test_api.py:86,96` + `test_quizctl.py:120-122` + `agent/gateway.py:52` | ✅ cubierto |
| R-API-16 | Sin token / token inválido → **401** | `settings.py:46-51` (`TokenAuthentication` + `IsAuthenticated`) | `test_api.py:15,19` + `test_permissions.py:53` + `test_quizctl.py:110` | ✅ cubierto |
| R-API-17 | Autenticado sin permiso → **403** | `quiz/permissions.py` (**TODO**) | `test_permissions.py:34,40,49` (**fallan hoy**) | 🔴 pendiente |
| R-API-18 | Método no permitido → **405** | `ModelViewSet` de DRF | *ninguna* → crear (`POST /api/exams/{id}/`) | 🟡 parcial |
| R-API-19 | `Content-Type` no soportado → **415** | Parsers por defecto de DRF | *ninguna* → crear (`text/plain`) | 🟡 parcial |
| R-API-20 | Fallo interno → **5xx** sin filtrar datos | `settings.py:10` `DEBUG=True` (**expone detalles**) | *ninguna*; requiere R-REP-03 | 🟡 parcial |

### 4.2 Códigos de salida de `quizctl` (Parte 2 — ambos `TODO`)

| Req | Implementación prevista | Prueba que lo demuestra | Estado |
|---|---|---|---|
| R-API-21 | `quizctl.py:45-50` `exit_code_for` — `200 <= s < 300 → 0` | `test_quizctl.py:17-19` `test_success_is_zero` | 🔴 pendiente |
| R-API-22 | `400 → EXIT_VALIDATION (2)` | `test_quizctl.py:21-22` | 🔴 pendiente |
| R-API-23 | `401, 403 → EXIT_FORBIDDEN (3)` | `test_quizctl.py:24-26` | 🔴 pendiente |
| R-API-24 | `404 → EXIT_NOT_FOUND (4)` | `test_quizctl.py:28-29` | 🔴 pendiente |
| R-API-25 | `5xx → EXIT_SERVER (5)` | `test_quizctl.py:31-33` | 🔴 pendiente |
| R-API-26 | resto → `EXIT_OTHER (1)` | `test_quizctl.py:35-37` | 🔴 pendiente |
| R-API-27 | `quizctl.py:53-64` `build_question_payload` — `rsplit(":ok", 1)` | `test_quizctl.py:41-46` `test_ok_marks_the_correct_choice` | 🔴 pendiente |
| R-API-28 | misma función (solo el `:ok` final) | `test_quizctl.py:48-51` `test_only_the_final_ok_counts` | 🔴 pendiente |
| R-API-29 | misma función (sin validación local) | `test_quizctl.py:53-55` + `test_quizctl.py:87-91` | 🔴 pendiente |
| R-API-30 | `quizctl.py:73-74` sin `QUIZ_TOKEN` → `Result(status=-1)` → `main` devuelve `EXIT_OTHER` | `test_quizctl.py:114-115` | ✅ cubierto (no depende del TODO) |
| R-API-31 | `quizctl.py:83-84` `except requests.RequestException` → `status=0` → `EXIT_NETWORK` | `test_quizctl.py:117-118` | ✅ cubierto |
| R-API-32 | `quizctl.py:76-77` `if dry_run and method != "GET"` | `test_quizctl.py:93-99` `test_dry_run_describes_and_creates_nothing` | ✅ cubierto |
| R-API-33 | `quizctl.py:146-150` `render` con `--json` | `test_quizctl.py:75-79`, `81-85`, `87-91` | ✅ cubierto |
| R-API-34 | `quizctl.py:134-143` `ops` lee `/api/schema/?format=json` | `test_quizctl.py:120-122` `test_ops_lists_the_contract` | ✅ cubierto |
| R-API-35 | 403 del servidor → salida 3 | `test_quizctl.py:104-108` (`CliLiveTests`) — **requiere la Parte 3** | 🔴 pendiente |
| R-API-36 | 404 → salida 4 | `test_quizctl.py:101-102` | 🟡 parcial (falla mientras `exit_code_for` no exista) |

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

### 4.4 Reglas de roles (Parte 3 — `quiz/permissions.py` TODO)

| Req | Implementación prevista | Prueba que lo demuestra | Estado |
|---|---|---|---|
| R-API-47 | `permissions.py:19-20` → `request.user.is_staff → True` | `test_permissions.py:43-45` `test_a_person_can_delete` (**falla hoy**) | 🔴 pendiente |
| R-API-48 | `permissions.py:19-20` → grupo `AGENT_GROUP` y método en `{GET, POST, PUT, PATCH}` | `test_permissions.py:22,25,29` (**fallan hoy**) | 🔴 pendiente |
| R-API-49 | `permissions.py:19-20` → `request.method == "DELETE"` con agente → `False` | `test_permissions.py:34-38` `test_the_agent_cannot_delete` (**falla hoy**) | 🔴 pendiente |
| R-API-50 | misma rama, aplicada a `ExamViewSet` | `test_permissions.py:40-41` `test_the_agent_cannot_delete_an_exam_either` (**falla hoy**) | 🔴 pendiente |
| R-API-51 | `permissions.py:19-20` → resto autenticado: solo métodos seguros | `test_permissions.py:47-51` `test_somebody_without_a_role_can_only_read` (**falla hoy**) | 🔴 pendiente |
| R-API-52 | `settings.py:48-51` `IsAuthenticated` antes de `AgentPermission` | `test_permissions.py:53-55` `test_no_token_is_401_not_403` (ya verde: no depende del TODO) | ✅ cubierto |
| R-API-53 | `permissions.py:13` «an unknown method is denied» | *ninguna* explícita → crear (p. ej. método no en la lista blanca) | 🟡 parcial |
| R-API-54 | Regla ambigua: ¿el agente puede `PATCH /api/exams/{id}/`? | *ninguna* → decidir Q-06 y luego crear | ⚪ decisión |

---

## 5. Criterio 4-A — Repositorio

| Req | Implementación / evidencia | Cómo se demuestra | Estado |
|---|---|---|---|
| R-REP-01 | `README.md:10-31` (puesta en marcha), `:33-105` (partes), `:63-71` (códigos) | Revisión documental + seguir los comandos en una máquina limpia | 🟡 parcial (el README dice que las Partes 2 y 3 «fallarán» — **quedará desactualizado** en cuanto se implementen) |
| R-REP-02 | `requirements.txt:1-4` | Lectura del archivo + `pip install -r` | ✅ cubierto |
| R-REP-03 | `settings.py:9-10` (`SECRET_KEY` con reserva + `DEBUG=True`) — **hoy es inseguro** | Revisión de configuración; prueba de que con `DEBUG=False` y sin `DJANGO_SECRET_KEY` el arranque falla | 🔴 pendiente |
| R-REP-04 | `.gitignore:1-7` | Lectura del archivo | ✅ cubierto |
| R-REP-05 | `seed_quiz.py:49-55` **imprime** tokens, pero no los versiona | `rg` de valores de token en el árbol (verificación pendiente, sin terminal en esta fase) | 🟡 parcial |
| R-REP-06 | `config/`, `quiz/`, `agent/`, `quizctl.py`, `quiz/tests/` | Estructura del árbol | ✅ cubierto |
| R-REP-07 | `python manage.py test` — **no ejecutado en esta fase** | Ejecutar los 4 módulos; hoy fallan `test_quizctl` y `test_permissions` por los `TODO` | 🔴 pendiente |
| R-REP-08 | `README.md:39` (`spectacular --file schema.yml`); `.gitignore:7` lo excluye. Legible sin token: **sin verificar** (Q-11) | Ejecutar el comando; comprobar `SpectacularAPIView.permission_classes` | 🟡 parcial |
| R-REP-09 | `AGENTS.md` §7; `README.md:117-119` | Revisión de estilo | ✅ cubierto |
| R-REP-10 | `AGENTS.md`, `opencode.json:1-4` | Lectura | ✅ cubierto |
| R-REP-11 | `seed_quiz.py:11-27` (`get_or_create`), `:35` (borra y recarga) | `helpers.py:8-13` (`call_command("seed_quiz")` en 3 clases de prueba) | ✅ cubierto |
| R-REP-12 | `quiz/migrations/0001_initial.py`; datos en `seed_quiz.py` | `python manage.py migrate` en BD vacía | 🟡 parcial (no ejecutado en esta fase) |
| R-REP-13 | `docs/` **no existe** (creado ahora con este documento); no hay ADR | Existe `docs/requisitos.md` y `docs/trazabilidad.md`; falta ADR si se decide la UI | 🟡 parcial |
| R-REP-14 | No hay CI ni script de verificación | — | 🔴 pendiente (opcional) |

---

## 6. Criterio 4-B — Tabla de API / interfaz gráfica (mejora adicional)

**Hecho comprobado:** esta capa **no existe**. `config/settings.py:13-20` no incluye `admin`, `sessions`,
`messages` ni `staticfiles`; `settings.py:22-25` solo tiene 2 middlewares; **no hay bloque `TEMPLATES`**;
**no existen** carpetas `templates/` ni `static/`.

**Arquitectura ya decidida** en `docs/adr/0001-arquitectura-de-la-interfaz-web.md` y `docs/arquitectura.md`:
server-rendered, `ModelForm` + `formset` en línea, CBVs en `quiz/web_views.py`, CSS propia sin CDN,
**sin `django.contrib.admin`**, API por token y UI por sesión sin mezclarse. Esta matriz usa esa estructura
como «implementación prevista»; **ninguna de estas pruebas existe todavía**.

| Req | Implementación prevista (ADR 0001) | Prueba prevista | Estado |
|---|---|---|---|
| R-UI-01 | `quiz/web_views.py::ExamListView` + `quiz/templates/quiz/exams/list.html` | `quiz/tests/test_ui.py::test_exam_table_shows_the_question_count` | 🔴 pendiente |
| R-UI-02 | `QuestionListView` + `questions/list.html` (columnas id, examen, texto, nº opciones, correcta) | `test_ui.py::test_question_table_shows_choices_and_the_correct_one` | 🔴 pendiente |
| R-UI-03 | `paginate_by=5` en las `ListView` + partial `_pagination.html` | `test_ui.py::test_the_table_is_paginated` | 🔴 pendiente |
| R-UI-04 | `get_queryset()` leyendo `GET["search"]` / `GET["exam"]` | `test_ui.py::test_search_and_filter_narrow_the_table` + `test_ui.py::test_the_filtered_url_is_shareable` | 🔴 pendiente |
| R-UI-05 | `ModelForm` de `Question` + `inlineformset_factory` para `Choice` con validación de RN-01/RN-02 | `test_ui.py::test_two_correct_choices_is_refused_and_the_form_keeps_the_data` | 🔴 pendiente |
| R-UI-06 | `DeleteView` + `*_confirm_delete.html` | `test_ui.py::test_delete_asks_for_confirmation` | 🔴 pendiente |
| R-UI-07 | Tabla de acciones compartida (`docs/arquitectura.md:316-321`) en las plantillas | `test_ui.py::test_the_agent_does_not_see_the_delete_button` | 🔴 pendiente |
| R-UI-08 | `403.html` / `404.html` / `500.html` propias | `test_ui.py::test_an_invalid_post_redisplays_the_form_with_errors` | 🔴 pendiente |
| R-UI-09 | Partial de estado vacío | `test_ui.py::test_an_empty_table_shows_an_empty_state` | 🔴 pendiente |
| R-UI-10 | `quiz/templates/quiz/base.html` + `partials/` + `quiz/static/quiz/css/style.css`, sin CDN | `test_ui.py::test_the_stylesheet_is_served_without_internet` | 🔴 pendiente |
| R-UI-11 | CSS: `:focus-visible`, contraste ≥ 4.5:1, `prefers-reduced-motion`, sin trampas de foco | Revisión de la hoja + navegación por tabulador | 🔴 pendiente |
| R-UI-12 | Sin JS obligatorio | `test_ui.py::test_the_ui_works_with_javascript_disabled` | 🔴 pendiente |
| R-UI-13 | `quiz/tests/test_ui.py` (patrón S07: `test_front_page`, `test_auth`, `test_crud`) | El propio módulo | 🔴 pendiente |
| R-UI-14 | **Sin** `django.contrib.admin` | `test_ui.py::test_the_admin_is_not_installed` (`/admin/` → 404) | 🔴 pendiente |
| R-UI-T1 | `settings.TEMPLATES` + `APP_DIRS` (`docs/arquitectura.md:216-240`) | Una prueba por vista renderizada | 🔴 pendiente |
| R-UI-T2 | `django.contrib.staticfiles` + `STATICFILES_DIRS` (`docs/arquitectura.md:164-190`) | `test_ui.py::test_the_stylesheet_is_served` | 🔴 pendiente |
| R-UI-T3 | **Frontera de confianza**: API por token, UI por sesión, no se mezclan (`docs/arquitectura.md:272-299`) | `test_ui.py::test_a_session_does_not_authenticate_the_api` (401) · `test_ui.py::test_a_token_does_not_authenticate_the_ui` (302) · `test_ui.py::test_the_ui_requires_a_csrf_token` (403 sin él) | 🔴 pendiente |
| R-UI-T4 | La UI usa el **ORM**, no la API por HTTP (ADR 0001) | — | ✅ decidido |
| R-UI-T5 | **Validador único** de RN-01/RN-02 compartido por el serializador y el `formset` | `test_ui.py::test_both_paths_reject_the_same_invalid_question` (una prueba por cada vía) | 🔴 pendiente |
| R-UI-T6 | La UI no expone acciones R2 sin aprobación humana | `test_ui.py::test_the_ui_offers_no_destructive_bulk_action` | 🔴 pendiente |
| R-UI-T7 | **Regresión:** los 4 entregables siguen verdes tras tocar `settings.py` (`docs/arquitectura.md:294-297`) | `python manage.py test` completo tras el cambio | 🔴 pendiente |

---

## 7. Huecos de prueba detectados (agenda del `tester`)

> Ordenados por riesgo. Todos **recomendados**: la API ya está verde en lo esencial; esto cierra los Huecos.

| # | Prueba a añadir | Módulo | Requisitos que cierra |
|---|---|---|---|
| 1 | `PUT` incompleto → 400 y completo → 200 | `test_api.py` | R-SER-30, R-API-13 |
| 2 | `POST` con `choices: []` → 400 | `test_api.py` | R-SER-20 |
| 3 | `POST` con 3 opciones, 0 correctas → 400 | `test_api.py` | R-SER-22, R-SER-12 |
| 4 | `POST` con 1 sola opción → 400 | `test_api.py` | R-SER-19 |
| 5 | `POST` sin `choices` → 400 | `test_api.py` | R-SER-18 |
| 6 | `POST` con `exam` inexistente → 400 | `test_api.py` | R-SER-15 |
| 7 | `POST /api/exams/` sin `title` → 400; con `title` de 121 → 400; con `created_at`/`question_count` → 201 e ignorados | `test_api.py` | R-SER-02…06, R-API-02 |
| 8 | `?exam=abc` → comportamiento acordado | `test_api.py` | R-VIE-08 (tras Q-05) |
| 9 | `?exam=&search=` combinados | `test_api.py` | R-VIE-07 |
| 10 | `?page=2` y `?page=999` → 404 | `test_api.py` | R-VIE-10 |
| 11 | `assertNumQueries` en el listado de preguntas | `test_api.py` | R-VIE-11 |
| 12 | `POST /api/exams/{id}/` → 405; `text/plain` → 415 | `test_api.py` | R-API-18, R-API-19 |
| 13 | `GET /api/choices/` → 404 (las opciones no tienen endpoint) | `test_api.py` | R-SER-31 |
| 14 | Orden estable por `id` en la lista y entre páginas | `test_api.py` | R-VIE-04 |
| 15 | El lector ve todos los exámenes (sin ACL por objeto) | `test_api.py` | R-VIE-16 |
| 16 | `question_count` en la respuesta de `POST /api/exams/` (según Q-04) | `test_api.py` | R-SER-08 |
| 17 | `PATCH`/`PUT` **con** `choices` las reemplaza y es atómico | `test_api.py` | R-SER-27, R-SER-29 |
| 18 | El parámetro `exam` aparece en el esquema OpenAPI | `test_api.py` | R-VIE-13 |
| 19 | El esquema es accesible sin token (contrato público) | `test_api.py` | R-VIE-18, R-REP-08 |
| 20 | Método desconocido → denegado por defecto | `test_permissions.py` | R-API-53 |
| 21 | El agente puede/no puede modificar exámenes (según Q-06) | `test_permissions.py` | R-API-54, A-06 |
| 22 | Arranque con `DEBUG=False` y sin `DJANGO_SECRET_KEY` | `test_settings.py` (nuevo) | R-REP-03 |
| 23 | `SpectacularAPIView` acepta o no token → fijar la postura del contrato | `test_api.py` | R-VIE-18, R-REP-08, Q-11 |
| 24 | **Frontera de confianza** (solo si se implementa la UI): sesión no autentica la API (401), token no autentica la UI (302), la UI exige CSRF (403) | `test_ui.py` | R-UI-T3 |
| 25 | **Regresión:** los 4 entregables siguen verdes tras tocar `settings.py` | suite completa | R-UI-T7 |
| 26 | Validador RN-01/RN-02 compartido: la misma pregunta inválida se rechaza por API **y** por formulario | `test_ui.py` | R-UI-T5 |

---

## 8. Flujo recomendado (quien lo ejecute)

1. `backend-django` implementa `quizctl.exit_code_for` + `build_question_payload` (**T-IMP-1, T-IMP-2**).
2. `seguridad` (aprobación) + `backend-django` implementan `AgentPermission` (**T-IMP-3**).
3. `tester` ejecuta `python manage.py test` y confirma **R-REP-07**.
4. `tester` cubre los 22 huecos de §7 en el orden indicado (**T-REC-1**).
5. `arquitecto` decide Q-04, Q-05, Q-06 (y ADR si entra la UI).
6. `documentador` actualiza `README.md:104-105` (que hoy dice que las pruebas fallarán) y añade la sección de UI si se aprueba.
7. `revisor-codigo` revisa los cambios.
8. Cierre: criterios de aceptación cumplidos y sin hallazgos críticos abiertos.

---

## 9. Nota de honestidad

- **No se ha ejecutado ninguna prueba** en la fase A/B: este documento no puede afirmar que algo «pasa», solo que
  **existe la prueba** que lo demostraría. Los estados `✅ cubierto` significan *prueba presente*, no *prueba verde*.
- Las citas `archivo:línea` se obtuvieron **leyendo** el repositorio; son verificables.
- **No se ha inventado ningún requisito del campus**: el texto oficial de la rúbrica no está en el repositorio
  (`README.md:8`). Los 4 criterios proceden del enunciado de la misión.
- **No hay secretos** en este documento. `seed_quiz` imprime tokens por terminal (`seed_quiz.py:49-55`); aquí solo
  se menciona el mecanismo, nunca un valor.
- El proyecto de referencia S07 se ha usado **solo como lectura** para describir el patrón de UI del curso
  (`blog/views.py`, `blog/templates/…`, `blog/static/css/style.css`, `config/settings.py`).
