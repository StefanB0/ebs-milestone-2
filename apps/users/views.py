from django.contrib.auth.models import User
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.viewsets import GenericViewSet
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework import status
from drf_spectacular.utils import extend_schema, inline_serializer

from rest_framework import serializers

from apps.users.serializers import UserSerializer, UserRegisterSerializer, UserLoginSerializer
from apps.common.permissions import ReadOnly


@extend_schema(
    responses=inline_serializer(
        name="abcd", fields={"refresh": serializers.CharField(), "access": serializers.CharField()}
    )
)
class RegisterUserView(GenericAPIView):
    serializer_class = UserRegisterSerializer
    permission_classes = (AllowAny,)
    authentication_classes = ()

    def post(self, request: Request) -> Response:
        #  Validate data
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        # Get password from validated data
        password = validated_data.pop("password")

        # Create user
        user = User.objects.create(
            **validated_data,
            is_superuser=True,
            is_staff=True,
        )

        # Set password
        user.set_password(password)
        user.save()

        refresh = RefreshToken.for_user(user)

        # ? Swagger doesnt display correct response fields
        return Response(
            {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            }
        )


class UserListView(GenericAPIView):
    serializer_class = UserSerializer
    permission_classes = (ReadOnly, IsAuthenticated)

    def get(self, request: Request) -> Response:
        users = User.objects.all()
        users_data = map(lambda user: {"id": user.id, "fullname": user.first_name + " " + user.last_name}, users)
        return Response(users_data)

class UserLoginView(GenericAPIView):
    serializer_class = UserLoginSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }, status=status.HTTP_200_OK)


class UserViewSet(RetrieveModelMixin, ListModelMixin, GenericViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    @action(
        detail=False,
        methods=["POST"],
        url_path="register",
        serializer_class=UserRegisterSerializer,
        authentication_classes=[],
        permission_classes=[AllowAny],
    )
    @extend_schema(
        responses=inline_serializer(
            name="abcd", fields={"refresh": serializers.CharField(), "access": serializers.CharField()}
        )
    )
    def register(self, request, *args, **kwargs):
        #  Validate data
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        # Get password from validated data
        password = validated_data.pop("password")

        # Create user
        user = User.objects.create(
            **validated_data,
            is_superuser=True,
            is_staff=True,
        )

        # Set password
        user.set_password(password)
        user.save()

        refresh = RefreshToken.for_user(user)

        # ? Swagger doesnt display correct response fields
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
        serializer_class=UserLoginSerializer,
        authentication_classes=[],
        permission_classes=[AllowAny],
    )
    def login(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=["POST"],
        url_path="refresh",
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
