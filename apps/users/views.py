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
        #  Validate data
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        user = serializer.instance
        user.set_password(serializer.validated_data["password"])
        user.save()

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            }
        )

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
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            },
            status=status.HTTP_200_OK,
        )

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

        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            raise InvalidToken(e.args[0])

        return Response(serializer.validated_data, status=status.HTTP_200_OK)
