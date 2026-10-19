"""The HTTP status matrix of the API: one test for every cell.

Why this file exists: ``test_api.py`` proves that the happy path works and that a few
errors are answered. It does not pin WHICH status each combination answers. This module
walks the whole matrix (route x verb x role x body) and compares the EXPECTED status with
the OBTAINED one, so a change in any cell fails loudly instead of silently.

Every test reads ``expected`` first and the server's answer second: if a cell moves, the
failure says which one, what was expected and what arrived. The statuses below were taken
from the delivered server (Django 5.2 + DRF); the ones that are DRF's own conventions
(401 for anonymous, 405 for a verb without a handler) are pinned on purpose: they are the
answer a client like ``quizctl`` or ``agent.gateway`` relies on.

Run only this module with:
    python manage.py test quiz.tests.test_http_matrix
"""
from django.contrib.auth.models import User
from django.test import Client

from rest_framework.test import APITestCase

from quiz.models import Exam, Question

from .helpers import exam_id, reader_token, seed, valid_body

EXAMS = "/api/exams/"
QUESTIONS = "/api/questions/"
UNKNOWN_ID = 99999


class StatusMatrixTestCase(APITestCase):
    """Shared plumbing: three identities and one place that compares expected vs obtained."""

    def setUp(self):
        self.person, self.agent = seed()
        self.reader = reader_token()
        self.exam = exam_id()
        self.question = Question.objects.first()

    def as_(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        return self.client

    def as_person(self):
        return self.as_(self.person)

    def as_agent(self):
        return self.as_(self.agent)

    def as_reader(self):
        return self.as_(self.reader)

    def anonymous(self):
        self.client.credentials()
        return self.client

    def assert_status(self, expected, response, cell):
        """Compare the expected status with the obtained one, naming the cell that moved."""
        self.assertEqual(
            expected,
            response.status_code,
            f"[{cell}] se esperaba {expected} y se obtuvo {response.status_code}: "
            f"{response.request.get('REQUEST_METHOD', '?')} {response.request['PATH_INFO']} "
            f"-> {response.content[:200]!r}",
        )

    def body(self, **changes):
        """A valid POST body with the given changes applied."""
        payload = valid_body(self.exam)
        payload.update(changes)
        return payload


# --- reads --------------------------------------------------------------------------------------


class ReadMatrixTests(StatusMatrixTestCase):
    def test_person_lists_exams(self):
        """GET /api/exams/ with a valid token -> 200."""
        self.assert_status(200, self.as_person().get(EXAMS), "person · GET exams · list")

    def test_person_reads_one_exam(self):
        """GET /api/exams/<id>/ of an existing exam -> 200."""
        self.assert_status(200, self.as_person().get(f"{EXAMS}{self.exam}/"), "person · GET exams · detail")

    def test_reading_an_exam_that_does_not_exist_is_404(self):
        """GET /api/exams/<unknown>/ -> 404 (and not 200 with an empty body)."""
        response = self.as_person().get(f"{EXAMS}{UNKNOWN_ID}/")
        self.assert_status(404, response, "person · GET exams · detail unknown")
        self.assertIn("detail", response.json())

    def test_person_lists_questions(self):
        """GET /api/questions/ -> 200, paginated."""
        self.assert_status(200, self.as_person().get(QUESTIONS), "person · GET questions · list")

    def test_person_reads_one_question(self):
        """GET /api/questions/<id>/ -> 200 with the options nested."""
        self.assert_status(200, self.as_person().get(f"{QUESTIONS}{self.question.id}/"),
                           "person · GET questions · detail")

    def test_reading_a_question_that_does_not_exist_is_404(self):
        """GET /api/questions/<unknown>/ -> 404."""
        self.assert_status(404, self.as_person().get(f"{QUESTIONS}{UNKNOWN_ID}/"),
                           "person · GET questions · detail unknown")

    def test_filtering_by_an_existing_exam_is_200(self):
        """GET /api/questions/?exam=<id> -> 200 with only that exam's questions."""
        response = self.as_person().get(QUESTIONS, {"exam": self.exam})
        self.assert_status(200, response, "person · GET questions · filter exam")
        self.assertEqual(response.json()["count"], 4)

    def test_filtering_by_an_exam_that_does_not_exist_is_an_empty_200(self):
        """GET /api/questions/?exam=<unknown> -> 200 with zero results (the exam is not an error)."""
        response = self.as_person().get(QUESTIONS, {"exam": UNKNOWN_ID})
        self.assert_status(200, response, "person · GET questions · filter unknown exam")
        self.assertEqual(response.json()["count"], 0)

    def test_a_filter_that_is_not_a_number_is_400(self):
        """GET /api/questions/?exam=abc -> 400 naming the parameter, not a silent 200.

        CHANGED ON 2026-10-16 (backend-django, review of the delivered server): this cell used
        to be pinned as 200 with everything, because ``get_queryset`` only filtered when the
        value was ``isdigit()``. That made ``?exam=²`` a 500 and a typo look like «everything».
        The contract now is the same one the body already had: a value that is not an exam id
        is a 400 that names «exam».
        """
        response = self.as_person().get(QUESTIONS, {"exam": "abc"})
        self.assert_status(400, response, "person · GET questions · filter not a number")
        self.assertIn("exam", response.json())

    def test_a_filter_that_is_digit_but_not_a_number_is_400(self):
        """GET /api/questions/?exam=² -> 400, and never the 500 that ``int("²")`` used to raise."""
        response = self.as_person().get(QUESTIONS, {"exam": "²"})
        self.assert_status(400, response, "person · GET questions · filter superscript two")
        self.assertIn("exam", response.json())

    def test_a_negative_filter_is_400(self):
        """GET /api/questions/?exam=-1 -> 400: an id of an exam is never negative."""
        response = self.as_person().get(QUESTIONS, {"exam": "-1"})
        self.assert_status(400, response, "person · GET questions · filter negative")
        self.assertIn("exam", response.json())

    def test_an_empty_filter_is_400(self):
        """GET /api/questions/?exam= (empty) -> 400: the caller asked for something."""
        response = self.as_person().get(QUESTIONS, {"exam": ""})
        self.assert_status(400, response, "person · GET questions · filter empty")
        self.assertIn("exam", response.json())

    def test_searching_is_200(self):
        """GET /api/questions/?search=<text> -> 200 with the matching questions."""
        response = self.as_person().get(QUESTIONS, {"search": "prefetch_related"})
        self.assert_status(200, response, "person · GET questions · search")
        self.assertEqual(response.json()["count"], 1)

    def test_a_search_with_no_match_is_an_empty_200(self):
        """GET /api/questions/?search=zzz -> 200 with zero results."""
        response = self.as_person().get(QUESTIONS, {"search": "zzz"})
        self.assert_status(200, response, "person · GET questions · search without matches")
        self.assertEqual(response.json()["count"], 0)

    def test_the_first_page_is_200(self):
        """GET /api/questions/?page=1 -> 200."""
        self.assert_status(200, self.as_person().get(QUESTIONS, {"page": 1}),
                           "person · GET questions · page 1")

    def test_the_last_page_is_200(self):
        """GET /api/questions/?page=2 -> 200 (8 questions, 5 per page)."""
        self.assert_status(200, self.as_person().get(QUESTIONS, {"page": 2}),
                           "person · GET questions · page 2")

    def test_a_page_that_does_not_exist_is_404(self):
        """GET /api/questions/?page=999 -> 404, not an empty 200."""
        self.assert_status(404, self.as_person().get(QUESTIONS, {"page": 999}),
                           "person · GET questions · page 999")

    def test_a_page_that_is_not_a_number_is_404(self):
        """GET /api/questions/?page=abc -> 404 (DRF's PageNumberPagination)."""
        self.assert_status(404, self.as_person().get(QUESTIONS, {"page": "abc"}),
                           "person · GET questions · page not a number")

    def test_the_api_root_is_200_with_a_token(self):
        """GET /api/ -> 200 listing the three collections (exams, questions and options)."""
        response = self.as_person().get("/api/")
        self.assert_status(200, response, "person · GET api root")
        self.assertEqual(sorted(response.json()), ["exams", "options", "questions"])


# --- creations -----------------------------------------------------------------------------------


class CreateMatrixTests(StatusMatrixTestCase):
    def test_a_valid_question_is_201(self):
        """POST /api/questions/ with a complete and valid body -> 201."""
        response = self.as_person().post(QUESTIONS, self.body(), format="json")
        self.assert_status(201, response, "person · POST questions · valid")

    def test_a_missing_text_is_400(self):
        """POST without the required field «text» -> 400."""
        payload = self.body()
        del payload["text"]
        response = self.as_person().post(QUESTIONS, payload, format="json")
        self.assert_status(400, response, "person · POST questions · missing text")
        self.assertIn("text", response.json())

    def test_a_missing_exam_is_400(self):
        """POST without the required field «exam» -> 400."""
        payload = self.body()
        del payload["exam"]
        response = self.as_person().post(QUESTIONS, payload, format="json")
        self.assert_status(400, response, "person · POST questions · missing exam")
        self.assertIn("exam", response.json())

    def test_a_missing_choices_field_is_400(self):
        """POST without the required field «choices» -> 400 (it is not optional)."""
        payload = self.body()
        del payload["choices"]
        response = self.as_person().post(QUESTIONS, payload, format="json")
        self.assert_status(400, response, "person · POST questions · missing choices")
        self.assertIn("choices", response.json())

    def test_a_blank_text_is_400(self):
        """POST with «text»: "" -> 400 (blank is not allowed)."""
        response = self.as_person().post(QUESTIONS, self.body(text=""), format="json")
        self.assert_status(400, response, "person · POST questions · blank text")

    def test_an_exam_that_is_not_a_number_is_400(self):
        """POST with «exam»: "no-es-un-numero" -> 400 (wrong type)."""
        response = self.as_person().post(QUESTIONS, self.body(exam="no-es-un-numero"), format="json")
        self.assert_status(400, response, "person · POST questions · exam wrong type")
        self.assertIn("exam", response.json())

    def test_a_null_exam_is_400(self):
        """POST with «exam»: null -> 400."""
        response = self.as_person().post(QUESTIONS, self.body(exam=None), format="json")
        self.assert_status(400, response, "person · POST questions · exam null")

    def test_an_exam_that_does_not_exist_is_400(self):
        """POST with «exam»: 99999 -> 400 naming the invalid primary key."""
        response = self.as_person().post(QUESTIONS, self.body(exam=UNKNOWN_ID), format="json")
        self.assert_status(400, response, "person · POST questions · exam unknown")
        self.assertIn("99999", str(response.json()))

    def test_choices_that_are_not_a_list_is_400(self):
        """POST with «choices»: "tres" -> 400 (wrong type)."""
        response = self.as_person().post(QUESTIONS, self.body(choices="tres"), format="json")
        self.assert_status(400, response, "person · POST questions · choices wrong type")

    def test_a_choice_without_text_is_400(self):
        """POST with an option that has no «text» -> 400 with the index of the option."""
        response = self.as_person().post(
            QUESTIONS,
            self.body(choices=[{"is_correct": True}, {"text": "Otra", "is_correct": False}]),
            format="json",
        )
        self.assert_status(400, response, "person · POST questions · choice without text")
        self.assertIn("0", response.json()["choices"])

    def test_an_is_correct_that_is_not_a_boolean_is_400(self):
        """POST with «is_correct»: "quiz" -> 400 (wrong type)."""
        response = self.as_person().post(
            QUESTIONS,
            self.body(choices=[{"text": "a", "is_correct": "quiz"}, {"text": "b", "is_correct": False}]),
            format="json",
        )
        self.assert_status(400, response, "person · POST questions · is_correct wrong type")

    def test_no_correct_option_is_400(self):
        """POST with zero correct options -> 400 with the reason of the domain."""
        response = self.as_person().post(
            QUESTIONS,
            self.body(choices=[{"text": "a", "is_correct": False}, {"text": "b", "is_correct": False}]),
            format="json",
        )
        self.assert_status(400, response, "person · POST questions · zero correct")
        self.assertIn("exactamente una", str(response.json()))

    def test_two_correct_options_are_400(self):
        """POST with two correct options -> 400 with the reason of the domain."""
        response = self.as_person().post(
            QUESTIONS,
            self.body(choices=[{"text": "a", "is_correct": True}, {"text": "b", "is_correct": True}]),
            format="json",
        )
        self.assert_status(400, response, "person · POST questions · two correct")
        self.assertIn("exactamente una", str(response.json()))

    def test_a_single_option_is_400(self):
        """POST with one option only -> 400: a question needs at least two."""
        response = self.as_person().post(
            QUESTIONS,
            self.body(choices=[{"text": "Única", "is_correct": True}]),
            format="json",
        )
        self.assert_status(400, response, "person · POST questions · one choice")
        self.assertIn("al menos dos", str(response.json()))

    def test_an_empty_list_of_options_is_400(self):
        """POST with «choices»: [] -> 400 for the same rule."""
        response = self.as_person().post(QUESTIONS, self.body(choices=[]), format="json")
        self.assert_status(400, response, "person · POST questions · no choices")
        self.assertIn("al menos dos", str(response.json()))

    def test_an_unknown_field_is_ignored(self):
        """POST with an extra field -> 201.

        Obtained behaviour of DRF's ModelSerializer, pinned so that a future change to
        ``extra_kwargs`` or to the serializers is noticed. It is NOT a requirement of the
        lab: the API simply does not reject unknown keys.
        """
        response = self.as_person().post(QUESTIONS, self.body(inesperado="x"), format="json")
        self.assert_status(201, response, "person · POST questions · unknown field")

    def test_the_agent_may_create(self):
        """POST with the agent's token -> 201."""
        self.assert_status(201, self.as_agent().post(QUESTIONS, self.body(), format="json"),
                           "agent · POST questions · valid")

    def test_a_reader_may_not_create(self):
        """POST with a token that is neither staff nor agent -> 403."""
        response = self.as_reader().post(QUESTIONS, self.body(), format="json")
        self.assert_status(403, response, "reader · POST questions · valid")

    def test_anonymous_may_not_create(self):
        """POST with no token -> 401 (never 403: there is no identity to judge)."""
        response = self.anonymous().post(QUESTIONS, self.body(), format="json")
        self.assert_status(401, response, "anonymous · POST questions · valid")


# --- updates ------------------------------------------------------------------------------------


class UpdateMatrixTests(StatusMatrixTestCase):
    def two_choices(self):
        return [{"text": "Primera", "is_correct": True}, {"text": "Segunda", "is_correct": False}]

    def test_a_complete_put_is_200(self):
        """PUT /api/questions/<id>/ with the whole body -> 200."""
        response = self.as_person().put(f"{QUESTIONS}{self.question.id}/", self.body(), format="json")
        self.assert_status(200, response, "person · PUT questions · complete")

    def test_a_put_without_text_is_400(self):
        """PUT without «text» -> 400: PUT is not a partial update."""
        payload = self.body()
        del payload["text"]
        response = self.as_person().put(f"{QUESTIONS}{self.question.id}/", payload, format="json")
        self.assert_status(400, response, "person · PUT questions · missing text")

    def test_a_put_without_choices_is_400(self):
        """PUT without «choices» -> 400: the options are part of the resource."""
        response = self.as_person().put(
            f"{QUESTIONS}{self.question.id}/", {"exam": self.exam, "text": "t"}, format="json"
        )
        self.assert_status(400, response, "person · PUT questions · missing choices")

    def test_a_put_that_breaks_a_rule_is_400(self):
        """PUT with two correct options -> 400, not a half applied write."""
        response = self.as_person().put(
            f"{QUESTIONS}{self.question.id}/",
            self.body(choices=[{"text": "a", "is_correct": True}, {"text": "b", "is_correct": True}]),
            format="json",
        )
        self.assert_status(400, response, "person · PUT questions · two correct")

    def test_putting_over_a_question_that_does_not_exist_is_404(self):
        """PUT /api/questions/<unknown>/ -> 404."""
        response = self.as_person().put(f"{QUESTIONS}{UNKNOWN_ID}/", self.body(), format="json")
        self.assert_status(404, response, "person · PUT questions · unknown id")

    def test_a_partial_update_is_200(self):
        """PATCH /api/questions/<id>/ with only «text» -> 200 and the options untouched."""
        response = self.as_person().patch(
            f"{QUESTIONS}{self.question.id}/", {"text": "Solo cambia el enunciado"}, format="json"
        )
        self.assert_status(200, response, "person · PATCH questions · text")
        self.assertEqual(len(response.json()["choices"]), 4)

    def test_a_patch_may_replace_the_options(self):
        """PATCH with «choices» -> 200 and the new options replace the previous ones."""
        response = self.as_person().patch(
            f"{QUESTIONS}{self.question.id}/", {"choices": self.two_choices()}, format="json"
        )
        self.assert_status(200, response, "person · PATCH questions · choices")
        self.assertEqual(len(response.json()["choices"]), 2)

    def test_a_patch_that_breaks_a_rule_is_400(self):
        """PATCH with one single option -> 400."""
        response = self.as_person().patch(
            f"{QUESTIONS}{self.question.id}/",
            {"choices": [{"text": "Única", "is_correct": True}]},
            format="json",
        )
        self.assert_status(400, response, "person · PATCH questions · one choice")

    def test_a_patch_to_an_unknown_exam_is_400(self):
        """PATCH with «exam»: 99999 -> 400."""
        response = self.as_person().patch(
            f"{QUESTIONS}{self.question.id}/", {"exam": UNKNOWN_ID}, format="json"
        )
        self.assert_status(400, response, "person · PATCH questions · exam unknown")

    def test_patching_a_question_that_does_not_exist_is_404(self):
        """PATCH /api/questions/<unknown>/ -> 404."""
        response = self.as_person().patch(f"{QUESTIONS}{UNKNOWN_ID}/", {"text": "x"}, format="json")
        self.assert_status(404, response, "person · PATCH questions · unknown id")

    def test_the_agent_may_update_a_question(self):
        """PATCH with the agent's token -> 200."""
        response = self.as_agent().patch(f"{QUESTIONS}{self.question.id}/", {"text": "Del agente"}, format="json")
        self.assert_status(200, response, "agent · PATCH questions · text")

    def test_the_agent_may_update_an_exam(self):
        """PUT /api/exams/<id>/ with the agent's token -> 200."""
        response = self.as_agent().put(f"{EXAMS}{self.exam}/", {"title": "Renombrado por el agente"}, format="json")
        self.assert_status(200, response, "agent · PUT exams · title")

    def test_a_reader_may_not_update(self):
        """PATCH with a reader's token -> 403."""
        response = self.as_reader().patch(f"{QUESTIONS}{self.question.id}/", {"text": "x"}, format="json")
        self.assert_status(403, response, "reader · PATCH questions · text")

    def test_anonymous_may_not_update(self):
        """PATCH with no token -> 401."""
        response = self.anonymous().patch(f"{QUESTIONS}{self.question.id}/", {"text": "x"}, format="json")
        self.assert_status(401, response, "anonymous · PATCH questions · text")


# --- deletions -----------------------------------------------------------------------------------


class DeleteMatrixTests(StatusMatrixTestCase):
    def test_a_person_deletes_a_question_with_204(self):
        """DELETE /api/questions/<id>/ -> 204 and no body."""
        response = self.as_person().delete(f"{QUESTIONS}{self.question.id}/")
        self.assert_status(204, response, "person · DELETE questions · existing")
        self.assertEqual(response.content, b"")

    def test_a_deleted_question_is_then_a_404(self):
        """GET of a deleted question -> 404."""
        self.as_person().delete(f"{QUESTIONS}{self.question.id}/")
        self.assert_status(404, self.as_person().get(f"{QUESTIONS}{self.question.id}/"),
                           "person · GET questions · after delete")

    def test_deleting_a_question_twice_is_404(self):
        """DELETE of an already deleted question -> 404, not 204 and not 500."""
        self.as_person().delete(f"{QUESTIONS}{self.question.id}/")
        self.assert_status(404, self.as_person().delete(f"{QUESTIONS}{self.question.id}/"),
                           "person · DELETE questions · twice")

    def test_deleting_a_question_that_does_not_exist_is_404(self):
        """DELETE /api/questions/<unknown>/ -> 404."""
        self.assert_status(404, self.as_person().delete(f"{QUESTIONS}{UNKNOWN_ID}/"),
                           "person · DELETE questions · unknown id")

    def test_a_person_deletes_an_exam_with_204(self):
        """DELETE /api/exams/<id>/ -> 204."""
        self.assert_status(204, self.as_person().delete(f"{EXAMS}{self.exam}/"),
                           "person · DELETE exams · existing")

    def test_deleting_an_exam_that_does_not_exist_is_404(self):
        """DELETE /api/exams/<unknown>/ -> 404."""
        self.assert_status(404, self.as_person().delete(f"{EXAMS}{UNKNOWN_ID}/"),
                           "person · DELETE exams · unknown id")

    def test_the_agent_may_not_delete_a_question(self):
        """DELETE with the agent's token -> 403 and the question survives."""
        response = self.as_agent().delete(f"{QUESTIONS}{self.question.id}/")
        self.assert_status(403, response, "agent · DELETE questions · existing")
        self.assertTrue(Question.objects.filter(id=self.question.id).exists())

    def test_the_agent_may_not_delete_an_exam(self):
        """DELETE /api/exams/<id>/ with the agent's token -> 403."""
        self.assert_status(403, self.as_agent().delete(f"{EXAMS}{self.exam}/"), "agent · DELETE exams · existing")

    def test_the_agent_gets_403_even_if_the_question_does_not_exist(self):
        """The rule is answered before the object is looked up: DELETE unknown -> 403, not 404.

        This is the order DRF works in (permissions first). It matters: a 403 never leaks
        whether an id exists.
        """
        self.assert_status(403, self.as_agent().delete(f"{QUESTIONS}{UNKNOWN_ID}/"),
                           "agent · DELETE questions · unknown id")

    def test_a_reader_may_not_delete(self):
        """DELETE with a reader's token -> 403."""
        self.assert_status(403, self.as_reader().delete(f"{QUESTIONS}{self.question.id}/"),
                           "reader · DELETE questions · existing")

    def test_anonymous_may_not_delete(self):
        """DELETE with no token -> 401."""
        self.assert_status(401, self.anonymous().delete(f"{QUESTIONS}{self.question.id}/"),
                           "anonymous · DELETE questions · existing")


# --- roles, verbs and the contract ---------------------------------------------------------------


class VerbAndRoleMatrixTests(StatusMatrixTestCase):
    def test_anonymous_may_not_read(self):
        """GET /api/questions/ with no token -> 401."""
        self.assert_status(401, self.anonymous().get(QUESTIONS), "anonymous · GET questions · list")

    def test_anonymous_may_not_read_the_exams(self):
        """GET /api/exams/ with no token -> 401."""
        self.assert_status(401, self.anonymous().get(EXAMS), "anonymous · GET exams · list")

    def test_anonymous_may_not_read_one_question(self):
        """GET /api/questions/<id>/ with no token -> 401."""
        self.assert_status(401, self.anonymous().get(f"{QUESTIONS}{self.question.id}/"),
                           "anonymous · GET questions · detail")

    def test_anonymous_may_not_read_the_api_root(self):
        """GET /api/ with no token -> 401."""
        self.assert_status(401, self.anonymous().get("/api/"), "anonymous · GET api root")

    def test_a_wrong_token_is_401(self):
        """GET with an unknown token -> 401."""
        response = self.as_("nonsense").get(QUESTIONS)
        self.assert_status(401, response, "wrong token · GET questions · list")

    def test_an_empty_token_is_401(self):
        """GET with «Token » and nothing else -> 401."""
        response = self.as_("").get(QUESTIONS)
        self.assert_status(401, response, "empty token · GET questions · list")

    def test_a_token_in_the_wrong_scheme_is_401(self):
        """GET with «Bearer <key>» -> 401: the API only speaks «Token»."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.person}")
        self.assert_status(401, self.client.get(QUESTIONS), "bearer scheme · GET questions · list")

    def test_the_agent_may_read(self):
        """GET with the agent's token -> 200."""
        self.assert_status(200, self.as_agent().get(QUESTIONS), "agent · GET questions · list")

    def test_the_agent_may_read_the_exams(self):
        """GET /api/exams/ with the agent's token -> 200."""
        self.assert_status(200, self.as_agent().get(EXAMS), "agent · GET exams · list")

    def test_a_reader_may_read(self):
        """GET with a reader's token -> 200."""
        self.assert_status(200, self.as_reader().get(QUESTIONS), "reader · GET questions · list")

    def test_a_person_may_create_an_exam(self):
        """POST /api/exams/ with a person's token -> 201."""
        response = self.as_person().post(EXAMS, {"title": "Examen nuevo"}, format="json")
        self.assert_status(201, response, "person · POST exams · valid")

    def test_an_empty_exam_title_is_400(self):
        """POST /api/exams/ with «title»: "" -> 400."""
        response = self.as_person().post(EXAMS, {"title": ""}, format="json")
        self.assert_status(400, response, "person · POST exams · blank title")

    def test_a_missing_exam_title_is_400(self):
        """POST /api/exams/ without «title» -> 400."""
        response = self.as_person().post(EXAMS, {}, format="json")
        self.assert_status(400, response, "person · POST exams · missing title")

    def test_a_verb_without_a_handler_is_405(self):
        """POST /api/exams/<id>/ -> 405: there is no create on a detail route."""
        response = self.as_person().post(f"{EXAMS}{self.exam}/", {"title": "x"}, format="json")
        self.assert_status(405, response, "person · POST exams · detail")
        self.assertEqual(
            set(response["Allow"].replace(" ", "").split(",")),
            {"GET", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"},
            "the Allow header of a 405 lists the verbs the route DOES accept",
        )

    def test_the_permission_is_asked_before_the_handler(self):
        """POST /api/exams/<id>/ with a reader's token -> 403, not 405.

        The order matters: DRF authenticates and authorises before it looks for the handler,
        so a reader never learns which verbs a route implements.
        """
        self.assert_status(403, self.as_reader().post(f"{EXAMS}{self.exam}/", {}, format="json"),
                           "reader · POST exams · detail")

    def test_options_tells_what_the_collection_accepts(self):
        """OPTIONS /api/questions/ -> 200 with the allowed verbs."""
        response = self.as_person().options(QUESTIONS)
        self.assert_status(200, response, "person · OPTIONS questions · list")
        self.assertEqual(set(response["Allow"].replace(" ", "").split(",")), {"GET", "POST", "HEAD", "OPTIONS"})

    def test_head_does_not_bring_a_body(self):
        """HEAD /api/questions/ -> 200 with no content."""
        response = self.as_person().head(QUESTIONS)
        self.assert_status(200, response, "person · HEAD questions · list")
        self.assertEqual(response.content, b"")

    def test_anonymous_may_not_ask_for_the_options(self):
        """OPTIONS with no token -> 401: OPTIONS is a read and needs an identity too."""
        self.assert_status(401, self.anonymous().options(QUESTIONS), "anonymous · OPTIONS questions · list")

    def test_the_openapi_contract_is_public(self):
        """GET /api/schema/ without a token -> 200 (the contract must be readable)."""
        response = self.anonymous().get("/api/schema/")
        self.assert_status(200, response, "anonymous · GET schema")
        self.assertIn("openapi", response.content.decode())

    def test_the_contract_answers_yaml_too(self):
        """GET /api/schema/?format=yaml -> 200 in YAML."""
        response = self.anonymous().get("/api/schema/", {"format": "yaml"})
        self.assert_status(200, response, "anonymous · GET schema · yaml")
        self.assertTrue(response.content.decode().startswith("openapi:"))

    def test_the_contract_refuses_a_format_it_cannot_render(self):
        """GET /api/schema/ with «Accept: text/html» -> 406: it only renders YAML/JSON."""
        self.assert_status(406, self.anonymous().get("/api/schema/", HTTP_ACCEPT="text/html"),
                           "anonymous · GET schema · accept html")

    def test_the_browsable_documentation_is_public(self):
        """GET /api/docs/ without a token -> 200 (Swagger UI)."""
        response = self.anonymous().get("/api/docs/")
        self.assert_status(200, response, "anonymous · GET docs")
        self.assertIn("text/html", response["Content-Type"])


# --- the browsable API of DRF --------------------------------------------------------------------


class BrowsableApiTests(StatusMatrixTestCase):
    """DRF answers HTML when the browser asks for it: the same routes, same rules."""

    def html(self, path, token=None, params=None):
        if token:
            self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        else:
            self.anonymous()
        return self.client.get(path, params, HTTP_ACCEPT="text/html")

    def assert_html(self, expected, response, cell):
        self.assertEqual(
            expected,
            response.status_code,
            f"[{cell}] se esperaba {expected} y se obtuvo {response.status_code}",
        )
        self.assertTrue(
            response["Content-Type"].startswith("text/html"),
            f"[{cell}] la respuesta navegable debe ser HTML, vino {response['Content-Type']}",
        )

    def test_the_question_list_is_html_with_the_data_in_it(self):
        """GET /api/questions/ with «Accept: text/html» -> 200 and HTML with the questions."""
        response = self.html(QUESTIONS, self.person)
        self.assert_html(200, response, "person · GET questions · list · html")
        body = response.content.decode()
        self.assertIn("Un QuerySet con los artículos publicados", body)
        self.assertNotIn('{"count"', body)  # not the JSON renderer

    def test_one_question_is_html_with_its_options(self):
        """GET /api/questions/<id>/ as HTML -> 200 with the options inside."""
        response = self.html(f"{QUESTIONS}{self.question.id}/", self.person)
        self.assert_html(200, response, "person · GET questions · detail · html")
        self.assertIn(self.question.text[:40], response.content.decode())

    def test_the_exam_list_is_html(self):
        """GET /api/exams/ as HTML -> 200 with the exam titles."""
        response = self.html(EXAMS, self.person)
        self.assert_html(200, response, "person · GET exams · list · html")
        self.assertIn("Django · ORM", response.content.decode())

    def test_one_exam_is_html(self):
        """GET /api/exams/<id>/ as HTML -> 200."""
        response = self.html(f"{EXAMS}{self.exam}/", self.person)
        self.assert_html(200, response, "person · GET exams · detail · html")

    def test_the_navigable_api_asks_for_a_token_it_cannot_get_from_a_session(self):
        """GET as HTML with no token -> 401: there is no login form that a session could feed.

        TokenAuthentication has no login view, so the browsable API cannot authenticate a
        browser session. Worth pinning: a session does not turn into a token by accident.
        """
        self.assert_html(401, self.html(QUESTIONS), "anonymous · GET questions · list · html")

    def test_the_navigable_api_answers_json_when_json_is_asked_for(self):
        """The same route with «Accept: application/json» -> JSON, not HTML."""
        self.as_person()
        response = self.client.get(QUESTIONS, HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["Content-Type"].startswith("application/json"))


# --- the frontier between the two identities ------------------------------------------------------


class SessionTokenFrontierTests(StatusMatrixTestCase):
    """A browser session and an API token are two different doors. Neither opens the other."""

    def setUp(self):
        super().setUp()
        self.session_client = Client()
        self.session_client.force_login(User.objects.get(username="profe"))

    def test_a_valid_ui_session_does_not_open_the_api(self):
        """GET /api/questions/ with a perfect session and no token -> 401."""
        response = self.session_client.get(QUESTIONS)
        self.assertEqual(response.status_code, 401, "una sesión de la UI no vale para la API")

    def test_a_valid_ui_session_does_not_open_the_api_for_writing(self):
        """POST /api/questions/ with a session and no token -> 401 and nothing is written."""
        response = self.session_client.post(
            QUESTIONS, {"exam": self.exam, "text": "desde la sesión", "choices": [
                {"text": "a", "is_correct": True}, {"text": "b", "is_correct": False}]},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)
        self.assertFalse(Question.objects.filter(text="desde la sesión").exists())

    def test_a_valid_ui_session_does_not_delete_through_the_api(self):
        """DELETE /api/questions/<id>/ with a session and no token -> 401 and it survives."""
        response = self.session_client.delete(f"{QUESTIONS}{self.question.id}/")
        self.assertEqual(response.status_code, 401)
        self.assertTrue(Question.objects.filter(id=self.question.id).exists())

    def test_a_valid_ui_session_does_not_open_the_navigable_api(self):
        """The browsable API is also behind the token: a session gets 401, not HTML data."""
        response = self.session_client.get(QUESTIONS, HTTP_ACCEPT="text/html")
        self.assertEqual(response.status_code, 401)
        self.assertNotIn("Un QuerySet con los artículos publicados", response.content.decode())

    def test_an_api_token_does_not_open_the_interface(self):
        """GET / (the dashboard) with only a token -> 302 to the login page."""
        response = self.anonymous().get("/", headers={"authorization": f"Token {self.person}"})
        self.assertEqual(response.status_code, 302)
        self.assertIn("/acceso/", response["Location"])

    def test_an_api_token_does_not_write_through_the_interface(self):
        """POST /examenes/nuevo/ with only a token -> 302 and no exam is created."""
        response = self.anonymous().post(
            "/examenes/nuevo/", {"title": "creada con un token"},
            headers={"authorization": f"Token {self.person}"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Exam.objects.filter(title="creada con un token").exists())

    def test_the_token_wins_on_the_api_even_inside_a_browser(self):
        """Session AND a valid token: the token authenticates the API (DRF ignores the session)."""
        response = self.session_client.get(
            QUESTIONS, headers={"authorization": f"Token {self.person}"}
        )
        self.assertEqual(response.status_code, 200)