from rest_framework import serializers
from .models import Cohort, CohortMembership


class CohortSerializer(serializers.ModelSerializer):
    # Counts come from approved members, never from typed numbers.
    learner_count = serializers.IntegerField(source="seats_taken", read_only=True)
    mentor_count = serializers.IntegerField(source="mentor_total", read_only=True)
    seats_taken = serializers.IntegerField(read_only=True)
    seats_left = serializers.IntegerField(read_only=True)
    registration_state = serializers.CharField(read_only=True)
    pending_count = serializers.SerializerMethodField()

    def get_pending_count(self, obj):
        return obj.memberships.filter(status=CohortMembership.STATUS_PENDING).count()

    def validate_capacity(self, value):
        if self.instance and value is not None and value < self.instance.seats_taken:
            raise serializers.ValidationError(
                f"Capacity can't be lower than the {self.instance.seats_taken} mentees already approved."
            )
        return value

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        if not (request and request.user.is_staff):
            data.pop("pending_count", None)  # applications are private
        return data

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
            "registration_open",
            "capacity",
            "registration_state",
            "seats_taken",
            "seats_left",
            "pending_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "slug", "created_at", "updated_at"]
