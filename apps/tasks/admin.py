from django.contrib import admin

from apps.tasks.models import Task, Comment, TimeLog

# admin.site.register(Task)
# admin.site.register(Comment)
# admin.site.register(TimeLog)


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ["id", "title", "description", "user", "is_completed"]
    list_display_links = ["title"]
    search_fields = ["title", "description"]
    list_filter = ["is_completed"]


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ["id", "body", "task", "user"]
    list_display_links = ["body"]
    search_fields = ["body"]
    list_filter = ["task", "user"]


@admin.register(TimeLog)
class TimeLogAdmin(admin.ModelAdmin):
    list_display = ["task", "start_time", "duration"]
    search_fields = ["task"]
    list_filter = ["task"]
