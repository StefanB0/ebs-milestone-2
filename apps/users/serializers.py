from django.contrib.auth.models import User
from rest_framework import serializers


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = (
            "first_name",
            "last_name",
            "username",
            "email",
            "password",
        )


class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = (
            "first_name",
            "last_name",
            "username",
            "email",
            "password",
        )
