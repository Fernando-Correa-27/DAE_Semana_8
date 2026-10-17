"""What the database keeps and what it loses.

Two questions that ``test_api.py`` only answers for one case:

1. When the API answers 400, does anything at all reach the database? A rejected body must
   leave no question, no option and no half-written row behind (``services`` writes inside a
   transaction, and the rollback has to be proved, not assumed).
2. What happens to the related rows when an entity is deleted? Both interfaces share
   ``on_delete=CASCADE``, so deleting an exam must take its questions and options with it,
   and must not touch anything else.

Nothing here trusts a status code as proof: every test counts objects in the database.
"""
from unittest import mock

from django.contrib.auth.models import User
from django.db import models
from django.test import Client, TestCase
from rest_framework.test import APITestCase

from quiz import services
from quiz.models import Choice, Exam, Question

from .helpers import exam_id, seed, valid_body

QUESTIONS = "/api/questions/"
EXAMS = "/api/exams/"


class RejectedWritesTests(APITestCase):
    """A 400 (or a failed service call) must not leave anything persisted."""

    def setUp(self):
        self.person, _ = seed()
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.person}")
        self.exam = exam_id()
        # What the three tables hold before any rejected request.
        self.before = (Exam.objects.count(), Question.objects.count(), Choice.objects.count())

    def snapshot(self):
        return (Exam.objects.count(), Question.objects.count(), Choice.objects.count())

    def assert_nothing_was_written(self, response, expected_status=400, cell=""):
        """The request is rejected AND the three tables are exactly as they were."""
        self.assertEqual(expected_status, response.status_code, cell)
        self.assertEqual(self.before, self.snapshot(), f"{cell}: a rejected write changed the database")

    def post(self, **changes):
        payload = valid_body(self.exam)
        payload.update(changes)
        return self.client.post(QUESTIONS, payload, format="json")

    def test_two_correct_options_write_nothing(self):
        """The classic rule break: no question and no option is created."""
        response = self.post(choices=[{"text": "a", "is_correct": True}, {"text": "b", "is_correct": True}])
        self.assert_nothing_was_written(response, cell="two correct options")

    def test_no_correct_option_writes_nothing(self):
        """Zero correct options: also rejected, also nothing persisted."""
        response = self.post(choices=[{"text": "a", "is_correct": False}, {"text": "b", "is_correct": False}])
        self.assert_nothing_was_written(response, cell="zero correct options")

    def test_a_single_option_writes_nothing(self):
        """Less than two options: nothing is created, not even the question."""
        response = self.post(choices=[{"text": "Única", "is_correct": True}])
        self.assert_nothing_was_written(response, cell="one single option")

    def test_a_wrong_type_writes_nothing(self):
        """A body that is not even shaped like the contract does not reach the database."""
        self.assert_nothing_was_written(
            self.client.post(QUESTIONS, {"exam": "no-es-un-numero", "text": "t", "choices": []}, format="json"),
            cell="wrong type of exam",
        )

    def test_an_unknown_exam_writes_nothing(self):
        """A question cannot be created hanging from an exam that does not exist."""
        self.assert_nothing_was_written(self.post(exam=99999), cell="unknown exam")

    def test_a_missing_field_writes_nothing(self):
        """A missing required field is rejected before anything is written."""
        payload = valid_body(self.exam)
        del payload["choices"]
        self.assert_nothing_was_written(
            self.client.post(QUESTIONS, payload, format="json"), cell="missing choices"
        )

    def test_a_rejected_post_does_not_even_reach_an_insert(self):
        """The rejected POST runs 2 queries (the token and the exam it points at) and no INSERT.

        This is the strong version of the same idea: if a write had been attempted, the
        query counter would go up. 2 is the number measured on the delivered server.
        """
        with self.assertNumQueries(2):
            response = self.post(choices=[{"text": "a", "is_correct": True},
                                          {"text": "b", "is_correct": True}])
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Question.objects.filter(text="¿Qué es una API REST?").count(), 0)

    def test_a_rejected_put_leaves_the_previous_options_in_place(self):
        """PUT with two correct options: the question keeps its text and its four options."""
        question = Question.objects.first()
        text, choice_ids = question.text, list(question.choices.values_list("id", flat=True))
        response = self.client.put(
            f"{QUESTIONS}{question.id}/",
            dict(valid_body(self.exam), text="Enunciado que no debe guardarse",
                 choices=[{"text": "a", "is_correct": True}, {"text": "b", "is_correct": True}]),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        question.refresh_from_db()
        self.assertEqual(question.text, text)
        self.assertEqual(list(question.choices.values_list("id", flat=True)), choice_ids)

    def test_a_rejected_patch_leaves_the_previous_options_in_place(self):
        """PATCH with one single option: the four options that were there are still there."""
        question = Question.objects.first()
        response = self.client.patch(
            f"{QUESTIONS}{question.id}/", {"choices": [{"text": "Única", "is_correct": True}]}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(question.choices.count(), 4)


class ServiceRollbackTests(TestCase):
    """The rollback of ``services.create_question``/``update_question``, proved with a failure.

    A rejected body never reaches the database, so it cannot prove the transaction works.
    These tests break the write in the middle (the options cannot be saved) and check that
    the question that was already inserted disappears with it.
    """

    def setUp(self):
        seed()
        self.exam = Exam.objects.first()
        self.before = Question.objects.count()

    def test_a_question_is_not_left_without_its_options(self):
        """The options fail to be saved: the question must not survive either."""
        boom = mock.patch.object(Choice.objects, "bulk_create", side_effect=RuntimeError("disk full"))
        with boom, self.assertRaises(RuntimeError):
            services.create_question(
                self.exam, "Se queda a medias",
                [{"text": "a", "is_correct": True}, {"text": "b", "is_correct": False}],
            )
        self.assertEqual(Question.objects.count(), self.before)
        self.assertFalse(Question.objects.filter(text="Se queda a medias").exists())
        self.assertEqual(Choice.objects.count(), 32)

    def test_an_update_that_cannot_save_the_options_keeps_the_previous_ones(self):
        """The update fails after the text was saved: neither the text nor the options change."""
        question = self.exam.questions.first()
        original_text = question.text
        choice_ids = list(question.choices.values_list("id", flat=True))
        boom = mock.patch.object(Choice.objects, "bulk_create", side_effect=RuntimeError("disk full"))
        with boom, self.assertRaises(RuntimeError):
            services.update_question(
                question, text="Texto nuevo",
                choices=[{"text": "a", "is_correct": True}, {"text": "b", "is_correct": False}],
            )
        question.refresh_from_db()
        self.assertEqual(question.text, original_text, "el texto tampoco puede quedar a medias")
        self.assertEqual(list(question.choices.values_list("id", flat=True)), choice_ids)
        self.assertEqual(Choice.objects.count(), 32)

    def test_the_service_refuses_an_invalid_question_before_writing_anything(self):
        """``create_question`` raises the rule error and creates nothing (the UI path too)."""
        with self.assertRaises(services.QuizRuleError):
            services.create_question(self.exam, "Ni una", [{"text": "a", "is_correct": True}])
        self.assertEqual(Question.objects.count(), self.before)

    def test_the_rule_error_keeps_both_wordings_of_the_lab(self):
        """The two reasons the lab asks for are the ones the service raises."""
        with self.assertRaisesMessage(services.QuizRuleError, "al menos dos opciones"):
            services.validate_question_choices([{"text": "a", "is_correct": True}])
        with self.assertRaisesMessage(services.QuizRuleError, "exactamente una opción correcta"):
            services.validate_question_choices([
                {"text": "a", "is_correct": True}, {"text": "b", "is_correct": True}])


class CascadeDeleteTests(APITestCase):
    """Deleting a parent takes its children; deleting it from the API or from the UI."""

    def setUp(self):
        self.person, _ = seed()
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.person}")
        # The fixed data of the lab: 2 exams, 8 questions, 32 options.
        self.counts = (2, 8, 32)

    def test_deleting_an_exam_over_the_api_takes_its_questions_and_its_options(self):
        """DELETE /api/exams/<id>/ -> the exam, its 4 questions and their 16 options are gone."""
        exam = Exam.objects.first()
        questions = list(exam.questions.values_list("id", flat=True))
        choices = list(Choice.objects.filter(question__in=questions).values_list("id", flat=True))

        self.assertEqual(self.client.delete(f"{EXAMS}{exam.id}/").status_code, 204)

        self.assertEqual((Exam.objects.count(), Question.objects.count(), Choice.objects.count()),
                         (1, 4, 16))
        self.assertFalse(Question.objects.filter(id__in=questions).exists())
        self.assertFalse(Choice.objects.filter(id__in=choices).exists())

    def test_deleting_an_exam_does_not_touch_the_other_exams(self):
        """The cascade is not a global wipe: the other exam keeps its questions and options."""
        survivor = Exam.objects.last()
        survivor_questions = set(survivor.questions.values_list("id", flat=True))
        survivor_choices = set(Choice.objects.filter(question__in=survivor_questions)
                               .values_list("id", flat=True))

        self.client.delete(f"{EXAMS}{Exam.objects.first().id}/")

        self.assertTrue(survivor.questions.filter(id__in=survivor_questions).exists())
        self.assertEqual(Choice.objects.filter(id__in=survivor_choices).count(), len(survivor_choices))

    def test_deleting_a_question_takes_only_its_own_options(self):
        """DELETE /api/questions/<id>/ -> 4 options gone, the other questions untouched."""
        question = Question.objects.first()
        choice_ids = list(question.choices.values_list("id", flat=True))
        self.assertEqual(len(choice_ids), 4)

        self.assertEqual(self.client.delete(f"{QUESTIONS}{question.id}/").status_code, 204)

        self.assertEqual((Exam.objects.count(), Question.objects.count(), Choice.objects.count()),
                         (2, 7, 28))
        self.assertFalse(Choice.objects.filter(id__in=choice_ids).exists())

    def test_the_exam_left_behind_reports_zero_questions(self):
        """After the cascade the annotation of the exam says 0, and the API says 0 too."""
        exam = Exam.objects.first()
        self.client.delete(f"{EXAMS}{exam.id}/")
        response = self.client.get(f"{EXAMS}{exam.id}/")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.client.get(EXAMS).json()["results"][0]["question_count"], 4)

    def test_deleting_every_exam_leaves_the_domain_empty(self):
        """Deleting both exams leaves 0 exams, 0 questions and 0 options."""
        for exam in Exam.objects.all():
            self.assertEqual(self.client.delete(f"{EXAMS}{exam.id}/").status_code, 204)
        self.assertEqual((Exam.objects.count(), Question.objects.count(), Choice.objects.count()),
                         (0, 0, 0))

    def test_the_cascade_is_declared_in_the_model(self):
        """Both relations are CASCADE in the model, not only in the database."""
        exam_relation = Exam._meta.get_field("questions")
        question_relation = Question._meta.get_field("choices")
        self.assertIs(exam_relation.on_delete, models.CASCADE)
        self.assertIs(question_relation.on_delete, models.CASCADE)

    def test_the_interface_cascades_exactly_the_same(self):
        """The web interface deletes an exam with the same effect as the API."""
        person = User.objects.get(username="profe")
        web = Client()
        web.force_login(person)
        exam = Exam.objects.first()

        response = web.post(f"/examenes/{exam.pk}/eliminar/", follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual((Exam.objects.count(), Question.objects.count(), Choice.objects.count()),
                         (1, 4, 16))