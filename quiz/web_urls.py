"""Routes of the web interface.

They live apart from ``quiz/urls.py`` on purpose: the API router and its OpenAPI
contract are not touched by anything that happens in the browser.
"""
from django.urls import path

from . import web_views

app_name = "quiz_ui"

urlpatterns = [
    path("", web_views.DashboardView.as_view(), name="dashboard"),
    path("acceso/", web_views.SignInView.as_view(), name="login"),
    path("salir/", web_views.sign_out, name="logout"),
    path("examenes/", web_views.ExamListView.as_view(), name="exam_list"),
    path("examenes/nuevo/", web_views.ExamCreateView.as_view(), name="exam_create"),
    path("examenes/<int:pk>/", web_views.ExamDetailView.as_view(), name="exam_detail"),
    path("examenes/<int:pk>/editar/", web_views.ExamUpdateView.as_view(), name="exam_update"),
    path("examenes/<int:pk>/eliminar/", web_views.ExamDeleteView.as_view(), name="exam_delete"),
    path(
        "examenes/<int:exam_pk>/preguntas/nuevo/",
        web_views.QuestionCreateView.as_view(),
        name="question_create",
    ),
    path("preguntas/<int:pk>/editar/", web_views.QuestionUpdateView.as_view(), name="question_update"),
    path(
        "preguntas/<int:pk>/eliminar/",
        web_views.QuestionDeleteView.as_view(),
        name="question_delete",
    ),
]