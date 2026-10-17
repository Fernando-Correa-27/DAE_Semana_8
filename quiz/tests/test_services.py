"""The one rule and the one table: the same answer whichever way you ask.

ADR-0002 asks for a test that *affirms* that an invalid body gets the same verdict
through the serializer (API) and through the formset (web interface), and ADR-0003
asks for the deny-by-default of an unknown verb, which no delivered test covered.

Both live here, on purpose: ``test_api.py`` and ``test_permissions.py`` are the
specification of the lab and this file does not touch them, it only proves the
properties the ADRs declare.
"""
from types import SimpleNamespace

from django.contrib.auth.models import User
from rest_framework.test import APIRequestFactory, APITestCase

from quiz import services
from quiz.forms import CHOICES_PREFIX, ChoiceFormSetFactory
from quiz.models import Exam, Question
from quiz.permissions import AgentPermission
from quiz.views import QuestionViewSet

from .helpers import reader_token, seed

ONE_CHOICE = [{"text": "Única", "is_correct": True}]
TWO_CORRECT = [{"text": "A", "is_correct": True}, {"text": "B", "is_correct": True}]
NO_CORRECT = [{"text": "A", "is_correct": False}, {"text": "B", "is_correct": False}]


class SameVerdictTests(APITestCase):
    """The same invalid body, the same wording: serializer on one side, formset on the other."""

    def setUp(self):
        self.token, _ = seed()
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token}")
        self.exam = Exam.objects.first()

    def api_verdict(self, choices):
        """What the API answers: the status and every message of the body."""
        response = self.client.post(
            "/api/questions/",
            {"exam": self.exam.pk, "text": "Enunciado", "choices": choices},
            format="json",
        )
        return response.status_code, [str(error) for error in response.json()["choices"]]

    def form_verdict(self, choices, marked=None):
        """What the web interface answers: the messages of the options formset."""
        data = {
            f"{CHOICES_PREFIX}-TOTAL_FORMS": str(len(choices)),
            f"{CHOICES_PREFIX}-INITIAL_FORMS": "0",
            f"{CHOICES_PREFIX}-MIN_NUM_FORMS": "2",
            f"{CHOICES_PREFIX}-MAX_NUM_FORMS": "1000",
            "exam": self.exam.pk,
            "text": "Enunciado",
        }
        for index, choice in enumerate(choices):
            data[f"{CHOICES_PREFIX}-{index}-text"] = choice["text"]
        if marked is not None:
            data[f"{CHOICES_PREFIX}-correct"] = str(marked)
        formset = ChoiceFormSetFactory(data, prefix=CHOICES_PREFIX)
        self.assertFalse(formset.is_valid())
        return list(formset.non_form_errors())

    def assert_the_same_verdict(self, choices, marked=None):
        status, api_errors = self.api_verdict(choices)
        self.assertEqual(status, 400)
        form_errors = self.form_verdict(choices, marked)
        self.assertEqual(len(form_errors), 1)
        self.assertEqual(api_errors, form_errors)

    def test_one_choice_is_refused_by_both(self):
        self.assert_the_same_verdict(ONE_CHOICE, marked=0)

    def test_no_correct_choice_is_refused_by_both(self):
        self.assert_the_same_verdict(NO_CORRECT)

    def test_two_correct_choices_are_refused_with_the_same_wording(self):
        """The browser cannot even send it: the radio group marks one option at a time.

        So the API is the only path that can receive it, and it must answer with the
        wording of the service and not with a message of its own.
        """
        with self.assertRaises(services.QuizRuleError) as ctx:
            services.validate_question_choices(TWO_CORRECT)
        status, api_errors = self.api_verdict(TWO_CORRECT)
        self.assertEqual(status, 400)
        self.assertEqual(api_errors, [str(ctx.exception)])

    def test_the_two_writings_are_the_ones_of_the_service(self):
        with self.assertRaises(services.QuizRuleError) as few:
            services.validate_question_choices(ONE_CHOICE)
        with self.assertRaises(services.QuizRuleError) as none:
            services.validate_question_choices(NO_CORRECT)
        self.assertEqual(
            self.api_verdict(ONE_CHOICE)[1],
            self.form_verdict(ONE_CHOICE, marked=0),
        )
        self.assertIn("dos opciones", str(few.exception))
        self.assertIn("exactamente una opción correcta", str(none.exception))
        self.assertEqual(self.api_verdict(NO_CORRECT)[1], [str(none.exception)])


class WebAdapterTests(APITestCase):
    """The browser asks the same table the API asks, and answers the same verbs."""

    def setUp(self):
        self.token, _ = seed()
        reader_token()  # creates the user «lector»
        self.person = User.objects.get(username="profe")
        self.agent = User.objects.get(username="agente")
        self.reader = User.objects.get(username="lector")

    def request(self, method, user=None):
        request = APIRequestFactory().generic(method, "/api/questions/")
        request.user = user
        return request

    def test_the_action_of_a_browser_verb_is_known(self):
        """GET/HEAD/OPTIONS read, POST creates, PUT/PATCH modify, DELETE deletes."""
        expected = {
            "GET": "read", "HEAD": "read", "OPTIONS": "read",
            "POST": "create", "PUT": "modify", "PATCH": "modify", "DELETE": "delete",
        }
        for method, action in expected.items():
            self.assertEqual(services.web_action(method), action)
            self.assertEqual(services.web_action(method.lower()), action)

    def test_an_unknown_verb_is_no_action_of_the_interface(self):
        for method in ("TRACE", "CONNECT", "", None, "get extra"):
            self.assertEqual(services.web_action(method), "", method)

    def test_the_interface_is_opened_to_the_person_and_to_nobody_else(self):
        for method in ("GET", "POST", "PUT", "PATCH", "DELETE"):
            self.assertTrue(services.may_use(self.person, method), method)
            self.assertFalse(services.may_use(self.agent, method), method)
            self.assertFalse(services.may_use(self.reader, method), method)
            self.assertFalse(services.may_use(None, method), method)

    def test_an_unknown_verb_is_denied_in_the_interface_to_everybody(self):
        for user in (self.person, self.agent, self.reader, None):
            self.assertFalse(services.may_use(user, "TRACE"), user)

    def test_the_interface_and_the_api_agree_on_a_superuser_without_is_staff(self):
        """The divergence the review reported: the API said «person», the UI answered 403."""
        superuser = User.objects.create_user(username="root", is_superuser=True, is_staff=False)
        self.assertEqual(services.role_of(superuser), services.PERSON)
        for method in ("GET", "POST", "DELETE"):
            self.assertTrue(services.may_use(superuser, method), method)
            self.assertTrue(
                AgentPermission().has_permission(self.request(method, superuser), QuestionViewSet()),
                method,
            )


class MethodResolutionTests(APITestCase):
    """``method_of``: the verb of the request, or the one the action of the view stands for."""

    def test_the_verb_of_the_request_wins(self):
        view = QuestionViewSet()
        view.action = "list"
        self.assertEqual(services.method_of(APIRequestFactory().post("/api/questions/"), view), "POST")

    def test_without_a_verb_the_action_of_the_view_answers(self):
        """DRF always sends ``request.method``, so this is the adapter's own safety net."""
        view = QuestionViewSet()
        for action, method in services.ACTION_METHODS.items():
            view.action = action
            self.assertEqual(services.method_of(SimpleNamespace(), view), method, action)

    def test_an_unknown_action_without_a_verb_is_no_method_at_all(self):
        view = QuestionViewSet()
        view.action = "publish"
        self.assertEqual(services.method_of(SimpleNamespace(), view), "")

    def test_neither_a_verb_nor_a_view(self):
        self.assertEqual(services.method_of(SimpleNamespace(), None), "")


class DenyByDefaultTests(APITestCase):
    """An unknown verb is denied to every role: the literal requirement of Part 3."""

    VERBS = ("TRACE", "CONNECT", "PROPFIND", "LOCK", "FOO")

    def setUp(self):
        self.token, self.agent_token = seed()
        self.person = User.objects.get(username="profe")
        self.agent = User.objects.get(username="agente")

    def test_an_unknown_verb_is_denied_to_every_role(self):
        for role in (services.PERSON, services.AGENT, services.READER, services.ANONYMOUS):
            for verb in self.VERBS:
                self.assertFalse(services.may(role, verb), f"{role} · {verb}")

    def test_an_unknown_verb_never_reaches_the_handler(self):
        for verb in self.VERBS:
            request = APIRequestFactory().generic(verb, "/api/questions/")
            request.user = self.person
            view = QuestionViewSet()
            view.action = "list"
            self.assertFalse(AgentPermission().has_permission(request, view), verb)

    def test_the_verbs_of_the_table_are_the_ones_the_lab_asks_for(self):
        self.assertEqual(
            sorted(services.METHODS_BY_ROLE[services.PERSON]),
            ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"],
        )
        self.assertEqual(
            sorted(services.METHODS_BY_ROLE[services.AGENT]),
            ["GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"],
        )


class ExamFilterTests(APITestCase):
    """``?exam=``: a filter that is not an id is a 400, never a 500 and never silence."""

    def setUp(self):
        self.token, _ = seed()
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token}")
        self.exam = Exam.objects.first()

    def test_a_valid_filter_narrows_the_listing(self):
        response = self.client.get("/api/questions/", {"exam": self.exam.pk})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], self.exam.questions.count())

    def test_an_unknown_but_well_formed_id_is_an_empty_200(self):
        """An id that simply does not exist is not a mistake of the caller."""
        response = self.client.get("/api/questions/", {"exam": 99999})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 0)

    def test_values_that_are_not_an_id_are_400(self):
        for value in ("abc", "²", "1.0", "-1", "", " ", "1 OR 1=1", "٣", "9" * 30):
            response = self.client.get("/api/questions/", {"exam": value})
            self.assertEqual(response.status_code, 400, value)
            self.assertIn("exam", response.json())

    def test_no_filter_at_all_is_the_whole_listing(self):
        self.assertEqual(self.client.get("/api/questions/").json()["count"], Question.objects.count())