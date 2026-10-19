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

# The action each HTTP verb stands for in the browser interface. A verb that is not
# in this map is not an action of that interface, so it is denied to everybody.
WEB_ACTION_BY_METHOD = {
    "GET": "read", "HEAD": "read", "OPTIONS": "read",
    "POST": "create", "PUT": "modify", "PATCH": "modify", "DELETE": "delete",
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


def web_action(method: str) -> str:
    """What this HTTP verb means in the browser: read, create, modify, delete, or ""."""
    return WEB_ACTION_BY_METHOD.get(str(method or "").upper(), "")


def may_use(user, method: str) -> bool:
    """May this user perform this action from the browser interface?

    There is one table and one decision: the role comes from ``role_of``, so the
    browser asks exactly what the API asks and the two can never diverge (a
    superuser without ``is_staff`` is a person in both). The browser interface adds
    a single rule of its own (R-UI-07): it is private and it exists to manage
    content, so it is opened to the person and to nobody else. An unknown verb is
    denied to everybody: deny by default.
    """
    if not web_action(method):
        return False
    return role_of(user) == PERSON


# --- the invariant of a question -----------------------------------------------------------------

def validate_question_choices(choice_dicts):
    """Check the two rules of a question: at least two choices and exactly one correct one."""
    choices = list(choice_dicts or [])
    if len(choices) < MIN_CHOICES:
        raise QuizRuleError("Una pregunta necesita al menos dos opciones.")
    if sum(1 for choice in choices if choice.get("is_correct")) != 1:
        raise QuizRuleError("Debe haber exactamente una opción correcta.")
    return choices


def validate_option_write(question, is_correct: bool, choice=None) -> None:
    """Ask the same invariant when ONE option is written, instead of the whole list.

    ``validate_question_choices`` sees every option of a question at once, which is what
    a formset and the nested API can offer. The options endpoint writes a single row,
    so the rule is asked in its two halves: a correct option cannot join a question that
    already has one, and the only correct option of a question cannot stop being it.

    ``choice`` is the option being written, or ``None`` when it is being created. The
    decision belongs to the domain, so every interface gets the same answer and the same
    wording (ADR-0002).
    """
    others = question.choices.filter(is_correct=True)
    if choice is not None:
        others = others.exclude(pk=choice.pk)
    if is_correct and others.exists():
        raise QuizRuleError("Una pregunta no puede tener más de una opción correcta.")
    if not is_correct and choice is not None and choice.is_correct and not others.exists():
        raise QuizRuleError("Una pregunta necesita al menos una opción correcta.")


def validate_option_removal(choice) -> None:
    """Deleting an option is, for this invariant, exactly the same as unmarking it."""
    validate_option_write(choice.question, is_correct=False, choice=choice)


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