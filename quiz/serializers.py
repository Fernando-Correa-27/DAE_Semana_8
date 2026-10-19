from rest_framework import serializers

from .models import Choice, Exam, Question
from .services import (
    QuizRuleError,
    create_question,
    update_question,
    validate_option_write,
    validate_question_choices,
)


class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ["id", "text", "is_correct"]


class OptionSerializer(serializers.ModelSerializer):
    """An option as a resource of its own: the question travels as an identifier.

    The nested ``ChoiceSerializer`` above is what travels inside a question and stays
    untouched; this one is the standalone representation of the same model.
    """

    question = serializers.PrimaryKeyRelatedField(queryset=Question.objects.all())

    class Meta:
        model = Choice
        fields = ["id", "question", "text", "is_correct"]
        read_only_fields = ["id"]

    def validate(self, attrs):
        question = attrs.get("question") or getattr(self.instance, "question", None)
        is_correct = attrs.get("is_correct", getattr(self.instance, "is_correct", False))
        try:
            validate_option_write(question, is_correct, self.instance)
        except QuizRuleError as exc:
            raise serializers.ValidationError({"is_correct": str(exc)}) from exc
        return attrs


class ExamSerializer(serializers.ModelSerializer):
    question_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Exam
        fields = ["id", "title", "created_at", "question_count"]
        read_only_fields = ["created_at"]


class QuestionSerializer(serializers.ModelSerializer):
    # Choices travel nested inside the question; the exam travels as an identifier.
    choices = ChoiceSerializer(many=True)

    class Meta:
        model = Question
        fields = ["id", "exam", "text", "choices", "created_at"]
        read_only_fields = ["created_at"]

    def validate_choices(self, value):
        try:
            return validate_question_choices(value)
        except QuizRuleError as exc:
            raise serializers.ValidationError(str(exc)) from exc

    def create(self, validated_data):
        return create_question(validated_data["exam"], validated_data["text"], validated_data["choices"])

    def update(self, instance, validated_data):
        return update_question(instance, choices=validated_data.pop("choices", None), **validated_data)
