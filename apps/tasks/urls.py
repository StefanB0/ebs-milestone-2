from django.urls import path

from apps.tasks.views import TaskViewSet

urlpatterns = [
    path("users/<int:pk>/", TaskViewSet.as_view({"get": "user_tasks"}), name="tasks-user"),
]
