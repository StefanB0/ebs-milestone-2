import logging

from django.core.cache import cache
from django.contrib.auth import get_user_model
from drf_spectacular.openapi import OpenApiExample, OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiResponse, inline_serializer, OpenApiParameter
from elasticsearch_dsl.query import Q
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.parsers import FormParser, MultiPartParser

from rest_framework.viewsets import ModelViewSet, GenericViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status, mixins, serializers

from apps.tasks.documents import TaskDocument
from apps.tasks.exceptions import TimeLogError
from apps.tasks.models import Task, Comment, TimeLog, TaskAttachment
from apps.tasks.serializers import (
    TaskSerializer,
    TaskPreviewSerializer,
    TaskUpdateSerializer,
    TaskSearchSerializer,
    CommentSerializer,
    TimeLogSerializer,
    TimeLogTopSerializer,
    TaskAttachmentSerializer,
    TaskElasticSearchSerializer,
)
from apps.tasks.signals import task_comment, task_assigned, task_complete, task_undo

User = get_user_model()

logger = logging.getLogger("django")


class TaskViewSet(ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]
    queryset = Task.objects.all()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=self.request.user)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @extend_schema(responses={200: TaskPreviewSerializer})
    def list(self, request, *args, **kwargs):
        queryset = Task.objects.filter(user=request.user)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = TaskPreviewSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = TaskPreviewSerializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(responses={200: TaskPreviewSerializer(many=True)})
    @action(detail=False, methods=["GET"], url_path="all", url_name="all-tasks", serializer_class=TaskPreviewSerializer)
    def all_tasks(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    #
    @extend_schema(responses={200: TaskPreviewSerializer(many=True)})
    @action(detail=False, methods=["GET"], url_path="users/(?P<pk>[^/.]+)", url_name="user")
    def user_tasks(self, request, *args, **kwargs):
        user_id = self.kwargs.get("pk")
        if not User.objects.filter(id=user_id).exists():
            return Response(status=status.HTTP_404_NOT_FOUND)

        queryset = Task.objects.filter(user=user_id)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = TaskPreviewSerializer(queryset, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = TaskPreviewSerializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(responses={201: TaskPreviewSerializer(many=True)})
    @action(detail=False, methods=["GET"], url_path="completed")
    def completed_tasks(self, request, *args, **kwargs):
        queryset = Task.objects.filter(is_completed=True, user=request.user)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = TaskPreviewSerializer(queryset, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = TaskPreviewSerializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(responses={200: TaskPreviewSerializer(many=True)})
    @action(detail=False, methods=["GET"], url_path="incomplete")
    def incomplete_tasks(self, request, *args, **kwargs):
        queryset = Task.objects.filter(is_completed=False, user=request.user)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = TaskPreviewSerializer(queryset, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = TaskPreviewSerializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(responses={200: TaskPreviewSerializer(many=True)})
    @action(detail=False, methods=["POST"], url_path="search", serializer_class=TaskSearchSerializer)
    def search(self, request, *args, **kwargs):
        search_serializer = self.get_serializer(data=request.data)
        search_serializer.is_valid(raise_exception=True)
        queryset = Task.objects.filter(title__icontains=search_serializer.validated_data["search"])

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = TaskPreviewSerializer(queryset, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = TaskPreviewSerializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                examples=[OpenApiExample(name="0", value={"message": "Task assigned successfully"})],
            ),
            400: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                examples=[OpenApiExample(name="0", value={"error": "Cannot assign same user"})],
            ),
        }
    )
    @action(detail=True, methods=["PATCH"], url_path="assign", serializer_class=TaskUpdateSerializer)
    def assign_task(self, request, *args, **kwargs):
        if not Task.objects.filter(id=kwargs["pk"]).exists():
            return Response({"error": "Task does not exist"}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_user = serializer.validated_data["user"]

        task = Task.objects.get(id=kwargs["pk"])
        if task.user == new_user:
            return Response({"error": "Task already belongs to user"}, status=status.HTTP_400_BAD_REQUEST)

        task.assign_user(new_user)
        task_assigned.send(sender=None, user=new_user, task=task)
        return Response({"message": "Task assigned successfully"})

    @extend_schema(
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                examples=[
                    OpenApiExample(name="1", value={"message": "Task completed successfully"}),
                    OpenApiExample(name="2", value={"error": "Task already completed"}),
                ],
            )
        }
    )
    @action(detail=True, methods=["PATCH"], url_path="complete", serializer_class=serializers.Serializer)
    def complete_task(self, request, *args, **kwargs):
        if not Task.objects.filter(id=kwargs["pk"]).exists():
            return Response({"error": "Task does not exist"}, status=status.HTTP_404_NOT_FOUND)

        task = Task.objects.get(id=kwargs["pk"])
        if task.is_completed:
            return Response({"error": "Task already completed"}, status=status.HTTP_400_BAD_REQUEST)

        task.complete_task()
        task_complete.send(sender=self.__class__, task=task)
        return Response({"message": "Task completed successfully"}, status=status.HTTP_200_OK)

    @extend_schema(
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                examples=[
                    OpenApiExample(name="1", value={"message": "Task undone successfully"}),
                    OpenApiExample(name="2", value={"error": "Task not yet completed"}),
                ],
            )
        }
    )
    @action(detail=True, methods=["PATCH"], url_path="undo", serializer_class=serializers.Serializer)
    def undo_task(self, request, *args, **kwargs):
        if not Task.objects.filter(id=kwargs["pk"]).exists():
            return Response({"error": "Task does not exist"}, status=status.HTTP_404_NOT_FOUND)

        task = Task.objects.get(id=kwargs["pk"])
        if not task.is_completed:
            return Response({"error": "Task not yet completed"}, status=status.HTTP_400_BAD_REQUEST)

        task.undo_task()
        task_undo.send(sender=self.__class__, task=task)
        return Response({"message": "Task undone successfully"}, status=status.HTTP_200_OK)

    @extend_schema(
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                examples=[OpenApiExample(name="0", value=["comment 1", "comment 2", "comment 3"])],
            )
        }
    )
    @action(detail=True, methods=["GET"], pagination_class=LimitOffsetPagination, url_path="comments")
    def comments(self, request, *args, **kwargs):
        if not Task.objects.filter(id=kwargs["pk"]).exists():
            return Response({"error": "Task does not exist"}, status=status.HTTP_404_NOT_FOUND)

        queryset = Comment.objects.filter(task=kwargs["pk"])

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = CommentSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = CommentSerializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.OBJECT, examples=[OpenApiExample(name="0", value={"message": "Task started"})]
            ),
            403: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                examples=[OpenApiExample(name="0", value={"error": "Timer already started"})],
            ),
        }
    )
    @action(detail=True, methods=["PATCH"], url_path="start-timer", serializer_class=serializers.Serializer)
    def start_timer(self, request, *args, **kwargs):
        if not Task.objects.filter(id=kwargs["pk"]).exists():
            return Response({"error": "Task does not exist"}, status=status.HTTP_404_NOT_FOUND)

        task = Task.objects.get(id=kwargs["pk"])
        err = task.start_timer()
        if err:
            return Response({"message": err}, status=403)
        return Response({"message": "Task started"})

    @extend_schema(
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.OBJECT, examples=[OpenApiExample(name="0", value={"message": "Timer stopped"})]
            )
        }
    )
    @action(detail=True, methods=["PATCH"], url_path="stop-timer", serializer_class=serializers.Serializer)
    def stop_timer(self, request, *args, **kwargs):
        if not Task.objects.filter(id=kwargs["pk"]).exists():
            return Response({"error": "Task does not exist"}, status=status.HTTP_404_NOT_FOUND)

        task = Task.objects.get(id=kwargs["pk"])
        err = task.stop_timer()
        if err:
            return Response({"message": err}, status=403)
        serializer = TaskSerializer(task)
        return Response({"message": "Timer stopped", "time spent on task": serializer.data["time_spent"]}, status=200)

    @extend_schema(responses={200: TimeLogSerializer(many=True)})
    @action(detail=True, methods=["GET"], url_path="timer-logs", serializer_class=TimeLogSerializer)
    def timer_logs(self, request, *args, **kwargs):
        if not Task.objects.filter(id=kwargs["pk"]).exists():
            return Response({"error": "Task does not exist"}, status=status.HTTP_404_NOT_FOUND)

        task = Task.objects.get(id=kwargs["pk"])
        queryset = task.timelog_set.all()

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = TimeLogSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = TimeLogSerializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        request={
            "multipart/form-data": {"type": "object", "properties": {"image": {"type": "string", "format": "binary"}}}
        },
        responses={
            201: OpenApiResponse(
                OpenApiTypes.OBJECT, examples=[OpenApiExample(name="0", value={"attach_id": 0, "task_id": 0})]
            )
        },
    )
    @action(
        detail=True,
        methods=["POST"],
        parser_classes=[MultiPartParser, FormParser],
        serializer_class=TaskAttachmentSerializer,
    )
    def attachment(self, request, *args, **kwargs):
        task = self.get_object()
        request_data = request.data
        request_data["task"] = task.id
        serializer = TaskAttachmentSerializer(data=request_data)

        serializer.is_valid(raise_exception=False)
        instance = serializer.save()

        return Response({"attach_id": instance.id, "task_id": task.id}, status=status.HTTP_201_CREATED)

    @extend_schema(responses={200: TaskAttachmentSerializer(many=True)})
    @action(detail=True, methods=["GET"], serializer_class=TaskAttachmentSerializer)
    def attachments(self, request, *args, **kwargs):
        if not Task.objects.filter(id=kwargs["pk"]).exists():
            return Response({"error": "Task does not exist"}, status=status.HTTP_404_NOT_FOUND)

        queryset = TaskAttachment.objects.filter(task=kwargs["pk"])
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class CommentViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, mixins.UpdateModelMixin, GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = CommentSerializer
    queryset = Comment.objects.all()

    @extend_schema(
        request=CommentSerializer,
        responses={
            201: OpenApiResponse(
                response=inline_serializer(name="CommentIDResponse", fields={"comment_id": serializers.IntegerField()}),
            )
        },
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        task = serializer.validated_data["task"]

        comment = serializer.save(user=request.user)
        task_comment.send(sender=None, user=task.user, task=task, comment=comment)

        headers = self.get_success_headers(serializer.data)
        return Response({"comment_id": serializer.data["id"]}, status=status.HTTP_201_CREATED, headers=headers)


class TaskTimeLogViewSet(mixins.CreateModelMixin, GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = TimeLogSerializer

    @extend_schema(
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                examples=[
                    OpenApiExample(name="0", value={"message": "Time Log successfully created", "time_log_id": 0})
                ],
            ),
            403: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                examples=[
                    OpenApiExample(name="1", value={"message": "You are not authorized to log time for this task"}),
                    OpenApiExample(name="2", value={"error": "TimeLog overlaps with another timeLog"}),
                    OpenApiExample(name="3", value={"error": "Task timer is already running."}),
                ],
            ),
        }
    )
    def create(self, request, *args, **kwargs):
        if not Task.objects.filter(id=request.data["task"]).exists():
            return Response({"error": "Task does not exist"}, status=status.HTTP_400_BAD_REQUEST)

        log_user = Task.objects.get(id=request.data["task"]).user

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if log_user != request.user:
            return Response({"message": "You are not authorized to log time for this task"}, status=403)

        try:
            time_log = serializer.save()
        except TimeLogError as e:
            error_message = str(e).split(".")[0]
            return Response({"message": error_message}, status=403)

        headers = self.get_success_headers(serializer.data)

        return Response(
            {"message": "Time Log successfully created", "time_log_id": time_log.id},
            headers=headers,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.OBJECT, examples=[OpenApiExample(name="0", value={"month_time_spent": "0"})]
            )
        }
    )
    @action(detail=False, methods=["GET"], url_path="last-month", url_name="last-month")
    def last_month_logs(self, request, *args, **kwargs):
        user = request.user
        month_time_spent = TimeLog.user_time_last_month(user)
        return Response({"month_time_spent": month_time_spent})

    @extend_schema(responses={200: TimeLogSerializer(many=True)})
    @action(
        detail=False,
        methods=["GET"],
        url_path="top",
        url_name="top",
        serializer_class=TimeLogTopSerializer,
        pagination_class=None,
    )
    def top_logs(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        limit = serializer.validated_data.get("limit")
        cache_str = self.request.user.username + "month-top-logs" + f":{limit}"
        cached_logs = cache.get(cache_str)
        if cached_logs is not None:
            logger.debug("Used cached logs")
            top_logs = cached_logs
        else:
            top_logs = TimeLog.user_top_logs(request.user, limit)
            cache.set(cache_str, top_logs, timeout=60)

        response_serializer = TimeLogSerializer(top_logs, many=True)
        return Response(response_serializer.data)


class ElasticSearchViewSet(GenericViewSet):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="title",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Title of the task (optional)",
            ),
            OpenApiParameter(
                name="description",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Description of the task (optional)",
            ),
            OpenApiParameter(
                name="comment_body",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Body of comment associated with the task (optional)",
            ),
            OpenApiParameter(
                name="limit",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Length of the response (optional, defaults to 20)",
            ),
        ],
        responses={200: "Response schema or serializer here"},
    )
    @action(detail=False, methods=["GET"], url_path="task", url_name="task")
    def task_search(self, request, *args, **kwargs):
        serializer = TaskElasticSearchSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        title = validated_data.get("title")
        description = validated_data.get("description")
        comment_body = validated_data.get("comment_body")
        limit = validated_data.get("limit")

        if not limit:
            limit = 20

        queries = []
        if title:
            queries.append(Q("match", title=title))
        if description:
            queries.append(Q("match", description=description))
        if comment_body:
            queries.append(Q("nested", path="comments", query=Q("match", comments__body=comment_body)))

        if not queries:
            return Response({"error": "No query was provided"}, status=status.HTTP_400_BAD_REQUEST)

        search_query = Q("bool", must=queries)

        search = TaskDocument.search()
        search = search.query(search_query)
        search = search.extra(track_total_hits=True)
        search = search[: int(limit)]
        search_result = search.execute()

        search_results = [hit.to_dict() for hit in search_result]

        return Response(search_results)
