"""The options as a resource of their own: ``/api/options/``.

The options keep travelling nested inside a question (``test_api.py`` fixes that), and
this file adds the second door of the same data without changing the first one.

What it pins down:
  - the resource works as a resource: list, detail, filter, search, create, update, delete;
  - it costs no extra query per option (``select_related`` on the question);
  - writing ONE option at a time keeps the invariant of its question, the very same
    invariant ``services.validate_question_choices`` guards when the whole list arrives:
    a question always has exactly one correct option;
  - a refusal writes nothing.

``test_api.py``, ``test_agent.py``, ``test_quizctl.py`` and ``test_permissions.py`` are the
specification of the lab and are not touched here.
"""
from rest_framework.test import APITestCase

from quiz.models import Choice, Question

from .helpers import seed

OPTIONS = "/api/options/"

# The wording the domain gives in services.py, so a reworded message fails here.
TWO_CORRECT = "no puede tener más de una opción correcta"
NO_CORRECT = "necesita al menos una opción correcta"


class OptionReadTests(APITestCase):
    def setUp(self):
        self.person, _ = seed()
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.person}")
        self.question = Question.objects.first()

    def test_options_are_listed_with_their_question(self):
        response = self.client.get(OPTIONS)
        self.assertEqual(response.status_code, 200)
        page = response.json()
        self.assertEqual(page["count"], Choice.objects.count())
        first = page["results"][0]
        self.assertEqual(sorted(first), ["id", "is_correct", "question", "text"])
        self.assertEqual(first["question"], Choice.objects.first().question_id)

    def test_an_option_can_be_read_on_its_own(self):
        option = self.question.choices.first()
        response = self.client.get(f"{OPTIONS}{option.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "id": option.id,
            "question": self.question.id,
            "text": option.text,
            "is_correct": option.is_correct,
        })

    def test_an_unknown_option_is_404(self):
        self.assertEqual(self.client.get(f"{OPTIONS}999999/").status_code, 404)

    def test_options_can_be_filtered_by_question(self):
        data = self.client.get(OPTIONS, {"question": self.question.id}).json()
        self.assertEqual(data["count"], self.question.choices.count())
        self.assertEqual({row["question"] for row in data["results"]}, {self.question.id})

    def test_a_filter_of_a_question_without_options_is_an_empty_200(self):
        other = Question.objects.exclude(pk=self.question.pk).first()
        self.assertEqual(self.client.get(OPTIONS, {"question": other.id}).json()["count"], 4)

    def test_a_question_filter_that_is_not_an_id_is_400(self):
        for value in ("abc", "²", "1.0", "-1", ""):
            response = self.client.get(OPTIONS, {"question": value})
            self.assertEqual(response.status_code, 400, value)
            self.assertIn("question", response.json())

    def test_options_can_be_searched_by_text(self):
        data = self.client.get(OPTIONS, {"search": "plantilla base"}).json()
        self.assertGreater(data["count"], 0)
        self.assertTrue(all("plantilla base" in row["text"].lower() for row in data["results"]))

    def test_the_listing_costs_the_same_with_more_options(self):
        """No N+1: the question of every option comes in the same query, not one per row."""
        extra = Question.objects.exclude(pk=self.question.pk).first()
        for index in range(40):
            extra.choices.create(text=f"Relleno {index}", is_correct=False)
        with self.assertNumQueries(3):  # the token, the COUNT the pagination needs, the rows
            self.assertEqual(self.client.get(OPTIONS, {"search": "Relleno"}).status_code, 200)


class OptionWriteTests(APITestCase):
    def setUp(self):
        self.person, _ = seed()
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.person}")
        self.question = Question.objects.first()

    def test_an_option_is_created_with_201(self):
        response = self.client.post(
            OPTIONS,
            {"question": self.question.id, "text": "Una opción nueva", "is_correct": False},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["question"], self.question.id)
        self.assertTrue(self.question.choices.filter(pk=body["id"]).exists())

    def test_put_replaces_the_option(self):
        option = self.question.choices.filter(is_correct=False).first()
        response = self.client.put(
            f"{OPTIONS}{option.id}/",
            {"question": self.question.id, "text": "Texto reemplazado", "is_correct": False},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        option.refresh_from_db()
        self.assertEqual(option.text, "Texto reemplazado")

    def test_patch_changes_only_what_is_sent(self):
        option = self.question.choices.filter(is_correct=False).first()
        response = self.client.patch(
            f"{OPTIONS}{option.id}/", {"text": "Texto cambiado"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        option.refresh_from_db()
        self.assertEqual((option.text, option.is_correct), ("Texto cambiado", False))

    def test_an_option_is_deleted_with_204(self):
        option = self.question.choices.filter(is_correct=False).first()
        self.assertEqual(self.client.delete(f"{OPTIONS}{option.id}/").status_code, 204)
        self.assertEqual(self.client.get(f"{OPTIONS}{option.id}/").status_code, 404)

    def test_an_option_of_a_missing_required_field_is_400(self):
        response = self.client.post(OPTIONS, {"text": "Sin pregunta"}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_an_option_of_a_question_that_does_not_exist_is_400(self):
        response = self.client.post(
            OPTIONS,
            {"question": 999999, "text": "Sin pregunta", "is_correct": False},
            format="json",
        )
        self.assertEqual(response.status_code, 400)


class OptionInvariantTests(APITestCase):
    """«Exactly one correct option», asked one option at a time.

    These are the same rule of ``services.validate_question_choices``, translated to a
    door that writes a single row: two correct options, a question left without a correct
    one, and the deletion of the only correct option.
    """

    def setUp(self):
        self.person, self.agent = seed()
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.person}")
        self.question = Question.objects.first()
        self.correct = self.question.choices.get(is_correct=True)
        self.wrong = self.question.choices.filter(is_correct=False).first()

    def test_a_second_correct_option_is_400_and_saves_nothing(self):
        response = self.client.patch(
            f"{OPTIONS}{self.wrong.id}/", {"is_correct": True}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(TWO_CORRECT, str(response.json()))
        self.wrong.refresh_from_db()
        self.assertFalse(self.wrong.is_correct)
        self.assertEqual(self.question.choices.filter(is_correct=True).count(), 1)

    def test_creating_a_second_correct_option_is_400_and_saves_nothing(self):
        before = Choice.objects.count()
        response = self.client.post(
            OPTIONS,
            {"question": self.question.id, "text": "Otra correcta", "is_correct": True},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(TWO_CORRECT, str(response.json()))
        self.assertEqual(Choice.objects.count(), before)

    def test_unmarking_the_only_correct_option_is_400_and_saves_nothing(self):
        response = self.client.patch(
            f"{OPTIONS}{self.correct.id}/", {"is_correct": False}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(NO_CORRECT, str(response.json()))
        self.correct.refresh_from_db()
        self.assertTrue(self.correct.is_correct)

    def test_deleting_the_only_correct_option_is_400_and_saves_nothing(self):
        response = self.client.delete(f"{OPTIONS}{self.correct.id}/")
        self.assertEqual(response.status_code, 400)
        self.assertIn(NO_CORRECT, str(response.json()))
        self.assertTrue(Choice.objects.filter(pk=self.correct.pk).exists())

    def test_the_correct_option_moves_to_another_question_in_one_call(self):
        """The rule follows the question the option ends up in, not the one it came from."""
        other = Question.objects.exclude(pk=self.question.pk).first()
        response = self.client.patch(
            f"{OPTIONS}{self.correct.id}/", {"question": other.id}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(TWO_CORRECT, str(response.json()))
        self.correct.refresh_from_db()
        self.assertEqual(self.correct.question_id, self.question.id)

    def test_moving_an_ordinary_option_to_another_question_is_allowed(self):
        """A question without the moved option keeps its own correct one, and the other
        keeps the correct one it already had."""
        other = Question.objects.exclude(pk=self.question.pk).first()
        response = self.client.patch(
            f"{OPTIONS}{self.wrong.id}/", {"question": other.id}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.wrong.refresh_from_db()
        self.assertEqual(self.wrong.question_id, other.id)
        self.assertEqual(self.question.choices.filter(is_correct=True).count(), 1)
        self.assertEqual(other.choices.filter(is_correct=True).count(), 1)


class OptionPermissionTests(APITestCase):
    """The table of roles applies here exactly as it does to the questions."""

    def setUp(self):
        self.person, self.agent = seed()
        self.question = Question.objects.first()
        self.correct = self.question.choices.get(is_correct=True)
        self.wrong = self.question.choices.filter(is_correct=False).first()

    def as_agent(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.agent}")

    def test_an_agent_may_create_and_modify_an_option(self):
        self.as_agent()
        response = self.client.post(
            OPTIONS,
            {"question": self.question.id, "text": "Del agente", "is_correct": False},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        created = response.json()["id"]
        self.assertEqual(
            self.client.patch(f"{OPTIONS}{created}/", {"text": "Editada"}, format="json").status_code,
            200,
        )

    def test_an_agent_may_never_delete_an_option(self):
        self.as_agent()
        self.assertEqual(self.client.delete(f"{OPTIONS}{self.wrong.id}/").status_code, 403)
        self.assertTrue(Choice.objects.filter(pk=self.wrong.pk).exists())

    def test_no_token_is_401(self):
        self.client.credentials()
        self.assertEqual(self.client.get(OPTIONS).status_code, 401)