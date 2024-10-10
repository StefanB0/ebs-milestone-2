from rest_framework import serializers

from apps.tasks.models import Task, Comment


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ["title", "description", "is_completed", "user"]


class TaskCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ["title", "description", "is_completed"]
        extra_kwargs = {
            "user": {"default": serializers.CurrentUserDefault(), "read_only": True}
        }


class TaskSearchSerializer(serializers.Serializer):
    search = serializers.CharField(max_length=255)

class TaskUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ["id", "user"]


class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = "__all__"


class EmptySerializer(serializers.Serializer):
    pass