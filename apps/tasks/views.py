from rest_framework.viewsets import ModelViewSet, GenericViewSet
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status, mixins

from django.core.mail import send_mail

from apps.tasks.models import Task, Comment
from apps.tasks.serializers import TaskSerializer, TaskCreateSerializer, TaskUpdateSerializer, TaskSearchSerializer, CommentSerializer, EmptySerializer

# Create your views here.


class TaskViewSet(ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]
    queryset = Task.objects.all()

    def create(self, request, *args, **kwargs):
        serializer = TaskCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=self.request.user)
        headers = self.get_success_headers(serializer.data)
        task_id = serializer.instance.id
        return Response({"task_id": task_id}, status=status.HTTP_201_CREATED, headers=headers)

    def list(self, request, *args, **kwargs):
        queryset = Task.objects.filter(user=request.user)

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
        task = Task.objects.get(id=kwargs["pk"])

        retrieve_data = {
            "id": task.id,
            **s_retrieve.data
        }


        return Response(retrieve_data)

    @action(detail=False, methods=["GET"], url_path="all", url_name="all-tasks")
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

    @action(detail=False, methods=["POST"], url_path="search", serializer_class=TaskSearchSerializer)
    def search(self, request, *args, **kwargs):
        search_serializer = self.get_serializer(data=request.data)
        search_serializer.is_valid(raise_exception=True)
        queryset = Task.objects.filter(title__icontains=search_serializer.validated_data["search"], user=request.user)
        serializer = TaskSerializer(queryset, many=True)

        response_data = [{"id": task["user"], "title": task["title"]} for task in serializer.data]
        return Response(response_data)

    @action(detail=True, methods=["PATCH"], url_path="assign", serializer_class=TaskUpdateSerializer)
    def assign_task(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        queryset = Task.objects.all()

        serializer.is_valid(raise_exception=True)
        new_user = serializer.validated_data["user"]

        task = queryset.get(id=kwargs["pk"])
        old_user = task.user
        if old_user == new_user:
            return Response({"message": "Task assigned successfully"}, status=200)
        
        task.user = serializer.validated_data["user"]
        task.save()

        send_mail(
            subject="Task assigned",
            message=f"Task [{task.title}] has been assigned to you",
            from_email="from@example.com",
            recipient_list=[new_user.email],
            fail_silently=False,
        )

        return Response({"message": "Task assigned successfully"})

    @action(detail=True, methods=["PATCH"], url_path="complete", serializer_class=EmptySerializer)
    def complete_task(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        task = queryset.get(id=kwargs["pk"])

        if task.is_completed:
            return Response({"message": "Task completed successfully"}, status=200)

        task.is_completed = True
        task.save()

        send_mail(
            subject="Task completed",
            message=f"Task [{task.title}] has been completed",
            from_email="from@example.com",
            recipient_list=[task.user.email],
            fail_silently=False,
        )

        comments = Comment.objects.filter(task=task)
        for comment in comments:
            send_mail(
                subject="Task completed",
                message=f"Task [{task.title}] has been completed",
                from_email="from@example.com",
                recipient_list=[comment.user.email],
                fail_silently=False,
            )

        return Response({"message": "Task completed successfully"})


    @action(detail=True, methods=["GET"], url_path="comments")
    def comments(self, request, *args, **kwargs):
        comments = Comment.objects.filter(task=kwargs["pk"])
        # serializer = CommentSerializer(comments, many=True)

        response_data = [comment.body for comment in comments]
        return Response(response_data)

class CommentViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = CommentSerializer

    def get_queryset(self):
        user = self.request.user
        return Comment.objects.filter(task__user=user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        task = serializer.validated_data["task"]
        send_mail(
            subject="Comment added",
            message=f"Comment added to task [{task.title}]",
            from_email="example@mail.com",
            recipient_list=[task.user.email],
            fail_silently=False,
        )

        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response({"comment_id": serializer.data["id"]}, status=status.HTTP_201_CREATED, headers=headers)