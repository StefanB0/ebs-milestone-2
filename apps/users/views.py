from django.contrib.auth import get_user_model
from django.db.models import Sum, F

from apps.tasks.models import Task
from drf_spectacular.utils import extend_schema, OpenApiResponse, inline_serializer
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.viewsets import GenericViewSet
from rest_framework.decorators import action
from rest_framework import mixins
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework import status, serializers

from django.shortcuts import render

from apps.users.serializers import UserSerializer, UserRegisterSerializer, UserLoginSerializer, UserPreviewSerializer

User = get_user_model()


class UserViewSet(mixins.RetrieveModelMixin, mixins.ListModelMixin, mixins.UpdateModelMixin, GenericViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    @extend_schema(responses={200: UserPreviewSerializer})
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        fullname = f"{instance.first_name} {instance.last_name}"

        response_data = {
            "id": instance.id,
            "username": instance.username,
            "fullname": fullname,
            "email": instance.email,
        }

        return Response(response_data)

    @extend_schema(responses={200: UserPreviewSerializer(many=True)})
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        response_data = []
        for user in queryset:
            response_data.append(
                {
                    "id": user.id,
                    "username": user.username,
                    "fullname": f"{user.first_name} {user.last_name}",
                    "email": user.email,
                }
            )

        return Response(response_data)

    @extend_schema(
        request=UserRegisterSerializer,
        responses={
            201: OpenApiResponse(
                response=inline_serializer(
                    name="UserRegisterResponse",
                    fields={"refresh": serializers.CharField(), "access": serializers.CharField()},
                ),
            )
        },
    )
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
        serializer = self.get_serializer(data=request.data)
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

    @extend_schema(
        request=UserRegisterSerializer,
        responses={
            201: OpenApiResponse(
                response=inline_serializer(
                    name="UserLoginResponse",
                    fields={"refresh": serializers.CharField(), "access": serializers.CharField()},
                ),
            )
        },
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

        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:  # pragma: no cover # django rest framework
            raise InvalidToken(e.args[0])

        return Response(serializer.validated_data)

    @action(detail=False, url_path="profile", url_name="profile", permission_classes=[AllowAny])
    def profile(self, request, *args, **kwargs):
        return render(request, "profile.html", {"user": request.user})

    @action(detail=True, url_path="top-tasks", url_name="top-tasks")
    def top_tasks(self, request, *args, **kwargs):
        assert isinstance(F("time_all").desc, object)

        tasks = (
            Task.objects.filter(user=kwargs["pk"])
            .annotate(time_all=Sum("timelog__duration"))
            .order_by(F("time_all").desc(nulls_last=True))[:20]
        )
        return render(request, "tasks/tasks_email.html", {"tasks": tasks})
