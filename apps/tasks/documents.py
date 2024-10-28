from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl.registries import registry

from apps.tasks.models import Task, Comment
from apps.users.models import User


@registry.register_document
class TaskDocument(Document):
    user = fields.ObjectField(
        properties={
            "email": fields.TextField(),
        }
    )

    comments = fields.NestedField(
        properties={
            "body": fields.TextField(),
        }
    )

    class Index:
        name = "tasks"
        settings = {"number_of_shards": 1, "number_of_replicas": 0}

    class Django:
        model = Task

        fields = ["title", "description", "is_completed"]
        related_models = [Comment, User]

    def get_instances_from_related(self, related_instance):
        if isinstance(related_instance, User):
            return related_instance.task_set.all()
        elif isinstance(related_instance, Comment):
            return related_instance.task
