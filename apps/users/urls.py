from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from apps.users.views import RegisterUserView, UserListView, UserLoginView


# router = DefaultRouter()
# router.register("users", UserViewSet)

urlpatterns = [
    path("register", RegisterUserView.as_view(), name="token_register"),
    path("login", UserLoginView.as_view(), name="token_login"),
    path("list", UserListView.as_view(), name="user_list"),
    path("token/refresh", TokenRefreshView.as_view(), name="token_refresh"),
    # path("", include(router.urls)),
]
