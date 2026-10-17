"""Views of the web interface.

They are Django views on purpose: this module does not belong to DRF and does
not touch ``quiz/views.py``. Their only way to write a question is
``quiz.services``: the invariant of the options is not repeated here.
"""
from django.contrib import messages
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)

from . import queries, services
from .forms import ChoiceFormSetFactory, ExamForm, QuestionForm
from .models import Exam, Question
from .web_mixins import StaffRequiredMixin, SuccessMessageMixin

PAGE_SIZE = 10
FORM_PREFIX = "choices"


class SignInView(LoginView):
    """The only entry point of the interface: a Django session, never a token."""

    template_name = "quiz/login.html"
    redirect_authenticated_user = True


sign_out = LogoutView.as_view()


class DashboardView(StaffRequiredMixin, TemplateView):
    """Landing page: how much there is and where to start."""

    template_name = "quiz/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["totals"] = queries.totals()
        context["recent_exams"] = queries.exams_with_counts()[:5]
        return context


class ExamListView(StaffRequiredMixin, ListView):
    """All exams, each with its number of questions."""

    model = Exam
    context_object_name = "exams"
    template_name = "quiz/exam_list.html"
    paginate_by = PAGE_SIZE

    def get_queryset(self):
        return queries.exams_with_counts()


class ExamCreateView(StaffRequiredMixin, SuccessMessageMixin, CreateView):
    model = Exam
    form_class = ExamForm
    template_name = "quiz/exam_form.html"
    success_url = reverse_lazy("quiz_ui:exam_list")
    success_message = "Examen «{title}» creado."

    def get_success_context(self):
        return {"title": self.object.title}


class ExamUpdateView(StaffRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Exam
    form_class = ExamForm
    template_name = "quiz/exam_form.html"
    success_url = reverse_lazy("quiz_ui:exam_list")
    success_message = "Examen «{title}» actualizado."

    def get_success_context(self):
        return {"title": self.object.title}


class ExamDeleteView(StaffRequiredMixin, SuccessMessageMixin, DeleteView):
    """Deleting an exam takes its questions and options with it, so it asks first."""

    model = Exam
    template_name = "quiz/exam_confirm_delete.html"
    success_url = reverse_lazy("quiz_ui:exam_list")
    success_message = "Examen «{title}» eliminado."

    def get_success_context(self):
        return {"title": self.object.title}


class ExamDetailView(StaffRequiredMixin, DetailView):
    """One exam with all its questions, each with its options."""

    model = Exam
    template_name = "quiz/exam_detail.html"
    context_object_name = "exam"

    def get_queryset(self):
        return queries.exam_with_questions()


class QuestionFormView(StaffRequiredMixin, CreateView):
    """Common ground of creating and editing a question with its options.

    ``services`` does the writing, so the options of a question are always
    replaced as a whole and always with the invariant checked.
    """

    model = Question
    form_class = QuestionForm
    template_name = "quiz/question_form.html"

    def get_instance(self):
        """The question the options formset hangs from. A new one when creating."""
        return self.object or Question()

    def get_formset(self):
        """The options formset: bound to the posted data, or empty for a new form."""
        if self.request.method == "POST":
            return ChoiceFormSetFactory(self.request.POST, instance=self.get_instance(), prefix=FORM_PREFIX)
        return ChoiceFormSetFactory(instance=self.get_instance(), prefix=FORM_PREFIX)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["choices_formset"] = self.get_formset()
        context["exam_id"] = self.get_exam_id()
        return context

    def get_exam_id(self):
        """Which exam the screen belongs to. Needed by the links back to it."""
        raise NotImplementedError


class QuestionCreateView(QuestionFormView):
    def get_exam_id(self):
        return self.kwargs.get("exam_pk")

    def get_initial(self):
        """The exam comes from the URL, so the form opens with it chosen."""
        initial = super().get_initial()
        if "exam_pk" in self.kwargs:
            initial["exam"] = get_object_or_404(Exam, pk=self.kwargs["exam_pk"]).pk
        return initial

    def form_valid(self, form):
        formset = self.get_formset()
        if not formset.is_valid():
            return self.form_invalid(form)
        self.object = services.create_question(
            exam=form.cleaned_data["exam"],
            text=form.cleaned_data["text"],
            choice_dicts=formset.filled_choices(),
        )
        messages.success(self.request, "Pregunta creada.")
        return redirect("quiz_ui:exam_detail", pk=self.object.exam_id)


class QuestionUpdateView(QuestionFormView):
    """The object of the view is not enough: CreateView empties it on every POST."""

    def get_object(self, queryset=None):
        if getattr(self, "question", None) is None:
            self.question = get_object_or_404(queries.questions_with_choices(), pk=self.kwargs["pk"])
        return self.question

    def get_instance(self):
        return self.get_object()

    def get_exam_id(self):
        return self.get_object().exam_id

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["question"] = self.get_object()
        return context

    def form_valid(self, form):
        formset = self.get_formset()
        if not formset.is_valid():
            return self.form_invalid(form)
        question = self.get_object()
        services.update_question(
            question,
            exam=form.cleaned_data["exam"],
            text=form.cleaned_data["text"],
            choices=formset.filled_choices(),
        )
        messages.success(self.request, "Pregunta actualizada.")
        return redirect("quiz_ui:exam_detail", pk=question.exam_id)


class QuestionDeleteView(StaffRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Question
    template_name = "quiz/question_confirm_delete.html"
    success_message = "Pregunta eliminada."

    def get_queryset(self):
        return Question.objects.select_related("exam")

    def get_success_url(self):
        return reverse("quiz_ui:exam_detail", args=[self.object.exam_id])