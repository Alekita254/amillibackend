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
        # Only a real change is checked: an unchanged value must not block saving other fields.
        if (self.instance and value is not None and value != self.instance.capacity
                and value < self.instance.seats_taken):
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


class RegistrationSerializer(serializers.ModelSerializer):
    """Public application. The cohort comes in through the serializer context."""

    class Meta:
        model = CohortMembership
        fields = [
            "role", "full_name", "email", "phone", "location",
            "headline", "about", "expertise", "linkedin", "show_publicly",
        ]

    def validate(self, attrs):
        cohort = self.context["cohort"]
        state = cohort.registration_state
        if state == "closed":
            raise serializers.ValidationError("Registration for this cohort is closed.")
        if state == "full" and attrs["role"] == CohortMembership.ROLE_MENTEE:
            raise serializers.ValidationError("This cohort is full.")
        if CohortMembership.objects.filter(cohort=cohort, email__iexact=attrs["email"].strip()).exists():
            raise serializers.ValidationError(DUPLICATE_MESSAGE)
        return attrs


DUPLICATE_MESSAGE = "You've already registered for this cohort with this email."


class PublicPersonSerializer(serializers.ModelSerializer):
    """What the public may see of a member. Never add contact details here."""

    class Meta:
        model = CohortMembership
        fields = ["id", "role", "full_name", "headline", "about"]


FULL_APPROVE_MESSAGE = "Cohort is full. Raise the capacity first."


class MembershipSerializer(serializers.ModelSerializer):
    """Staff view of a member. The cohort comes in through the serializer context."""

    mentor = serializers.PrimaryKeyRelatedField(
        queryset=CohortMembership.objects.all(), allow_null=True, required=False
    )
    mentor_name = serializers.SerializerMethodField()

    class Meta:
        model = CohortMembership
        fields = [
            "id", "role", "status", "full_name", "email", "phone", "location", "headline",
            "about", "expertise", "linkedin", "show_publicly", "mentor", "mentor_name",
            "admin_note", "created_at", "decided_at",
        ]
        read_only_fields = ["id", "created_at", "decided_at"]

    def get_mentor_name(self, obj):
        return obj.mentor.full_name if obj.mentor_id else None

    def validate(self, attrs):
        cohort, inst = self.context["cohort"], self.instance
        M = CohortMembership

        # A member added directly by staff is approved unless they say otherwise.
        if inst is None and "status" not in self.initial_data:
            attrs["status"] = M.STATUS_APPROVED

        role = attrs.get("role", inst.role if inst else None)
        status = attrs.get("status", inst.status if inst else None)

        if "email" in attrs:
            clash = M.objects.filter(cohort=cohort, email__iexact=attrs["email"].strip())
            if inst:
                clash = clash.exclude(pk=inst.pk)
            if clash.exists():
                raise serializers.ValidationError(DUPLICATE_MESSAGE)

        # Mentors don't have mentors; turning someone into a mentor drops theirs.
        if role == M.ROLE_MENTOR:
            if attrs.get("mentor"):
                raise serializers.ValidationError("Only mentees can have a mentor.")
            attrs["mentor"] = None

        mentor = attrs.get("mentor", inst.mentor if inst else None)
        if mentor and (
            mentor.cohort_id != cohort.id
            or mentor.role != M.ROLE_MENTOR
            or mentor.status != M.STATUS_APPROVED
        ):
            raise serializers.ValidationError("Mentor must be an approved mentor of this cohort.")

        # Capacity: only an approved mentee takes a seat.
        takes_seat = role == M.ROLE_MENTEE and status == M.STATUS_APPROVED
        had_seat = bool(inst) and inst.role == M.ROLE_MENTEE and inst.status == M.STATUS_APPROVED
        if takes_seat and not had_seat and cohort.capacity is not None and cohort.seats_taken >= cohort.capacity:
            raise serializers.ValidationError(FULL_APPROVE_MESSAGE)
        return attrs
