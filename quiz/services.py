"""Business rules of the quiz, written ONCE so that every interface shares them.

The API (serializers), the console client (which only reads the contract) and any future
web interface must ask these functions instead of repeating the rules in their own code.
"""
from django.db import transaction

from .models import Choice, Question

AGENT_GROUP = "agente"

MIN_CHOICES = 2

PERSON, AGENT, READER, ANONYMOUS = "person", "agent", "reader", "anonymous"

READ_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
AGENT_METHODS = READ_METHODS | {"POST", "PUT", "PATCH"}
KNOWN_METHODS = AGENT_METHODS | {"DELETE"}

METHODS_BY_ROLE = {
    PERSON: KNOWN_METHODS,   # the person (teacher) may do everything, but only with real HTTP verbs
    AGENT: AGENT_METHODS,    # the agent may read, create and modify, but NEVER delete
    READER: READ_METHODS,    # anybody else logged in may only read
    ANONYMOUS: frozenset(),  # no identity, no access
}

ACTION_METHODS = {
    "list": "GET", "retrieve": "GET",
    "create": "POST", "update": "PUT", "partial_update": "PATCH", "destroy": "DELETE",
}


class QuizRuleError(Exception):
    """A rule of the quiz was broken. Its message is what the user reads."""


# --- roles and permissions -----------------------------------------------------------------------

def role_of(user) -> str:
    """Which role plays this user: person, agent, reader or anonymous."""
    if user is None or not getattr(user, "is_authenticated", False):
        return ANONYMOUS
    if getattr(user, "is_staff", False) or getattr(user, "is_superuser", False):
        return PERSON
    if is_agent(user):
        return AGENT
    return READER


def is_agent(user) -> bool:
    """Is this user a member of the agent group? An anonymous or unsaved user never is."""
    if user is None or not getattr(user, "is_authenticated", False) or not getattr(user, "pk", None):
        return False
    return user.groups.filter(name=AGENT_GROUP).exists()


def method_of(request, view=None) -> str:
    """The HTTP verb of the request, or the one its view action stands for."""
    method = getattr(request, "method", None)
    if method:
        return method.upper()
    return ACTION_METHODS.get(getattr(view, "action", None), "")


def may(role: str, method: str) -> bool:
    """May a role use this method? Unknown verbs are denied for everybody (deny by default)."""
    return str(method or "").upper() in METHODS_BY_ROLE.get(role, frozenset())


# --- the invariant of a question -----------------------------------------------------------------

def validate_question_choices(choice_dicts):
    """Check the two rules of a question: at least two choices and exactly one correct one."""
    choices = list(choice_dicts or [])
    if len(choices) < MIN_CHOICES:
        raise QuizRuleError("Una pregunta necesita al menos dos opciones.")
    if sum(1 for choice in choices if choice.get("is_correct")) != 1:
        raise QuizRuleError("Debe haber exactamente una opción correcta.")
    return choices


def _replace_choices(question, choice_dicts) -> None:
    """The choices sent replace the previous ones."""
    question.choices.all().delete()
    Choice.objects.bulk_create(
        Choice(question=question, text=choice.get("text", ""), is_correct=bool(choice.get("is_correct")))
        for choice in choice_dicts
    )


def create_question(exam, text, choice_dicts) -> Question:
    """Create a question with its choices, or nothing at all: it is one atomic step."""
    choices = validate_question_choices(choice_dicts)
    with transaction.atomic():
        question = Question.objects.create(exam=exam, text=text)
        _replace_choices(question, choices)
    return question


def update_question(question: Question, **fields) -> Question:
    """Update the fields given (exam, text and optionally choices) in one atomic step."""
    choices = fields.pop("choices", None)
    if choices is not None:
        validate_question_choices(choices)
    changed = []
    with transaction.atomic():
        for name in ("exam", "text"):
            if fields.get(name) is not None:
                setattr(question, name, fields.pop(name))
                changed.append(name)
        if changed:
            question.save(update_fields=changed)
        if choices is not None:
            _replace_choices(question, choices)
    return question