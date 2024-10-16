from django.contrib.auth.models import User
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.viewsets import GenericViewSet
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework import status


from apps.users.serializers import UserSerializer, UserRegisterSerializer, UserLoginSerializer


class UserViewSet(RetrieveModelMixin, ListModelMixin, GenericViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        fullname = f"{instance.first_name} {instance.last_name}"

        response_data = {
            "id": instance.id,
            "username": instance.username,
            "full name": fullname,
            "email": instance.email,
        }

        return Response(response_data)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        response_data = []
        for user in queryset:
            response_data.append(
                {
                    "id": user.id,
                    "username": user.username,
                    "full name": f"{user.first_name} {user.last_name}",
                    "email": user.email,
                }
            )

        return Response(response_data)

    @action(
        detail=False,
        methods=["POST"],
        url_path="register",
        url_name="register",
        serializer_class=UserRegisterSerializer,
        authentication_classes=[],
        permission_classes=[AllowAny],
    )
    def register(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        user = serializer.instance
        user.set_password(serializer.validated_data["password"])
        user.save()

        refresh = RefreshToken.for_user(user)

        response_data = {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }

        return Response(response_data, status=status.HTTP_201_CREATED)

    @action(
        detail=False,
        methods=["POST"],
        url_path="login",
        url_name="login",
        serializer_class=UserLoginSerializer,
        authentication_classes=[],
        permission_classes=[AllowAny],
    )
    def login(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        refresh = RefreshToken.for_user(user)

        response_data = {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }

        return Response(response_data)

    @action(
        detail=False,
        methods=["POST"],
        url_path="refresh",
        url_name="refresh",
        serializer_class=TokenRefreshSerializer,
        authentication_classes=[],
        permission_classes=[AllowAny],
    )
    def refresh(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        try:  # pragma: no cover # django rest framework
            serializer.is_valid(raise_exception=True)
        except TokenError as e:  # pragma: no cover # django rest framework
            raise InvalidToken(e.args[0])

        return Response(serializer.validated_data)
