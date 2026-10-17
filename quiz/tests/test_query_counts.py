"""How many queries each listing costs, pinned to a number.

The N+1 problem is not a matter of taste: it is a number of queries that grows with the
data. These tests fix that number, and they also fix the *shape* of the answer: the same
listing is measured with 8 questions and with 68, and it must cost exactly the same. A
number that only says «> 0» would not catch anything.

The numbers come from the delivered server and are broken down in each docstring, so a
failure says WHICH part of the request grew.

Two presentations are covered:
  - the API (``/api/questions/``, ``/api/exams/``), which the agent and quizctl read;
  - the web interface (the exam detail, the exam list and the dashboard).
And the lowest layer, ``quiz.queries``, is measured on its own.
"""
from django.contrib.auth.models import User
from django.test import Client, TestCase
from rest_framework.test import APITestCase

from quiz import queries
from quiz.models import Choice, Exam, Question

from .helpers import exam_id, seed

QUESTIONS = "/api/questions/"
EXAMS = "/api/exams/"

# The queries of an authenticated API read, one by one:
#   1 the token (and its user) of the Authorization header;
#   2 the COUNT(*) the pagination needs;
#   3 the rows, with the exam already JOINed (select_related);
#   4 the options of the page, in one query (prefetch_related).
API_QUESTION_LIST = 4
# The exams listing needs no join per row: the counter is an annotation (3 in total).
API_EXAM_LIST = 3
# A single object: the token, the row with its exam JOINed, and its options.
API_QUESTION_DETAIL = 3


class ApiQueryCountTests(APITestCase):
    def setUp(self):
        self.person, _ = seed()
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.person}")
        self.exam = exam_id()
        self.question = Question.objects.first()

    def add_questions(self, how_many):
        """More data, so a query that grows with the rows has somewhere to show up."""
        exam = Exam.objects.get(pk=self.exam)
        for index in range(how_many):
            exam.questions.create(text=f"Pregunta de relleno {index}")

    def test_the_question_list_costs_four_queries(self):
        """GET /api/questions/ -> token + COUNT + rows (JOIN) + options."""
        with self.assertNumQueries(API_QUESTION_LIST):
            self.assertEqual(self.client.get(QUESTIONS).status_code, 200)

    def test_the_question_list_costs_the_same_with_sixty_more_questions(self):
        """68 questions instead of 8, still 4 queries: that is what rules the N+1 out."""
        self.add_questions(60)
        self.assertEqual(Question.objects.count(), 68)
        with self.assertNumQueries(API_QUESTION_LIST):
            self.assertEqual(self.client.get(QUESTIONS).status_code, 200)

    def test_the_page_carries_every_option_of_its_questions(self):
        """The prefetch brings the whole set of options of each question, none missing."""
        page = self.client.get(QUESTIONS).json()["results"]
        self.assertEqual(len(page), 5)
        for question in page:
            stored = Choice.objects.filter(question_id=question["id"]).count()
            self.assertEqual(len(question["choices"]), stored, f"question #{question['id']}")

    def test_the_second_page_costs_the_same_as_the_first(self):
        """Paging is not an excuse to query more."""
        with self.assertNumQueries(API_QUESTION_LIST):
            self.assertEqual(self.client.get(QUESTIONS, {"page": 2}).status_code, 200)

    def test_filtering_by_exam_costs_four_queries(self):
        """The «exam» filter narrows the rows, it does not add a query."""
        with self.assertNumQueries(API_QUESTION_LIST):
            self.assertEqual(self.client.get(QUESTIONS, {"exam": self.exam}).status_code, 200)

    def test_searching_costs_four_queries(self):
        """The «search» filter narrows the rows, it does not add a query."""
        with self.assertNumQueries(API_QUESTION_LIST):
            self.assertEqual(self.client.get(QUESTIONS, {"search": "prefetch"}).status_code, 200)

    def test_one_question_costs_three_queries(self):
        """GET /api/questions/<id>/ -> token + row (JOIN) + its options."""
        with self.assertNumQueries(API_QUESTION_DETAIL):
            self.assertEqual(self.client.get(f"{QUESTIONS}{self.question.id}/").status_code, 200)

    def test_the_exam_list_costs_three_queries(self):
        """GET /api/exams/ -> token + COUNT + rows with the question_count annotation."""
        with self.assertNumQueries(API_EXAM_LIST):
            self.assertEqual(self.client.get(EXAMS).status_code, 200)

    def test_the_exam_list_costs_the_same_with_thirty_more_exams(self):
        """32 exams instead of 2, still 3 queries: the counter is a JOIN, not one query per exam."""
        for index in range(30):
            Exam.objects.create(title=f"Examen {index:02d}")
        with self.assertNumQueries(API_EXAM_LIST):
            self.assertEqual(self.client.get(EXAMS).status_code, 200)

    def test_the_annotation_is_a_single_query_with_no_second_one_per_exam(self):
        """Counting the questions of 32 exams costs the same query that lists them."""
        for index in range(30):
            exam = Exam.objects.create(title=f"Examen {index:02d}")
            Question.objects.create(exam=exam, text="Una pregunta")
        with self.assertNumQueries(1):
            counts = {exam.title: exam.question_count for exam in queries.exams_with_counts()}
        self.assertEqual(counts["Examen 00"], 1)
        self.assertEqual(counts["Django · ORM"], 4)


class WebQueryCountTests(TestCase):
    """The screens pay the session (1 query) and the user (1 query) before any data."""

    def setUp(self):
        seed()
        self.exam = Exam.objects.first()
        self.web = Client()
        self.web.force_login(User.objects.get(username="profe"))

    def get(self, path, expected_queries):
        with self.assertNumQueries(expected_queries):
            response = self.web.get(path)
        self.assertEqual(response.status_code, 200)
        return response

    def test_the_exam_list_costs_four_queries(self):
        """Session + user + COUNT + the exams with their annotated counter."""
        self.get("/examenes/", 4)

    def test_the_exam_list_costs_the_same_with_nine_more_exams(self):
        for index in range(9):
            Exam.objects.create(title=f"Examen {index:02d}")
        self.get("/examenes/", 4)

    def test_the_exam_detail_costs_five_queries(self):
        """Session + user + the exam + its questions (1 query) + their options (1 query)."""
        self.get(f"/examenes/{self.exam.pk}/", 5)

    def test_the_exam_detail_costs_the_same_with_sixty_more_questions(self):
        """64 questions instead of 4, still 5 queries: prefetch_related is doing its job."""
        for index in range(60):
            question = Question.objects.create(exam=self.exam, text=f"Pregunta {index}")
            Choice.objects.create(question=question, text="a", is_correct=True)
            Choice.objects.create(question=question, text="b", is_correct=False)
        self.get(f"/examenes/{self.exam.pk}/", 5)

    def test_the_dashboard_costs_six_queries(self):
        """Session + user + the three counters (3 queries) + the five recent exams."""
        response = self.get("/", 6)
        self.assertEqual(response.context["totals"], {
            "exams": Exam.objects.count(),
            "questions": Question.objects.count(),
            "choices": Choice.objects.count(),
        })

    def test_the_dashboard_costs_the_same_with_more_data(self):
        for index in range(20):
            Question.objects.create(exam=self.exam, text=f"Pregunta {index}")
        self.get("/", 6)

    def test_an_anonymous_request_never_touches_the_database(self):
        """Sanity of the two previous numbers: without a session there is no session query.

        The login guard answers before looking at any data: 0 queries.
        """
        anonymous = Client()
        with self.assertNumQueries(0):
            self.assertEqual(anonymous.get("/examenes/").status_code, 302)


class QueryLayerTests(TestCase):
    """``quiz.queries`` measured on its own, without HTTP: the layer both presentations use."""

    def setUp(self):
        seed()
        self.exam = Exam.objects.first()

    def test_the_three_counters_are_three_queries(self):
        with self.assertNumQueries(3):
            totals = queries.totals()
        self.assertEqual(totals, {"exams": 2, "questions": 8, "choices": 32})

    def test_questions_with_choices_is_two_queries_however_many_there_are(self):
        """One query for the questions (with the exam JOINed) and one for all their options."""
        for index in range(40):
            question = Question.objects.create(exam=self.exam, text=f"Relleno {index}")
            Choice.objects.create(question=question, text="a", is_correct=True)
            Choice.objects.create(question=question, text="b", is_correct=False)
        with self.assertNumQueries(2):
            read = [(question.exam.title, len(question.choices.all())) for question in queries.questions_with_choices()]
        self.assertEqual(len(read), 48)
        self.assertEqual(sum(choices for _, choices in read), 32 + 80)

    def test_questions_with_choices_of_one_exam_does_not_query_more(self):
        with self.assertNumQueries(2):
            questions = list(queries.questions_with_choices(exam=self.exam))
        self.assertEqual(len(questions), 4)

    def test_an_exam_with_its_questions_is_three_queries(self):
        """The exams with their counter, their questions and all the options of those: 3 queries."""
        with self.assertNumQueries(3):
            read = [
                (exam.title, exam.question_count, sum(len(question.choices.all()) for question in exam.questions.all()))
                for exam in queries.exam_with_questions()
            ]
        self.assertEqual(read, [("Django · ORM", 4, 16), ("Django · Plantillas", 4, 16)])

    def test_an_exam_with_its_questions_costs_the_same_with_sixty_more_questions(self):
        """20 questions per exam instead of 4, still 3 queries."""
        for exam in queries.exams_with_counts():
            for index in range(16):
                question = Question.objects.create(exam=exam, text=f"Relleno {index}")
                Choice.objects.create(question=question, text="a", is_correct=True)
                Choice.objects.create(question=question, text="b", is_correct=False)
        with self.assertNumQueries(3):
            read = [exam.question_count for exam in queries.exam_with_questions()]
        self.assertEqual(read, [20, 20])