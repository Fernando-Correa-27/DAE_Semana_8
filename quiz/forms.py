"""Forms of the web interface.

The rules of a question ("at least two options", "exactly one correct") are not
written here: they are asked to ``quiz.services.validate_question_choices``,
which is the single place where they live (ADR-0002). This module only decides
how the answer reaches the person: an error per field or a non-field error on
top of the rows.
"""
from django import forms
from django.core.exceptions import ValidationError
from django.forms.models import inlineformset_factory
from django.utils.translation import gettext_lazy as _

from . import services
from .models import Choice, Exam, Question

TEXTAREA_ATTRS = {"rows": 5}


class ExamForm(forms.ModelForm):
    """Create and edit an exam. One field, one label, no placeholder tricks."""

    class Meta:
        model = Exam
        fields = ["title"]
        labels = {"title": _("Título del examen")}
        widgets = {
            "title": forms.TextInput(
                attrs={"maxlength": 120, "autocomplete": "off", "placeholder": _("Ejemplo: Prueba 1 · Django")}
            )
        }
        help_texts = {"title": _("Hasta 120 caracteres.")}


class QuestionForm(forms.ModelForm):
    """Create and edit a question; the options travel in the formset below."""

    class Meta:
        model = Question
        fields = ["exam", "text"]
        labels = {"exam": _("Examen"), "text": _("Enunciado")}
        widgets = {
            "text": forms.Textarea(attrs={**TEXTAREA_ATTRS, "placeholder": _("Escribe aquí la pregunta")})
        }
        help_texts = {"text": _("Opcionalmente, añade el enunciado y sus opciones debajo.")}


class CorrectChoiceRadio(forms.CheckboxInput):
    """One radio button per option, all of them sharing a single ``name``.

    A browser only keeps one checked radio per name, so "exactly one correct
    option" becomes a property of the HTML itself and the page keeps working
    with JavaScript disabled. The row index travels as the value and
    ``ChoiceFormSet`` rebuilds ``is_correct`` from it, so the server never
    trusts the browser: the verdict comes from ``services``.
    """

    template_name = "quiz/widgets/correct_choice.html"

    def __init__(self, attrs=None):
        defaults = {"class": "choice-radio"}
        defaults.update(attrs or {})
        super().__init__(defaults)

    def get_context(self, name, value, attrs):
        # name, value and checked are rendered by the template, so they must not
        # travel inside attrs: the template writes them first and a duplicated
        # attribute would be ignored by the browser.
        return {
            "widget": {
                "type": "radio",
                "name": self.group_name,
                "value": self.row_index,
                "checked": bool(value),
                "attrs": self.build_attrs(self.attrs, attrs),
            }
        }

    group_name = ""
    row_index = 0


class ChoiceForm(forms.ModelForm):
    """A single option of a question: its text and whether it is the right one."""

    class Meta:
        model = Choice
        fields = ["text", "is_correct"]
        labels = {"text": _("Texto de la opción"), "is_correct": _("Correcta")}
        widgets = {
            "text": forms.TextInput(attrs={"maxlength": 200, "placeholder": _("Texto de la opción")}),
            "is_correct": CorrectChoiceRadio(),
        }


class ChoiceFormSet(forms.BaseInlineFormSet):
    """The options of a question, validated by the domain service.

    The rule is asked, not rewritten: whatever ``validate_question_choices``
    answers becomes a non-field error above the rows, exactly the same wording
    the API returns.
    """

    correct_field_name = ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.correct_field_name = f"{self.prefix}-correct"
        for index, form in enumerate(self.forms):
            widget = form.fields["is_correct"].widget
            widget.group_name = self.correct_field_name
            widget.row_index = index

    def filled_choices(self):
        """The options the person actually wrote, as the service wants them."""
        selected = self.data.get(self.correct_field_name)
        choices = []
        for index, form in enumerate(self.forms):
            if not form.cleaned_data or not form.cleaned_data.get("text", "").strip():
                continue
            choices.append(
                {
                    "text": form.cleaned_data["text"],
                    "is_correct": str(index) == selected,
                }
            )
        return choices

    def clean(self):
        super().clean()
        if any(self.errors):
            return
        try:
            services.validate_question_choices(self.filled_choices())
        except services.QuizRuleError as exc:
            raise ValidationError(str(exc)) from exc


ChoiceFormSetFactory = inlineformset_factory(
    Question,
    Choice,
    form=ChoiceForm,
    formset=ChoiceFormSet,
    extra=3,
    min_num=2,
    validate_min=False,  # the wording of "at least two" belongs to the service
    can_delete=False,
)