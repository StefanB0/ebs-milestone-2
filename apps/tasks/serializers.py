from rest_framework import serializers

from apps.tasks.models import Task, Comment, TimeLog, TaskAttachment


class TaskSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="pk", read_only=True)
    time_spent = serializers.DurationField(read_only=True)

    class Meta:
        model = Task
        fields = ["id", "title", "description", "is_completed", "user", "time_spent"]
        extra_kwargs = {"user": {"default": serializers.CurrentUserDefault(), "read_only": True}}


class TaskPreviewSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="pk", read_only=True)
    time_spent = serializers.DurationField(read_only=True)

    class Meta:
        model = Task
        fields = ["id", "title", "time_spent"]


class TaskSearchSerializer(serializers.Serializer):
    search = serializers.CharField(max_length=255)


class TaskUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ["id", "user"]


class CommentSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="pk", read_only=True)

    class Meta:
        model = Comment
        fields = ["id", "body", "task", "user"]
        extra_kwargs = {"user": {"default": serializers.CurrentUserDefault(), "read_only": True}}


class TaskAttachmentSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="pk", read_only=True)

    class Meta:
        model = TaskAttachment
        fields = ["id", "image", "task"]


class TaskElasticSearchSerializer(serializers.Serializer):
    title = serializers.CharField(required=False, max_length=100)
    description = serializers.CharField(required=False, max_length=200)
    comment_body = serializers.CharField(required=False, max_length=200)
    limit = serializers.IntegerField(required=False, min_value=1, max_value=1000, default=20)


class TimeLogSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="pk", read_only=True)

    class Meta:
        model = TimeLog
        fields = ("id", "task", "start_time", "duration")


class TimeLogTopSerializer(serializers.Serializer):
    limit = serializers.IntegerField(default=20, min_value=1, required=False)
