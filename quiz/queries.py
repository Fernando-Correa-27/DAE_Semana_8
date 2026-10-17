"""Reads of the quiz domain.

The web interface asks this module for the data it lists, so a screen keeps a
constant number of queries: the counter of an exam is an annotation (a JOIN, not
one query per row) and the children arrive in a prefetch instead of being resolved
while rendering (the classic N+1).
"""
from django.db.models import Count, Prefetch

from .models import Choice, Exam, Question

__all__ = ["exams_with_counts", "exam_with_questions", "questions_with_choices", "recent_exams", "totals"]


def exams_with_counts():
    """Every exam ordered by id, each one carrying its number of questions."""
    return Exam.objects.annotate(question_count=Count("questions")).order_by("id")


def recent_exams(limit=5):
    """The newest exams, each one carrying its number of questions."""
    return exams_with_counts().order_by("-id")[:limit]


def exam_with_questions():
    """One exam with its question counter and its questions already prefetched."""
    questions = Question.objects.prefetch_related("choices").order_by("id")
    return Exam.objects.annotate(question_count=Count("questions")).prefetch_related(
        Prefetch("questions", queryset=questions)
    )


def questions_with_choices(exam=None, text=None):
    """Questions with their exam and their options, narrowed by exam and/or by text."""
    queryset = Question.objects.select_related("exam").prefetch_related("choices").order_by("id")
    if exam is not None:
        queryset = queryset.filter(exam=exam)
    if text:
        queryset = queryset.filter(text__icontains=text.strip())
    return queryset


def totals():
    """The three counters of the dashboard, in three queries."""
    return {
        "exams": Exam.objects.count(),
        "questions": Question.objects.count(),
        "choices": Choice.objects.count(),
    }