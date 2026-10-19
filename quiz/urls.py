from rest_framework.routers import DefaultRouter

from .views import ExamViewSet, OptionViewSet, QuestionViewSet

router = DefaultRouter()
router.register("exams", ExamViewSet, basename="exam")
router.register("questions", QuestionViewSet, basename="question")
router.register("options", OptionViewSet, basename="option")

urlpatterns = router.urls
