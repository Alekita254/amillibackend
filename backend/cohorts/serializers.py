from rest_framework import serializers
from .models import Cohort


class CohortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cohort
        fields = [
            "id",
            "title",
            "slug",
            "short_description",
            "description",
            "program_type",
            "status",
            "duration",
            "start_date",
            "end_date",
            "learner_count",
            "mentor_count",
            "featured",
            "published",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "slug", "created_at", "updated_at"]
