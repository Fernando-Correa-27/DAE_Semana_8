"""Recorridos de la interfaz web por HTTP.

El runner del proyecto es ``python manage.py test``. Estas pruebas no tocan la
API: comprueban la segunda presentación del mismo dominio (sesión de Django,
plantillas, formularios) y que las dos fronteras siguen sin mezclarse.
"""
import re

from django.contrib.auth.models import User
from django.contrib.staticfiles import finders
from django.test import Client, TestCase
from django.urls import reverse

from quiz import services
from quiz.models import Choice, Exam, Question

from . import helpers


def choice_rows(*texts):
    """The management form plus one row per option of a question formset."""
    data = {
        "choices-TOTAL_FORMS": str(len(texts)),
        "choices-INITIAL_FORMS": "0",
        "choices-MIN_NUM_FORMS": "2",
        "choices-MAX_NUM_FORMS": "1000",
    }
    for index, text in enumerate(texts):
        data[f"choices-{index}-text"] = text
    return data


class UiTestCase(TestCase):
    """Persona (``profe``, staff) already logged in with a session."""

    def setUp(self):
        helpers.seed()
        self.person = User.objects.get(username="profe")
        self.client.force_login(self.person)
        self.exam = Exam.objects.first()

    def post_question(self, url, *texts, correct=None, **extra):
        data = choice_rows(*texts)
        if correct is not None:
            data["choices-correct"] = str(correct)
        data.update(extra)
        return self.client.post(url, data)


class AccessTests(UiTestCase):
    def test_anonymous_is_sent_to_the_login_page(self):
        self.client.logout()
        response = self.client.get(reverse("quiz_ui:dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("quiz_ui:login"), response["Location"])
        self.assertEqual(self.client.get(reverse("quiz_ui:login")).status_code, 200)

    def test_a_logged_in_user_without_staff_gets_403(self):
        student = User.objects.create_user(username="alumno", password="x")
        self.client.force_login(student)
        response = self.client.get(reverse("quiz_ui:dashboard"))
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "profesorado", status_code=403)

    def test_the_agent_is_a_reader_for_the_web_interface(self):
        self.client.force_login(User.objects.get(username="agente"))
        self.assertEqual(self.client.get(reverse("quiz_ui:dashboard")).status_code, 403)

    def test_logout_closes_the_session(self):
        response = self.client.post(reverse("quiz_ui:logout"))
        self.assertRedirects(response, reverse("quiz_ui:login"))
        self.assertEqual(self.client.get(reverse("quiz_ui:dashboard")).status_code, 302)

    def test_login_with_the_password_of_the_person(self):
        from django.contrib.auth.hashers import make_password

        self.client.logout()
        self.person.password = make_password("clave-de-prueba")
        self.person.save(update_fields=["password"])
        response = self.client.post(
            reverse("quiz_ui:login"), {"username": "profe", "password": "clave-de-prueba"}
        )
        self.assertRedirects(response, reverse("quiz_ui:dashboard"))

    def test_a_wrong_password_does_not_open_the_interface(self):
        self.client.logout()
        self.person.set_password("clave-de-prueba")
        self.person.save(update_fields=["password"])
        response = self.client.post(
            reverse("quiz_ui:login"), {"username": "profe", "password": "otra-cosa"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get(reverse("quiz_ui:dashboard")).status_code, 302)


class FrontierTests(UiTestCase):
    """The session of the UI never opens the API and the token never opens the UI."""

    def test_a_session_does_not_authenticate_the_api(self):
        self.client.force_login(User.objects.get(username="agente"))
        response = self.client.get("/api/questions/")
        self.assertEqual(response.status_code, 401)

    def test_a_token_does_not_authenticate_the_interface(self):
        self.client.logout()
        token = helpers.seed()[0]
        response = self.client.get(reverse("quiz_ui:dashboard"), headers={"authorization": f"Token {token}"})
        self.assertEqual(response.status_code, 302)


class DashboardAndListTests(UiTestCase):
    def test_dashboard_shows_the_three_counters(self):
        response = self.client.get(reverse("quiz_ui:dashboard"))
        self.assertContains(response, "Exámenes")
        self.assertEqual(response.context["totals"]["exams"], Exam.objects.count())
        self.assertEqual(response.context["totals"]["questions"], Question.objects.count())
        self.assertEqual(response.context["totals"]["choices"], Choice.objects.count())

    def test_exam_list_shows_the_number_of_questions(self):
        response = self.client.get(reverse("quiz_ui:exam_list"))
        for exam in Exam.objects.all():
            self.assertContains(response, exam.title)
        self.assertEqual(response.context["exams"][0].question_count, self.exam.questions.count())

    def test_exam_list_has_an_empty_state(self):
        Exam.objects.all().delete()
        response = self.client.get(reverse("quiz_ui:exam_list"))
        self.assertContains(response, "No hay exámenes")
        self.assertEqual(response.context["page_obj"].paginator.num_pages, 1)

    def test_exam_list_is_paginated(self):
        Exam.objects.all().delete()
        for index in range(11):
            Exam.objects.create(title=f"Examen {index:02d}")
        first = self.client.get(reverse("quiz_ui:exam_list"))
        self.assertEqual(len(first.context["exams"]), 10)
        second = self.client.get(reverse("quiz_ui:exam_list"), {"page": 2})
        self.assertEqual(len(second.context["exams"]), 1)
        self.assertContains(second, "Examen 10")


class ExamCrudTests(UiTestCase):
    def test_create_an_exam(self):
        response = self.client.post(reverse("quiz_ui:exam_create"), {"title": "Prueba de Córdoba"})
        self.assertRedirects(response, reverse("quiz_ui:exam_list"))
        self.assertTrue(Exam.objects.filter(title="Prueba de Córdoba").exists())

    def test_the_success_message_is_shown_after_saving(self):
        response = self.client.post(
            reverse("quiz_ui:exam_create"), {"title": "Prueba de Córdoba"}, follow=True
        )
        self.assertContains(response, "Prueba de Córdoba")
        self.assertContains(response, "creado")

    def test_an_empty_title_comes_back_with_an_inline_error(self):
        response = self.client.post(reverse("quiz_ui:exam_create"), {"title": ""})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Exam.objects.filter(title="").exists())
        self.assertTrue(response.context["form"].errors["title"])
        self.assertContains(response, 'id="id_title-error"')
        self.assertContains(response, 'aria-describedby="id_title-help id_title-error"')

    def test_edit_an_exam(self):
        response = self.client.post(
            reverse("quiz_ui:exam_update", args=[self.exam.pk]), {"title": "Título corregido"}
        )
        self.assertRedirects(response, reverse("quiz_ui:exam_list"))
        self.exam.refresh_from_db()
        self.assertEqual(self.exam.title, "Título corregido")

    def test_deleting_an_exam_asks_first(self):
        url = reverse("quiz_ui:exam_delete", args=[self.exam.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "no se puede deshacer")
        self.assertTrue(Exam.objects.filter(pk=self.exam.pk).exists())

    def test_delete_an_exam_on_post(self):
        exam_id = self.exam.pk
        response = self.client.post(reverse("quiz_ui:exam_delete", args=[exam_id]), follow=True)
        self.assertRedirects(response, reverse("quiz_ui:exam_list"))
        self.assertFalse(Exam.objects.filter(pk=exam_id).exists())
        self.assertContains(response, "eliminado")


class QuestionCrudTests(UiTestCase):
    def test_the_detail_page_lists_the_questions_and_their_choices(self):
        response = self.client.get(reverse("quiz_ui:exam_detail", args=[self.exam.pk]))
        self.assertEqual(response.status_code, 200)
        question = self.exam.questions.first()
        self.assertContains(response, question.text)
        self.assertContains(response, question.choices.first().text)

    def test_the_detail_page_of_an_exam_without_questions_has_an_empty_state(self):
        Question.objects.all().delete()
        response = self.client.get(reverse("quiz_ui:exam_detail", args=[self.exam.pk]))
        self.assertContains(response, "todavía no tiene preguntas")

    def test_create_a_question_with_its_choices(self):
        url = reverse("quiz_ui:question_create", args=[self.exam.pk])
        response = self.post_question(
            url,
            "Un estilo de arquitectura sobre HTTP",
            "Un lenguaje de programación",
            correct=0,
            exam=self.exam.pk,
            text="¿Qué es una API REST?",
        )
        self.assertRedirects(response, reverse("quiz_ui:exam_detail", args=[self.exam.pk]))
        question = Question.objects.get(text="¿Qué es una API REST?")
        self.assertEqual(question.choices.count(), 2)
        correct = [choice.text for choice in question.choices.all() if choice.is_correct]
        self.assertEqual(correct, ["Un estilo de arquitectura sobre HTTP"])
        self.assertContains(self.client.get(url), "choices-correct")

    def test_the_form_renders_one_shared_radio_group(self):
        response = self.client.get(reverse("quiz_ui:question_create", args=[self.exam.pk]))
        self.assertEqual(response.content.decode().count('name="choices-correct"'), 5)

    def test_a_question_with_one_option_is_rejected(self):
        url = reverse("quiz_ui:question_create", args=[self.exam.pk])
        response = self.post_question(url, "Única opción", correct=0, exam=self.exam.pk, text="Solo una")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "al menos dos opciones")
        self.assertFalse(Question.objects.filter(text="Solo una").exists())

    def test_a_question_without_a_correct_option_is_rejected(self):
        url = reverse("quiz_ui:question_create", args=[self.exam.pk])
        response = self.post_question(url, "Una", "Otra", exam=self.exam.pk, text="Ninguna correcta")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "exactamente una opción correcta")
        self.assertFalse(Question.objects.filter(text="Ninguna correcta").exists())

    def test_the_error_wording_is_the_one_of_the_service(self):
        url = reverse("quiz_ui:question_create", args=[self.exam.pk])
        response = self.post_question(url, "Única opción", correct=0, exam=self.exam.pk, text="Solo una")
        formset = response.context["choices_formset"]
        with self.assertRaises(services.QuizRuleError) as ctx:
            services.validate_question_choices([{"text": "Única opción", "is_correct": True}])
        self.assertEqual(list(formset.non_form_errors()), [str(ctx.exception)])

    def test_update_a_question_replaces_its_choices(self):
        question = self.exam.questions.first()
        response = self.post_question(
            reverse("quiz_ui:question_update", kwargs={"pk": question.pk}),
            "Primera",
            "Segunda",
            "Tercera",
            correct=2,
            exam=self.exam.pk,
            text=question.text,
        )
        self.assertRedirects(response, reverse("quiz_ui:exam_detail", args=[self.exam.pk]))
        question.refresh_from_db()
        self.assertEqual(question.choices.count(), 3)
        self.assertEqual(
            [choice.text for choice in question.choices.all() if choice.is_correct], ["Tercera"]
        )

    def test_the_form_of_an_edit_shows_the_correct_option_marked(self):
        question = self.exam.questions.first()
        response = self.client.get(reverse("quiz_ui:question_update", kwargs={"pk": question.pk}))
        html = response.content.decode()
        correct_index = next(
            index for index, choice in enumerate(question.choices.all()) if choice.is_correct
        )
        checked = re.findall(r'<input type="radio"[^>]*value="(\d+)"[^>]*checked', html)
        self.assertEqual(checked, [str(correct_index)])

    def test_delete_a_question_asks_first_and_then_deletes(self):
        question = self.exam.questions.first()
        url = reverse("quiz_ui:question_delete", kwargs={"pk": question.pk})
        self.assertContains(self.client.get(url), "no se puede deshacer")
        self.assertTrue(Question.objects.filter(pk=question.pk).exists())
        response = self.client.post(url, follow=True)
        self.assertRedirects(response, reverse("quiz_ui:exam_detail", args=[self.exam.pk]))
        self.assertFalse(Question.objects.filter(pk=question.pk).exists())
        self.assertContains(response, "Pregunta eliminada")

    def test_an_unknown_exam_is_a_404(self):
        self.assertEqual(self.client.get(reverse("quiz_ui:question_create", args=[9999])).status_code, 404)


class SecurityAndAssetTests(UiTestCase):
    def test_a_post_without_the_csrf_token_is_forbidden(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.person)
        response = client.post(reverse("quiz_ui:exam_create"), {"title": "Sin token CSRF"})
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Exam.objects.filter(title="Sin token CSRF").exists())

    def test_the_interface_does_not_depend_on_the_internet(self):
        response = self.client.get(reverse("quiz_ui:dashboard"))
        self.assertNotContains(response, "cdn")
        self.assertNotContains(response, "https://")
        self.assertIsNotNone(finders.find("quiz/css/app.css"))

    def test_no_emoji_in_the_screens(self):
        for url in self._screens():
            html = self.client.get(url).content.decode("utf-8")
            for character in html:
                code = ord(character)
                self.assertFalse(
                    0x2600 <= code <= 0x27BF or 0x1F300 <= code <= 0x1FAFF,
                    f"Hay un icono en {url}: {character!r}",
                )

    def _screens(self):
        return [
            reverse("quiz_ui:dashboard"),
            reverse("quiz_ui:exam_list"),
            reverse("quiz_ui:exam_detail", args=[self.exam.pk]),
            reverse("quiz_ui:question_create", args=[self.exam.pk]),
            reverse("quiz_ui:login"),
        ]