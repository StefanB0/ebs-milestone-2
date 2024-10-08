from django.db import models

# Create your models here.


class Task(models.Model):
    title = models.CharField(max_length=255, unique=True)
    description = models.TextField()
    user = models.ForeignKey("User", on_delete=models.CASCADE)
    is_completed = models.BooleanField()

    def __str__(self) -> str:
        return self.title


class Comment(models.Model):
    body = models.TextField()
    task = models.ForeignKey(Task, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return self.body
