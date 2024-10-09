from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework import status

from apps.tasks.models import Task
from apps.tasks.serializers import TaskSerializer, TaskCreateSerializer, TaskUpdateSerializer, EmptySerializer
from rest_framework.response import Response

# Create your views here.


class TaskViewSet(ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Task.objects.filter(user=user)

    def create(self, request, *args, **kwargs):
        serializer = TaskCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=self.request.user)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        query_data = [{"id": instance.id, "title": instance.title} for instance in queryset]

        return Response(query_data)

        ###
        # s_list = super().list(request, *args, **kwargs)
        # list_data = [{"id": task["user"], "title": task["title"]} for task in s_list.data]

        # return Response(list_data)

    def retrieve(self, request, *args, **kwargs):
        s_retrieve = super().retrieve(request, *args, **kwargs)
        s_retrieve.data["id"] = s_retrieve.data["user"]

        return s_retrieve

    @action(detail=False, methods=["GET"], url_path="all")
    def all_tasks(self, request, *args, **kwargs):
        queryset = Task.objects.all()
        query_data = [{"id": instance.id, "title": instance.title} for instance in queryset]

        return Response(query_data)

    @action(detail=False, methods=["GET"], url_path="completed")
    def completed_tasks(self, request, *args, **kwargs):
        queryset = Task.objects.filter(is_completed=True, user=request.user)
        serializer = self.get_serializer(queryset, many=True)

        serializer_data = [{"id": task["user"], "title": task["title"]} for task in serializer.data]

        return Response(serializer_data)

    @action(detail=True, methods=["PATCH"], url_path="assign", serializer_class=TaskUpdateSerializer)
    def assign_task(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        queryset = Task.objects.all()

        serializer.is_valid(raise_exception=True)
        new_user = serializer.validated_data["user"]

        if new_user == request.user:
            return Response({"message": "Task already assigned to current user"}, status=400)

        task = queryset.get(id=kwargs["pk"])
        task.user = serializer.validated_data["user"]
        task.save()

        return Response({"message": "Task assigned successfully"})

    @action(detail=True, methods=["PATCH"], url_path="complete", serializer_class=EmptySerializer)
    def complete_task(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        task = queryset.get(id=kwargs["pk"])

        task.is_completed = True
        task.save()

        return Response({"message": "Task completed successfully"})