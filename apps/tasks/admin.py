from django.contrib import admin

from apps.tasks.models import Task, Comment

admin.site.register(Task)
admin.site.register(Comment)
