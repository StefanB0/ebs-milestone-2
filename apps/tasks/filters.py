from django_filters import rest_framework as filters

from apps.tasks.models import Attachment


class AttachmentTaskFilter(filters.FilterSet):
    class Meta:
        model = Attachment
        fields = ["task"]
