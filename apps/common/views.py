from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
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
