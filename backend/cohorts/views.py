from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from cohorts.models import Cohort, CohortMembership
from cohorts.serializers import CohortSerializer, DUPLICATE_MESSAGE, RegistrationSerializer, PublicPersonSerializer, MembershipSerializer
from cohorts.emails import send_application_received, send_decision
from django.db import IntegrityError
from django.utils import timezone
from django.utils.functional import cached_property
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from api.permissions import IsStaffOrReadOnly
from api.utils import custom_response, error_response
from rest_framework.exceptions import ValidationError


class PublishedForPublicMixin:
    """Drafts (published=False) are visible to staff only."""

    def get_queryset(self):
        qs = Cohort.objects.all()
        return qs if self.request.user.is_staff else qs.filter(published=True)


class CohortListCreateView(PublishedForPublicMixin, generics.ListCreateAPIView):
    queryset = Cohort.objects.all()
    serializer_class = CohortSerializer
    permission_classes = [IsStaffOrReadOnly]

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return custom_response(
            success=True,
            message="Cohorts retrieved successfully",
            data=response.data,
            status_code=status.HTTP_200_OK,
        )

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        return custom_response(
            success=True,
            message="Cohort created successfully",
            data=response.data,
            status_code=status.HTTP_201_CREATED,
        )


class CohortDetailView(PublishedForPublicMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = Cohort.objects.all()
    serializer_class = CohortSerializer
    permission_classes = [IsStaffOrReadOnly]

    def get_object(self):
        return get_object_or_404(self.get_queryset(), slug=self.kwargs["slug"])

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        return custom_response(
            success=True,
            message="Cohort retrieved successfully",
            data=response.data,
            status_code=status.HTTP_200_OK,
        )

    def update(self, request, *args, **kwargs):
        try:
            response = super().update(request, *args, **kwargs)
        except ValidationError as exc:
            return error_response(exc)
        return custom_response(
            success=True,
            message="Cohort updated successfully",
            data=response.data,
            status_code=status.HTTP_200_OK,
        )

    def destroy(self, request, *args, **kwargs):
        super().destroy(request, *args, **kwargs)
        return custom_response(
            success=True,
            message="Cohort deleted successfully",
            data=None,
            status_code=status.HTTP_200_OK,
        )


class CohortRegisterView(APIView):
    """Public: apply to a cohort. Creates a PENDING membership for an admin to review."""

    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "email"

    def post(self, request, slug):
        cohort = get_object_or_404(Cohort, slug=slug, published=True)
        received = custom_response(
            success=True,
            message="Application received. We'll email you once it's reviewed.",
            status_code=status.HTTP_201_CREATED,
        )

        # Hidden field only bots fill in: pretend it worked, store nothing.
        if str(request.data.get("website", "")).strip():
            return received

        serializer = RegistrationSerializer(data=request.data, context={"cohort": cohort})
        try:
            serializer.is_valid(raise_exception=True)
            member = serializer.save(cohort=cohort)
        except ValidationError as exc:
            return error_response(exc)
        except IntegrityError:  # two identical submissions racing
            return error_response(ValidationError(DUPLICATE_MESSAGE))

        send_application_received(member)
        return received


class CohortPeopleView(generics.ListAPIView):
    """Public: approved members who chose to be shown (mentors first)."""

    serializer_class = PublicPersonSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None

    def get_queryset(self):
        cohort = get_object_or_404(Cohort, slug=self.kwargs["slug"], published=True)
        return cohort.memberships.filter(
            status=CohortMembership.STATUS_APPROVED, show_publicly=True
        ).order_by("-role", "full_name")  # "MENTOR" sorts after "MENTEE", so descending puts mentors first

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return custom_response(success=True, message="People retrieved successfully", data=response.data)


def _release_mentees_unless_mentor(member):
    """A member who is no longer an approved mentor can't keep mentees."""
    if not (member.role == CohortMembership.ROLE_MENTOR and member.status == CohortMembership.STATUS_APPROVED):
        CohortMembership.objects.filter(mentor=member).update(mentor=None)


class _CohortMembersMixin:
    """Staff-only, scoped to one cohort (drafts included)."""

    permission_classes = [permissions.IsAdminUser]
    pagination_class = None

    @cached_property
    def cohort(self):
        return get_object_or_404(Cohort, slug=self.kwargs["slug"])

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "cohort": self.cohort}

    def get_queryset(self):
        return self.cohort.memberships.select_related("mentor")


class CohortMemberListCreateView(_CohortMembersMixin, generics.ListCreateAPIView):
    serializer_class = MembershipSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        for param in ("role", "status"):
            value = self.request.query_params.get(param)
            if value:
                qs = qs.filter(**{param: value.upper()})
        return qs

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return custom_response(success=True, message="Members retrieved successfully", data=response.data)

    def create(self, request, *args, **kwargs):
        try:
            response = super().create(request, *args, **kwargs)
        except ValidationError as exc:
            return error_response(exc)
        return custom_response(
            success=True, message="Member added", data=response.data, status_code=status.HTTP_201_CREATED
        )

    def perform_create(self, serializer):
        member = serializer.save(cohort=self.cohort)
        if member.status in (CohortMembership.STATUS_APPROVED, CohortMembership.STATUS_REJECTED):
            member.decided_at = timezone.now()
            member.save(update_fields=["decided_at"])
        serializer.instance = member


class CohortMemberDetailView(_CohortMembersMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = MembershipSerializer

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        return custom_response(success=True, message="Member retrieved successfully", data=response.data)

    def update(self, request, *args, **kwargs):
        try:
            response = super().update(request, *args, **kwargs)
        except ValidationError as exc:
            return error_response(exc)
        return custom_response(success=True, message="Member updated successfully", data=response.data)

    def perform_update(self, serializer):
        before = serializer.instance.status
        member = serializer.save()
        if member.status != before and member.status in (
            CohortMembership.STATUS_APPROVED, CohortMembership.STATUS_REJECTED
        ):
            member.decided_at = timezone.now()
            member.save(update_fields=["decided_at"])
            send_decision(member)  # once per change; an unchanged status sends nothing
        _release_mentees_unless_mentor(member)

    def destroy(self, request, *args, **kwargs):
        super().destroy(request, *args, **kwargs)  # mentees keep their place; mentor FK is SET_NULL
        return custom_response(success=True, message="Member removed", data=None)
