from elasticsearch_dsl import Document, Text, Boolean, Integer
from elasticsearch_dsl.aggs import Nested


class TaskDocument(Document):
    title = Text()
    description = Text()
    user_id = Text()
    is_completed = Boolean()
    time_spent = Integer()

    comments = Nested(properties={"id": Integer(), "body": Text(), "user_id": Text(), "username": Text()})

    class Index:
        name = "tasks"
