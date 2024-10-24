from django.contrib import admin
from django.db.models import QuerySet

from apps.tasks.models import Task, Comment, TimeLog, TaskAttachment


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ["id", "title", "description", "user", "is_completed"]
    list_display_links = ["title"]
    search_fields = ["title", "description"]
    list_filter = ["is_completed"]
    actions = ["mark_completed", "mark_incomplete", "delete_time_logs"]

    @admin.action(description="Mark task as completed and email users")
    def mark_completed(self, request, queryset: QuerySet):
        for task in queryset:
            task.complete_task()

    @admin.action(description="Mark task as incomplete and email users")
    def mark_incomplete(self, request, queryset: QuerySet):
        queryset.update(is_completed=False)
        for task in queryset:
            task.unmark_task()

    @admin.action(description="Delete task time logs")
    def delete_time_logs(self, request, queryset: QuerySet):
        TimeLog.objects.filter(task__in=queryset).delete()


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ["id", "body", "task", "user"]
    list_display_links = ["body"]
    search_fields = ["body"]
    list_filter = ["task", "user"]


@admin.register(TaskAttachment)
class TaskAttachmentAdmin(admin.ModelAdmin):
    list_display = ["id", "task"]
    list_display_links = ["task"]
    search_fields = ["task__title"]
    list_filter = ["task"]


@admin.register(TimeLog)
class TimeLogAdmin(admin.ModelAdmin):
    list_display = ["task", "start_time", "duration"]
    search_fields = ["task"]
    list_filter = ["task"]

    @admin.action(description="Stop timer for time logs")
    def stop_time_logs(self, request, queryset: QuerySet):
        for time_log in queryset:
            time_log.stop()
