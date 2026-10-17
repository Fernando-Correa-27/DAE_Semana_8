"""The findings of the code review that touch the browser, one test each.

Every test names the finding it closes (B1, I1, I2, I4, I7, I8 of
``docs/revision-codigo.md``). They live apart from ``test_web.py`` so the
specification tests of the lab are not touched.
"""
import re

from django.conf import settings
from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from quiz.models import Exam, Question

from . import helpers

RADIO = r'<input type="radio"[^>]*value="(\d+)"[^>]*checked'


def choice_rows(*texts, correct=None, **extra):
    """The management form plus one row per option of a question formset."""
    data = {
        "choices-TOTAL_FORMS": str(len(texts)),
        "choices-INITIAL_FORMS": "0",
        "choices-MIN_NUM_FORMS": "2",
        "choices-MAX_NUM_FORMS": "1000",
    }
    for index, text in enumerate(texts):
        data[f"choices-{index}-text"] = text
    if correct is not None:
        data["choices-correct"] = str(correct)
    data.update(extra)
    return data


class WebTestCase(TestCase):
    """The person (staff) already logged in with a session."""

    def setUp(self):
        helpers.seed()
        self.person = User.objects.get(username="profe")
        self.web = Client()
        self.web.force_login(self.person)
        self.exam = Exam.objects.first()
        self.other = Exam.objects.last()


class SingleAnnouncementTests(WebTestCase):
    """I1: one error of business, one announcement."""

    def answer_with_a_broken_question(self):
        """A submission the service refuses: three options and none marked as correct."""
        return self.web.post(
            reverse("quiz_ui:question_create", args=[self.exam.pk]),
            choice_rows("Primera", "Segunda", "Tercera", exam=self.exam.pk, text="Sin correcta"),
        )

    def test_the_business_message_is_announced_once_and_only_once(self):
        response = self.answer_with_a_broken_question()
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertEqual(html.count('role="alert"'), 1)
        self.assertEqual(html.count("exactamente una opción correcta"), 1)

    def test_the_one_announcement_is_the_focusable_summary(self):
        html = self.answer_with_a_broken_question().content.decode()
        self.assertIn('id="error-summary"', html)
        self.assertIn('role="alert" tabindex="-1"', html)

    def test_the_fieldset_points_at_the_summary_instead_of_repeating_it(self):
        html = self.answer_with_a_broken_question().content.decode()
        self.assertIn('href="#error-summary"', html)
        self.assertEqual(html.count("exactamente una opción correcta"), 1)

    def test_a_form_without_errors_announces_nothing(self):
        html = self.web.get(reverse("quiz_ui:question_create", args=[self.exam.pk])).content.decode()
        self.assertNotIn('role="alert"', html)


class ChoiceKeptTests(WebTestCase):
    """I2: coming back with errors must not lose the option that was marked."""

    def test_the_marked_option_survives_a_form_that_came_back_invalid(self):
        response = self.web.post(
            reverse("quiz_ui:question_create", args=[self.exam.pk]),
            # The exam is missing, so the form comes back invalid with everything typed.
            choice_rows("A", "B", "C", correct=2, exam="", text="Enunciado"),
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)
        html = response.content.decode()
        self.assertEqual(re.findall(RADIO, html), ["2"])
        for text in ("A", "B", "C"):
            self.assertIn(f'value="{text}"', html)

    def test_the_marked_option_survives_an_invalid_edit(self):
        question = self.exam.questions.first()
        response = self.web.post(
            reverse("quiz_ui:question_update", kwargs={"pk": question.pk}),
            choice_rows("Alfa", "Beta", "Gama", correct=1, exam="", text=question.text),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(re.findall(RADIO, response.content.decode()), ["1"])

    def test_without_a_marked_option_nothing_is_checked(self):
        response = self.web.post(
            reverse("quiz_ui:question_create", args=[self.exam.pk]),
            choice_rows("A", "B", exam="", text="Enunciado"),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(re.findall(RADIO, response.content.decode()), [])

    def test_the_form_of_a_new_question_still_starts_unchecked(self):
        html = self.web.get(reverse("quiz_ui:question_create", args=[self.exam.pk])).content.decode()
        self.assertEqual(re.findall(RADIO, html), [])


class RecentExamsTests(WebTestCase):
    """I4: «Últimos exámenes» means the newest ones."""

    def test_the_panel_lists_the_newest_exams_first(self):
        newest = Exam.objects.create(title="Recién creado")
        response = self.web.get(reverse("quiz_ui:dashboard"))
        recent = list(response.context["recent_exams"])
        self.assertEqual(recent[0].pk, newest.pk)
        self.assertEqual([exam.pk for exam in recent], sorted(exam.pk for exam in recent)[::-1])

    def test_the_panel_shows_at_most_five_exams(self):
        for index in range(6):
            Exam.objects.create(title=f"Examen {index:02d}")
        recent = self.web.get(reverse("quiz_ui:dashboard")).context["recent_exams"]
        self.assertEqual(len(recent), 5)
        self.assertEqual(recent[0].title, "Examen 05")

    def test_an_exam_with_no_questions_is_still_the_newest(self):
        Exam.objects.create(title="Vacío")
        recent = self.web.get(reverse("quiz_ui:dashboard")).context["recent_exams"]
        self.assertEqual(recent[0].title, "Vacío")


class QuestionListingTests(WebTestCase):
    """I7: the global listing of questions, with search and exam filter (R-UI-02, R-UI-04)."""

    def url(self, **params):
        return self.web.get(reverse("quiz_ui:question_list"), params)

    def test_the_listing_shows_every_question_of_the_project(self):
        response = self.url()
        self.assertEqual(response.status_code, 200)
        total = response.context["page_obj"].paginator.count
        self.assertEqual(total, Question.objects.count())
        listed = list(response.context["questions"])
        second = self.url(page=2).context["questions"]
        self.assertEqual(len(listed) + len(second), total)

    def test_the_table_has_the_columns_the_requirement_asks_for(self):
        html = self.url().content.decode()
        for column in ("Id", "Examen", "Enunciado", "Opciones", "Correcta", "Acciones"):
            self.assertIn(column, html)

    def test_each_row_carries_its_options_and_the_correct_one(self):
        question = self.exam.questions.first()
        html = self.url().content.decode()
        correct = question.choices.filter(is_correct=True).first()
        self.assertIn(correct.text, html)

    def test_the_search_filters_by_the_text_of_the_statement(self):
        response = self.url(q="EXCLUDE")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["questions"]), 1)
        self.assertIn("exclude()", response.context["questions"][0].text)

    def test_the_search_does_not_distinguish_case(self):
        found = self.url(q="PLANTILLA")
        self.assertEqual(len(found.context["questions"]), 2)
        self.assertEqual(found.context["text"], "PLANTILLA")

    def test_the_exam_filter_keeps_only_that_exam(self):
        response = self.url(exam=self.other.pk)
        self.assertEqual(len(response.context["questions"]), self.other.questions.count())
        self.assertEqual(
            {question.exam_id for question in response.context["questions"]}, {self.other.pk}
        )

    def test_the_two_filters_can_be_combined(self):
        response = self.url(exam=self.exam.pk, q="Post.objects")
        self.assertEqual(len(response.context["questions"]), 1)

    def test_the_filters_survive_the_pagination(self):
        for index in range(6):
            self.other.questions.create(text=f"Pregunta {index}")
        second = self.url(exam=self.other.pk, page=2)
        self.assertEqual(second.status_code, 200)
        self.assertTrue(second.context["page_obj"].has_previous())
        self.assertIn(f"exam={self.other.pk}", second.content.decode())

    def test_the_listing_is_paginated_with_the_size_of_the_project(self):
        for index in range(7):
            self.other.questions.create(text=f"Pregunta {index}")
        first = self.url()
        self.assertEqual(len(first.context["questions"]), settings.PAGE_SIZE)
        self.assertEqual(first.context["page_obj"].paginator.num_pages, 3)

    def test_a_search_without_results_says_so_instead_of_being_empty(self):
        response = self.url(q="no hay nada con esta palabra")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["questions"]), 0)
        self.assertContains(response, "Ninguna pregunta coincide con la búsqueda")

    def test_a_project_without_questions_says_so(self):
        Question.objects.all().delete()
        response = self.url()
        self.assertContains(response, "Todavía no hay preguntas")

    def test_an_exam_that_does_not_exist_is_404(self):
        self.assertEqual(self.url(exam=99999).status_code, 404)

    def test_a_filter_that_is_not_an_id_is_404_and_not_a_500(self):
        for value in ("abc", "²", "-1"):
            self.assertEqual(self.url(exam=value).status_code, 404, value)

    def test_the_listing_is_reachable_from_the_navigation(self):
        html = self.url().content.decode()
        self.assertIn(reverse("quiz_ui:question_list"), html)

    def test_the_listing_is_for_the_person_only(self):
        client = Client()
        client.force_login(User.objects.create_user(username="alumno", password="x"))
        self.assertEqual(client.get(reverse("quiz_ui:question_list")).status_code, 403)
        self.assertEqual(Client().get(reverse("quiz_ui:question_list")).status_code, 302)

    def test_the_listing_refuses_a_post(self):
        self.assertEqual(self.web.post(reverse("quiz_ui:question_list"), {}).status_code, 405)


class OnePageSizeTests(WebTestCase):
    """I8: one page size for the two presentations (R-UI-03)."""

    def test_the_exam_list_pages_with_the_size_of_the_project(self):
        for index in range(settings.PAGE_SIZE + 1):
            Exam.objects.create(title=f"Examen {index:02d}")
        response = self.web.get(reverse("quiz_ui:exam_list"))
        self.assertEqual(len(response.context["exams"]), settings.PAGE_SIZE)

    def test_the_api_pages_with_the_same_number(self):
        token, _ = helpers.seed()
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        results = client.get("/api/questions/").json()["results"]
        self.assertEqual(len(results), settings.PAGE_SIZE)
        self.assertEqual(settings.REST_FRAMEWORK["PAGE_SIZE"], settings.PAGE_SIZE)