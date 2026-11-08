from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from cohorts.models import Cohort
from cohorts.serializers import CohortSerializer
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
