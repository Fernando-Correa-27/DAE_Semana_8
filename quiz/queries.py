"""Reads of the quiz domain.

Both presentations ask this module for data, so a screen and the API never
disagree about which questions belong to an exam or how many there are. Every
list is built to keep the number of queries constant: the counter of an exam is
an annotation (a JOIN, not one query per row) and the children arrive in a
prefetch instead of being resolved while rendering (the classic N+1).
"""
from django.db.models import Count, Prefetch

from .models import Choice, Exam, Question

__all__ = ["exams_with_counts", "exam_with_questions", "questions_with_choices", "totals"]


def exams_with_counts():
    """Every exam ordered by id, each one carrying its number of questions."""
    return Exam.objects.annotate(question_count=Count("questions")).order_by("id")


def exam_with_questions():
    """One exam with its question counter and its questions already prefetched."""
    questions = Question.objects.prefetch_related("choices").order_by("id")
    return Exam.objects.annotate(question_count=Count("questions")).prefetch_related(
        Prefetch("questions", queryset=questions)
    )


def questions_with_choices(exam=None):
    """Questions with their exam and their options, optionally only one exam's."""
    queryset = Question.objects.select_related("exam").prefetch_related("choices").order_by("id")
    if exam is not None:
        queryset = queryset.filter(exam=exam)
    return queryset


def totals():
    """The three counters of the dashboard, in three queries."""
    return {
        "exams": Exam.objects.count(),
        "questions": Question.objects.count(),
        "choices": Choice.objects.count(),
    }