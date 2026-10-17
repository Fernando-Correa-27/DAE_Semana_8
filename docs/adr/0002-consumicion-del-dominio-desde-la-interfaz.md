# ADR-0002 · Cómo consume la interfaz el dominio

- **Estado:** aceptada
- **Fecha:** 2026-10-16
- **Decide:** el Arquitecto de software
- **Depende de:** [ADR-0001](0001-arquitectura-de-la-interfaz-web.md)

## Contexto

La interfaz y la API son **dos presentaciones del mismo dominio** (exámenes, preguntas,
opciones). Hay que decidir cómo llega la interfaz a los datos y, sobre todo, **dónde vive la
regla de negocio**.

Hoy la regla está atada al transporte:

```python
# quiz/serializers.py:31-36
def validate_choices(self, value):
    if len(value) < 2:
        raise serializers.ValidationError("Una pregunta necesita al menos dos opciones.")
    if sum(1 for choice in value if choice.get("is_correct")) != 1:
        raise serializers.ValidationError("Debe haber exactamente una opción correcta.")
```

Lo mismo ocurre con la escritura atómica (`create`/`update` con `transaction.atomic` y
`bulk_create`, `serializers.py:38-51`) y con el filtrado de lectura (`get_queryset`,
`views.py:26-31`).

La interfaz tiene tres caminos posibles, y dos de ellos son trampas.

## Alternativas consideradas

### A. La UI habla HTTP con su propia API, desde dentro del proceso

Es decir, las vistas web llaman a `https://127.0.0.1:8000/api/questions/` con `requests`,
igual que lo hace `quizctl.py`.

**Problemas concretos, no teóricos:**

1. **Hay que inventar una identidad.** La UI autentica por sesión; la API, por token. La
   petición interna necesita un token *del usuario que está usando el navegador*. El servidor
   tendría que emitirlo, guardarlo y mandarlo en cada llamada. Eso es un token persistente
   guardado en un servidor web: una credencial de larga vida dentro de una base de datos.
   Y si en vez de emitirlo se reutiliza el token fijo de `seed_quiz`, entonces **la UI deja de
   comprobar los roles**: el agente podría borrar desde el navegador con el token de `profe`,
   y la frontera de la Parte 3 se deshace sin que nadie lo note.
2. **La UI no funcionaría sin servidor levantado.** `runserver` es un proceso: si la UI
   necesita HTTP contra sí mismo, basta con tener el puerto ocupado o el single‑threaded
   bloqueado para que la interfaz se caiga. Con SQLite y un servidor no concurrente, además,
   aparece el riesgo real de *database is locked*.
3. **Un agujero CSRF inevitable.** Un POST del navegador a la API propia tendría que marcarse
   `csrf_exempt` para no fallar el token CSRF. Se desactiva la protección exactamente en la
   única superficie de escritura por sesión que introduce la UI.
4. **Errores inmanejables.** La validación vive en el servidor y llega como un JSON 400. Sin
   validación en el formulario, el usuario ve «400 Bad Request» sin saber qué campo falla; con
   validación en el formulario, ya se ha duplicado la regla.
5. **Coste y latencia** para serializar y deserializar datos que ya están en el proceso, más
   el servidor de pruebas lento (`LiveServerTestCase` en vez de `TestCase`).

**Descartada.**

### B. La UI usa el ORM directamente, cada vista por su cuenta

`Question.objects.create(...)` en la vista, con sus propias reglas.

Es la tentación real, y por eso hay que decirla en voz alta: es **lo más rápido de escribir**
y parece «una capa más fina». Y es exactamente el error que este ADR existe para evitar, porque:

- la invariante de opciones **deja de existir** para la UI (o se copia, y quedan dos
  redacciones del mismo mensaje);
- la escritura deja de ser atómica: una pregunta sin sus opciones, o con la mitad de ellas,
  queda guardada si algo falla en medio;
- los roles se deciden con `if user.is_staff:` sueltos, en una decena de vistas, que
  nadie lee entera.

**Descartada.**

### C. Híbrido: la UI lee del ORM y escribe por HTTP

La peor de las dos: dos caminos de escritura con garantías distintas, y una clase de bug
difícil de ver («funciona en la web, no funciona en la API»).

**Descartada por principio de mínima superficie.**

### D. La UI consume el dominio en proceso, a través de servicios compartidos ← **elegida**

## Decisión

1. **Se extrae la regla de negocio a `quiz/services.py`**, fuera de cualquier capa de
   transporte. El servicio expone la invariante y las escrituras atómicas:

   ```python
   # quiz/services.py  (nombres y comentarios en inglés)
   def question_rules(choices) -> list[str]:
       """THE domain invariant: at least two options, exactly one correct.
       Returns the list of violations; empty means valid. One place, no exceptions."""

   def create_question(*, exam, text, choices) -> Question: ...
   def update_question(question, *, exam=None, text=None, choices=None) -> Question: ...
   ```

2. **`QuestionSerializer.validate_choices` pasa a delegar** en `question_rules()`, y
   `create`/`update` en `create_question`/`update_question`. El comportamiento público de la
   API **no cambia**: mismos mensajes, mismos códigos HTTP, mismo orden.
   **Los textos se copian carácter a carácter**, porque
   `quiz/tests/test_api.py:57` comprueba que el 400 contiene `"exactamente una"`.
   Mover una regla no puede cambiar su redacción.

3. **El formulario de la UI hace lo mismo**: `QuestionFormSet.clean()` llama a
   `question_rules()` y traduce la lista de errores a `ValidationError` de Django. No reescribe
   los mensajes: los muestra.

4. **`quiz/queries.py`** recoge las lecturas (el `select_related`/`prefetch_related` de
   `views.py:27` y los filtros de `?exam=`/`?search=`) para que la lista web y la lista de la
   API lean igual. La UI no escribe una consulta «parecida»: usa la misma función.

5. **Prohibición explícita**: las vistas web **no** llaman a `objects.create()` ni a `.save()`
   sobre `Question`/`Choice`, y **no** comprueban roles con `if user.is_staff:`. Pasan por
   `services` y por `permissions.may()` (ADR-0003).

### Por qué esto no es «duplicar la API»

La API y la UI **no se llaman entre sí**. Son dos presentaciones que dependen del mismo
dominio. La invariante tiene **una** implementación; el permiso tiene **una** tabla. Lo que se
elimina no es la lógica, es la **duplicación** de la lógica.

Y el laboratorio mejora: la pasarela del agente sigue hablando HTTP con la API de verdad, y
`quizctl.py` sigue siendo un cliente externo de verdad. La UI no falsea ninguno de los dos
entregables; simplemente se apoya en el mismo suelo.

### La costura queda abierta

`services.py` es **la única** pieza que habría que cambiar si el campus exigiera
literalmente «la UI consume la API por HTTP»: sus funciones pasarían a hacer la llamada
remota y a devolver el mismo tipo de valor. Las vistas de la UI, los formularios y las
plantillas **no se tocarían**. Esa es la prueba de que la decisión está bien tomada: el punto
de disagreement está aislado en un solo módulo, no disperso por toda la aplicación.

## Consecuencias

**A favor**

- Una sola redacción de la invariante; imposible que la UI acepte algo que la API rechaza.
- Escrituras atómicas en los dos caminos.
- Los roles de la UI y de la API salen de la misma tabla (ADR-0003).
- Pruebas de UI rápidas con `django.test.TestCase` (sin servidor).
- El coste está contenido en un archivo (`services.py`, ~50 líneas) que se puede mover entero.

**En contra / costes asumidos**

- Un refactor real del entregable ya entregado: `serializers.py` pasa a delegar. Hay que
  dejar `test_api.py` **intacto** como red de seguridad; si hay que tocarlo, se ha roto algo.
- `services.py` es código nuevo que el revisor tiene que leer con atención: es donde ahora
  vive la regla.
- Se pierde la propiedad, afirmada dos veces por costumbre, de «si funciona en la web,
  funciona en la API». Se compensa con `quiz/tests/test_services.py`, que **verifica la
  invariante una vez** y comprueba que serializer y formset coinciden.

## Verificación

1. `python manage.py test` verde, con `test_api.py` sin modificar.
2. `test_services.py` contiene una prueba que **afirma** que el mismo cuerpo inválido recibe el
   mismo veredicto por el serializador y por el formset.
3. Un `grep` de `web_views.py` no encuentra ni `objects.create(` ni `objects.filter(...).delete()`
   sobre `Question`/`Choice`.
4. El mensaje de la respuesta 400 sigue conteniendo `"exactamente una"` y
   `"al menos dos opciones"`.
5. La UI funciona con el servidor de la API apagado (es la misma prueba de que no hay HTTP
   oculto).
