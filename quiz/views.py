from django.db.models import Count
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import filters, viewsets
from rest_framework.exceptions import ValidationError

from .models import Exam, Question
from .serializers import ExamSerializer, QuestionSerializer

MAX_ID = 2**63 - 1  # the largest id a SQLite autoincrement ever gives


def exam_filter_id(raw: str) -> int:
    """The exam id of the «exam» filter, or a 400 that says what a valid value is.

    ``"²".isdigit()`` is True while ``int("²")`` raises, so the old ``isdigit()``
    check answered a 500. And a filter that is not an id used to be ignored in
    silence, returning every question as if the caller had asked for all of them.
    Both are mistakes of the caller, and the answer that helps is a 400 naming the
    parameter: never a 500 and never a list the caller did not ask for.
    """
    value = (raw or "").strip()
    if not value.isascii() or not value.isdecimal():
        raise ValidationError({"exam": "Expected the id of an exam, for example ?exam=1."})
    number = int(value)
    if not 1 <= number <= MAX_ID:
        raise ValidationError({"exam": "Expected the id of an exam: it must be a positive whole number."})
    return number


class ExamViewSet(viewsets.ModelViewSet):
    serializer_class = ExamSerializer
    queryset = Exam.objects.annotate(question_count=Count("questions")).order_by("id")


@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter(
                "exam",
                int,
                description="Solo las preguntas de este examen. Un valor que no sea un id "
                "entra como 400 nombrando el parámetro.",
            ),
        ]
    )
)
class QuestionViewSet(viewsets.ModelViewSet):
    serializer_class = QuestionSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["text"]

    def get_queryset(self):
        queryset = Question.objects.select_related("exam").prefetch_related("choices")
        exam = self.request.query_params.get("exam")
        if exam is not None:
            queryset = queryset.filter(exam_id=exam_filter_id(exam))
        return queryset
