from django.contrib import admin
from apps.users.models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ["id", "email", "first_name", "last_name", "username", "is_active", "is_staff", "is_superuser"]
    list_display_links = ["email"]
    search_fields = ["id", "email"]
    list_filter = ["is_staff", "is_superuser"]
