"""Holes of ``test_web.py``, the ones that are worth a test.

``test_web.py`` already walks the happy path of the interface (login, panel, listados,
formularios, borrado con confirmación, paginación, CSRF, la frontera con la API). These
tests do not repeat it: they cover the cells it does not touch, and every one of them was
checked against the delivered server before being written here.

The gaps, in order of value:
  1. a POST shaped like a real browser sends it (the three empty rows of the formset);
  2. the 404 of the screens of an exam or a question that does not exist;
  3. the pages that do not exist (page 99, page 0, page «abc»);
  4. the verbs each screen answers (GET only for reading, POST for logout, 405 otherwise);
  5. the login screen when a session already exists;
  6. the limits of the fields (title 121, option 201);
  7. moving a question to another exam, and the destination of the delete redirects;
  8. the write screens seen by a user who is not staff.
"""
from html import escape

from django.contrib.auth.models import User
from django.test import Client, TestCase

from quiz.models import Choice, Exam, Question

from . import helpers


def browser_rows(*texts, correct=None, **extra):
    """The payload a browser sends: one row per option the form SHOWN, not per option typed.

    The formset of the lab always renders three extra rows, so a real submission carries
    five rows with three of them empty. That shape was not covered anywhere.
    """
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


class WebGapTestCase(TestCase):
    def setUp(self):
        helpers.seed()
        self.person = User.objects.get(username="profe")
        self.web = Client()
        self.web.force_login(self.person)
        self.exam = Exam.objects.first()
        self.other = Exam.objects.last()

    def ask(self, *texts, correct=None, **extra):
        return browser_rows(*texts, correct=correct, **extra)


class BrowserShapeTests(WebGapTestCase):
    """Gap 1: the submission a browser really makes."""

    def test_the_empty_rows_of_the_form_are_not_saved(self):
        """Five rows sent, two filled: the question is created with its two options."""
        response = self.web.post(
            f"/examenes/{self.exam.pk}/preguntas/nuevo/",
            self.ask("Un estilo de arquitectura sobre HTTP", "Un lenguaje de programación", "", "", "",
                     correct=0, exam=self.exam.pk, text="Enviado por un navegador"),
        )
        self.assertRedirects(response, f"/examenes/{self.exam.pk}/")
        question = Question.objects.get(text="Enviado por un navegador")
        self.assertEqual(question.choices.count(), 2)

    def test_a_row_with_only_spaces_is_not_an_option(self):
        """A row the person left half written does not count: only one option is filled."""
        before = Question.objects.count()
        response = self.web.post(
            f"/examenes/{self.exam.pk}/preguntas/nuevo/",
            self.ask("Única", "   ", correct=0, exam=self.exam.pk, text="Media escrita"),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "al menos dos opciones")
        self.assertEqual(Question.objects.count(), before)

    def test_the_form_shows_three_empty_rows_to_type_in(self):
        """The GET of the form offers five rows: two to fill and three spare."""
        response = self.web.get(f"/examenes/{self.exam.pk}/preguntas/nuevo/")
        self.assertEqual(response.content.decode().count('name="choices-0-text"'), 1)
        self.assertEqual(response.content.decode().count('name="choices-4-text"'), 1)


class MissingObjectTests(WebGapTestCase):
    """Gap 2: a screen of something that does not exist."""

    def test_an_unknown_exam_detail_is_404(self):
        self.assertEqual(self.web.get("/examenes/9999/").status_code, 404)

    def test_an_unknown_exam_edit_is_404(self):
        self.assertEqual(self.web.get("/examenes/9999/editar/").status_code, 404)

    def test_deleting_an_unknown_exam_is_404_and_deletes_nothing(self):
        self.assertEqual(self.web.get("/examenes/9999/eliminar/").status_code, 404)
        response = self.web.post("/examenes/9999/eliminar/")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(Exam.objects.count(), 2)

    def test_an_unknown_question_edit_is_404(self):
        self.assertEqual(self.web.get("/preguntas/9999/editar/").status_code, 404)

    def test_deleting_an_unknown_question_is_404(self):
        self.assertEqual(self.web.get("/preguntas/9999/eliminar/").status_code, 404)
        self.assertEqual(self.web.post("/preguntas/9999/eliminar/").status_code, 404)
        self.assertEqual(Question.objects.count(), 8)


class PaginationGapTests(WebGapTestCase):
    """Gap 3: pages that do not exist."""

    def test_the_last_page_has_the_remainder_when_the_total_is_not_a_multiple(self):
        for index in range(9):  # 2 from the seed + 9 = 11 exams, 5 per page (settings.PAGE_SIZE)
            Exam.objects.create(title=f"Examen {index:02d}")
        last = self.web.get("/examenes/", {"page": 3})
        self.assertEqual(last.status_code, 200)
        self.assertEqual(len(last.context["exams"]), 1)

    def test_a_page_that_does_not_exist_is_404(self):
        self.assertEqual(self.web.get("/examenes/", {"page": 99}).status_code, 404)

    def test_page_zero_is_404(self):
        self.assertEqual(self.web.get("/examenes/", {"page": 0}).status_code, 404)

    def test_a_page_that_is_not_a_number_is_404(self):
        self.assertEqual(self.web.get("/examenes/", {"page": "abc"}).status_code, 404)


class VerbTests(WebGapTestCase):
    """Gap 4: which verb each screen answers."""

    def test_the_read_only_screens_refuse_a_post(self):
        for url in ("/", "/examenes/", f"/examenes/{self.exam.pk}/"):
            self.assertEqual(self.web.post(url, {}).status_code, 405, url)

    def test_logging_out_only_answers_post(self):
        """GET /salir/ is 405: closing a session must not be something a link can do."""
        self.assertEqual(self.web.get("/salir/").status_code, 405)
        self.assertEqual(self.web.post("/salir/").status_code, 302)
        self.assertEqual(self.web.get("/").status_code, 302)  # the session was really closed


class SessionGapTests(WebGapTestCase):
    """Gap 5: the login screen with a session already open."""

    def test_the_login_screen_sends_a_session_to_the_panel(self):
        response = self.web.get("/acceso/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/")

    def test_signing_in_again_does_not_reach_the_login_screen(self):
        self.web.post("/acceso/", {"username": "profe", "password": "whatever"})
        self.assertEqual(self.web.get("/").status_code, 200)


class FieldLimitTests(WebGapTestCase):
    """Gap 6: the limits the fields declare."""

    def test_a_title_of_the_exact_maximum_length_is_saved(self):
        response = self.web.post("/examenes/nuevo/", {"title": "x" * 120})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Exam.objects.filter(title="x" * 120).exists())

    def test_a_title_longer_than_the_field_is_rejected_with_an_inline_error(self):
        response = self.web.post("/examenes/nuevo/", {"title": "x" * 121})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="id_title-error"')
        self.assertFalse(Exam.objects.filter(title="x" * 121).exists())

    def test_an_option_longer_than_the_field_is_rejected_and_nothing_is_created(self):
        before = (Question.objects.count(), Choice.objects.count())
        response = self.web.post(
            f"/examenes/{self.exam.pk}/preguntas/nuevo/",
            self.ask("a" * 201, "b", correct=0, exam=self.exam.pk, text="Opción demasiado larga"),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "menos de 200 caracteres")
        self.assertEqual((Question.objects.count(), Choice.objects.count()), before)

    def test_an_option_of_the_exact_maximum_length_is_saved(self):
        response = self.web.post(
            f"/examenes/{self.exam.pk}/preguntas/nuevo/",
            self.ask("a" * 200, "b", correct=0, exam=self.exam.pk, text="Opción del límite"),
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Question.objects.get(text="Opción del límite").choices.count(), 2)


class MovingAndRedirectTests(WebGapTestCase):
    """Gap 7: a question that changes exam, and where the redirects point."""

    def test_a_question_can_be_moved_to_another_exam(self):
        question = self.exam.questions.first()
        response = self.web.post(
            f"/preguntas/{question.pk}/editar/",
            self.ask("Primera", "Segunda", correct=0, exam=self.other.pk, text=question.text),
        )
        self.assertRedirects(response, f"/examenes/{self.other.pk}/")
        question.refresh_from_db()
        self.assertEqual(question.exam_id, self.other.pk)
        self.assertEqual(question.choices.count(), 2)

    def test_deleting_a_question_returns_to_the_exam_it_belongs_to(self):
        """The delete screen carries no exam in the URL: the redirect follows the object."""
        question = self.other.questions.first()
        response = self.web.post(f"/preguntas/{question.pk}/eliminar/")
        self.assertRedirects(response, f"/examenes/{self.other.pk}/")
        self.assertFalse(Question.objects.filter(pk=question.pk).exists())

    def test_editing_a_question_keeps_the_options_marked_correct(self):
        question = self.exam.questions.first()
        self.web.post(
            f"/preguntas/{question.pk}/editar/",
            self.ask("Alpha", "Beta", correct=1, exam=self.exam.pk, text=question.text),
        )
        question.refresh_from_db()
        self.assertEqual([choice.text for choice in question.choices.all() if choice.is_correct], ["Beta"])


class NonStaffScreenTests(TestCase):
    """Gap 8: the write screens as somebody who is not staff."""

    def setUp(self):
        helpers.seed()
        self.student = User.objects.create_user(username="alumno", password="x")
        self.agent = User.objects.get(username="agente")
        self.exam = Exam.objects.first()
        self.web = Client()
        self.web.force_login(self.student)

    def test_a_student_gets_403_on_every_screen(self):
        urls = [
            "/", "/examenes/", "/examenes/nuevo/", f"/examenes/{self.exam.pk}/",
            f"/examenes/{self.exam.pk}/editar/", f"/examenes/{self.exam.pk}/eliminar/",
            f"/examenes/{self.exam.pk}/preguntas/nuevo/", "/preguntas/1/editar/",
            "/preguntas/1/eliminar/",
        ]
        for url in urls:
            self.assertEqual(self.web.get(url).status_code, 403, url)
            self.assertEqual(self.web.post(url, {"title": "no"}).status_code, 403, url)
        self.assertEqual(Exam.objects.count(), 2)

    def test_the_agent_is_also_403_on_the_write_screens(self):
        """The group «agente» gives the API its powers, not the interface's."""
        self.web.force_login(self.agent)
        for url in ("/", "/examenes/", "/examenes/nuevo/", f"/examenes/{self.exam.pk}/preguntas/nuevo/"):
            self.assertEqual(self.web.get(url).status_code, 403, url)
        self.assertEqual(Question.objects.count(), 8)


class DetailContentTests(WebGapTestCase):
    """The detail screen shows the whole exam, not only its first question."""

    def test_every_question_of_the_exam_and_every_option_is_on_the_detail_screen(self):
        response = self.web.get(f"/examenes/{self.exam.pk}/")
        html = response.content.decode()
        for question in self.exam.questions.all():
            # the texts travel through the template, so they arrive HTML-escaped
            self.assertIn(escape(question.text[:40]), html)
            for choice in question.choices.all():
                self.assertIn(escape(choice.text), html)
        self.assertNotIn("Django · Plantillas", html)  # only the exam that was asked for

    def test_the_detail_screen_says_how_many_questions_the_exam_has(self):
        response = self.web.get(f"/examenes/{self.exam.pk}/")
        self.assertContains(response, "4 preguntas")
        self.assertEqual(response.context["exam"].question_count, 4)