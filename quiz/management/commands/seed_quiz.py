from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand
from django.db import transaction
from rest_framework.authtoken.models import Token

from quiz import seed_data
from quiz.models import Choice, Exam, Question
from quiz.permissions import AGENT_GROUP


def ensure_users(password=None):
    """The person (staff) and the agent (group «agente»), each with a token. Idempotent:
    running the seed again keeps the same tokens, so the environment variables stay valid.

    ``password`` is optional on purpose: without it the behaviour is exactly the one of
    before (an unusable password, because the API does not use passwords). With it, the
    person gets a real password so the web interface has somebody to log in with."""
    group, _ = Group.objects.get_or_create(name=AGENT_GROUP)
    person, created = User.objects.get_or_create(username="profe", defaults={"is_staff": True})
    if created:
        person.set_unusable_password()
        person.save()
    if password:
        person.set_password(password)
        person.save(update_fields=["password"])
    agent, created = User.objects.get_or_create(username="agente")
    if created:
        agent.set_unusable_password()
        agent.save()
    agent.groups.add(group)
    return (
        Token.objects.get_or_create(user=person)[0].key,
        Token.objects.get_or_create(user=agent)[0].key,
    )


class Command(BaseCommand):
    help = (
        "Carga los datos fijos del laboratorio y crea los usuarios «profe» y «agente» con su "
        "token. Con --password fija además la contraseña de «profe» para poder entrar en la "
        "interfaz web (sin la opción, la contraseña queda inservible)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            help="Contraseña del usuario «profe» para la interfaz web. Sin esta opción no se toca.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        Exam.objects.all().delete()  # cascades to questions and choices
        for title, questions in seed_data.EXAMS:
            exam = Exam.objects.create(title=title)
            for text, choices in questions:
                question = Question.objects.create(exam=exam, text=text)
                Choice.objects.bulk_create(
                    Choice(question=question, text=t, is_correct=ok) for t, ok in choices
                )
        human, agent = ensure_users(options.get("password"))

        if options["verbosity"] > 0:
            self.stdout.write(self.style.SUCCESS(
                f"Listo: {Exam.objects.count()} exámenes, {Question.objects.count()} preguntas."
            ))
            self.stdout.write("\nTokens (solo para esta máquina; el de la persona es el que puede borrar):")
            self.stdout.write("  PowerShell:")
            self.stdout.write(f'    $env:QUIZ_TOKEN_HUMANO = "{human}"')
            self.stdout.write(f'    $env:QUIZ_TOKEN_AGENTE = "{agent}"')
            self.stdout.write("  Bash:")
            self.stdout.write(f"    export QUIZ_TOKEN_HUMANO={human}")
            self.stdout.write(f"    export QUIZ_TOKEN_AGENTE={agent}")
            if options.get("password"):
                self.stdout.write(
                    self.style.SUCCESS(
                        "\nContraseña de «profe» establecida: ya se puede entrar en la interfaz web."
                    )
                )
