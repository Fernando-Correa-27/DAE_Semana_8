"""The API seen from OUTSIDE, over a real socket, by a client that is not Django.

``test_quizctl.CliLiveTests`` and ``test_agent`` already speak HTTP against a live server,
but through this project's own code. This module uses ``requests`` directly: it is the
point of view of any other program (a script, a CI job, another team), and it is the only
place where the wire format itself is checked - the ``Authorization`` header, the
``Content-Type`` of the answer, the ``Location`` of a created resource and the absolute
URLs of the pagination links.

The server is the one ``LiveServerTestCase`` starts, on 127.0.0.1 (not «localhost»: on
Windows it tries IPv6 first and every request waits).
"""
import requests
from django.test import LiveServerTestCase

from quiz.models import Question

from .helpers import exam_id, seed

EXAMS = "/api/exams/"
QUESTIONS = "/api/questions/"


class ExternalHttpClientTests(LiveServerTestCase):
    host = "127.0.0.1"

    def setUp(self):
        self.person, self.agent = seed()
        self.exam = exam_id()
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Token {self.person}",
            "Accept": "application/json",
        })

    def url(self, path):
        return self.live_server_url + path

    def get(self, path, params=None):
        return self.session.get(self.url(path), params=params, timeout=10)

    def post(self, path, body):
        return self.session.post(self.url(path), json=body, timeout=10)

    def delete(self, path):
        return self.session.delete(self.url(path), timeout=10)

    def valid_body(self, text="¿Qué es una API REST?"):
        return {
            "exam": self.exam,
            "text": text,
            "choices": [
                {"text": "Un estilo de arquitectura sobre HTTP", "is_correct": True},
                {"text": "Un lenguaje de programación", "is_correct": False},
            ],
        }

    # --- listing -------------------------------------------------------------------------------

    def test_listing_the_exams(self):
        """GET /api/exams/ -> 200 with the two exams of the seed."""
        response = self.get(EXAMS)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "application/json")
        payload = response.json()
        self.assertEqual(payload["count"], 2)
        self.assertEqual({exam["title"] for exam in payload["results"]}, {"Django · ORM", "Django · Plantillas"})

    def test_listing_the_questions(self):
        """GET /api/questions/ -> 200, paginated five at a time."""
        payload = self.get(QUESTIONS).json()
        self.assertEqual((payload["count"], len(payload["results"])), (8, 5))

    # --- creating ------------------------------------------------------------------------------

    def test_creating_a_question(self):
        """POST /api/questions/ -> 201 and the new resource is readable."""
        response = self.post(QUESTIONS, self.valid_body())
        self.assertEqual(response.status_code, 201)
        created = response.json()
        self.assertEqual(created["exam"], self.exam)
        self.assertEqual(len(created["choices"]), 2)

        read_back = self.get(f"{QUESTIONS}{created['id']}/")
        self.assertEqual(read_back.status_code, 200)
        self.assertEqual(read_back.json()["text"], "¿Qué es una API REST?")
        self.assertEqual(Question.objects.count(), 9)

    def test_the_created_resource_is_announced_in_the_body_not_in_a_location_header(self):
        """Obtained behaviour, pinned: the 201 has NO ``Location`` header.

        DRF's ``CreateModelMixin`` answers 201 with the serialized object and leaves the
        ``Location`` header out (Django's own ``HttpResponseCreated`` would set it). A
        client must therefore read the new ``id`` from the body and build the URL, which is
        what ``quizctl`` and ``agent.gateway`` do. Worth pinning: if a future Django/DRF
        adds the header, the clients can be simplified and this test says so.
        """
        response = self.post(QUESTIONS, self.valid_body())
        self.assertEqual(response.status_code, 201)
        self.assertNotIn("Location", response.headers)
        location = self.live_server_url + f"{QUESTIONS}{response.json()['id']}/"
        self.assertEqual(self.session.get(location, timeout=10).status_code, 200)

    def test_a_body_that_breaks_a_rule_is_400_with_the_reason(self):
        """POST with two correct options -> 400, and the reason travels in the body."""
        body = self.valid_body()
        body["choices"] = [{"text": "a", "is_correct": True}, {"text": "b", "is_correct": True}]
        response = self.post(QUESTIONS, body)
        self.assertEqual(response.status_code, 400)
        self.assertIn("exactamente una", response.text)
        self.assertEqual(Question.objects.count(), 8)

    # --- filtering and searching ----------------------------------------------------------------

    def test_filtering_by_exam(self):
        """GET /api/questions/?exam=<id> -> 200 with only that exam's questions."""
        response = self.get(QUESTIONS, params={"exam": self.exam})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["count"], 4)
        self.assertEqual({question["exam"] for question in payload["results"]}, {self.exam})

    def test_searching(self):
        """GET /api/questions/?search=<text> -> 200 with the questions that match."""
        response = self.get(QUESTIONS, params={"search": "prefetch_related"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)

    def test_the_next_page_link_is_an_absolute_url_of_this_server(self):
        """The link the client is told to follow points at the server that answered.

        A pagination link built with another host (the classic «testserver» trap) would send
        a real client somewhere that does not exist.
        """
        payload = self.get(QUESTIONS).json()
        self.assertTrue(payload["next"].startswith(self.live_server_url), payload["next"])
        self.assertEqual(self.session.get(payload["next"], timeout=10).status_code, 200)

    # --- deleting ------------------------------------------------------------------------------

    def test_deleting_a_question(self):
        """DELETE /api/questions/<id>/ -> 204 and then the resource is a 404."""
        created = self.post(QUESTIONS, self.valid_body()).json()
        response = self.delete(f"{QUESTIONS}{created['id']}/")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")
        self.assertEqual(self.get(f"{QUESTIONS}{created['id']}/").status_code, 404)
        self.assertEqual(Question.objects.count(), 8)

    def test_deleting_something_that_does_not_exist_is_404(self):
        """DELETE of an unknown id -> 404 over the wire as well."""
        self.assertEqual(self.delete(f"{QUESTIONS}99999/").status_code, 404)

    def test_the_agent_token_cannot_delete_over_http(self):
        """The role is decided by the SERVER even when the client is a well formed request."""
        agent_session = requests.Session()
        agent_session.headers.update({"Authorization": f"Token {self.agent}", "Accept": "application/json"})
        question = Question.objects.first()
        response = agent_session.delete(self.url(f"{QUESTIONS}{question.id}/"), timeout=10)
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Question.objects.filter(id=question.id).exists())

    # --- without a token ------------------------------------------------------------------------

    def test_without_a_token_the_listing_is_401(self):
        """No ``Authorization`` header -> 401, and the body says which scheme is expected."""
        response = requests.get(self.url(EXAMS), headers={"Accept": "application/json"}, timeout=10)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Las credenciales de autenticación no se proveyeron.")
        self.assertIn("Token", response.headers.get("WWW-Authenticate", ""))

    def test_with_a_wrong_token_the_listing_is_401(self):
        """An unknown key is a 401 too, never a 403 and never a 500."""
        response = requests.get(
            self.url(EXAMS), headers={"Authorization": "Token nonsense", "Accept": "application/json"}, timeout=10
        )
        self.assertEqual(response.status_code, 401)

    def test_without_a_token_a_write_is_401_and_writes_nothing(self):
        """POST with no token -> 401 and the database does not move."""
        response = requests.post(self.url(QUESTIONS), json=self.valid_body(), timeout=10)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(Question.objects.count(), 8)

    # --- the contract from outside ----------------------------------------------------------------

    def test_the_contract_is_readable_over_http_without_a_token(self):
        """GET /api/schema/?format=json -> 200 for anybody, exactly as quizctl's ``ops`` needs."""
        response = requests.get(self.url("/api/schema/"), params={"format": "json"}, timeout=10)
        self.assertEqual(response.status_code, 200)
        schema = response.json()
        self.assertIn("/api/questions/", schema["paths"])
        self.assertIn("tokenAuth", schema["components"]["securitySchemes"])