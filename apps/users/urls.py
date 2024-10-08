from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework.routers import DefaultRouter

from apps.users.views import RegisterUserView, UserListView, UserViewSet


router = DefaultRouter()
router.register("users", UserViewSet)

urlpatterns = [
    path("register", RegisterUserView.as_view(), name="token_register"),
    path("login", TokenObtainPairView.as_view(), name="token_login"),
    path("list", UserListView.as_view(), name="user_list"),
    path("token/refresh", TokenRefreshView.as_view(), name="token_refresh"),
    path("", include(router.urls)),
]
