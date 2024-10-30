from drf_spectacular.views import SpectacularSwaggerView, SpectacularAPIView, SpectacularRedocView
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status

from apps.common.helpers import EmptySerializer


class HealthView(GenericAPIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)
    serializer_class = EmptySerializer

    @staticmethod
    def get(request: Request) -> Response:
        return Response({"live": True}, status=status.HTTP_200_OK)


class ProtectedTestView(GenericAPIView):
    serializer_class = EmptySerializer

    @staticmethod
    def get(request: Request) -> Response:
        return Response({"live": True})


class AdminSpectacularSwaggerView(SpectacularSwaggerView):
    permission_classes = [IsAdminUser, IsAuthenticated]
    # SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    pass


class AdminSpectacularAPIView(SpectacularAPIView):
    permission_classes = [IsAdminUser, IsAuthenticated]
    # SpectacularAPIView.as_view(), name="schema"),
    pass


class AdminSpectacularRedocView(SpectacularRedocView):
    permission_classes = [IsAdminUser, IsAuthenticated]
    # SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    pass
