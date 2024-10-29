"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import SimpleRouter

from apps.common.views import AdminSpectacularSwaggerView, AdminSpectacularAPIView, AdminSpectacularRedocView
from apps.users.views import UserViewSet
from apps.tasks.views import TaskViewSet, CommentViewSet, TaskTimeLogViewSet, ElasticSearchViewSet

router = SimpleRouter()
router.register("users", UserViewSet, basename="users")
router.register("tasks", TaskViewSet, basename="tasks")
router.register("comments", CommentViewSet, basename="comments")
router.register("timelogs", TaskTimeLogViewSet, basename="timelogs")
router.register("elasticsearch", ElasticSearchViewSet, basename="elasticsearch")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("common/", include("apps.common.urls")),
    path("accounts/", include("allauth.urls")),
]

urlpatterns += router.urls

urlpatterns.extend(
    [
        path("", AdminSpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
        path("schema", AdminSpectacularAPIView.as_view(), name="schema"),
        path("redoc", AdminSpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    ]
)
