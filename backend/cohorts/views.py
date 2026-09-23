from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from cohorts.models import Cohort
from cohorts.serializers import CohortSerializer
from api.utils import custom_response


class CohortListCreateView(generics.ListCreateAPIView):
    queryset = Cohort.objects.all()
    serializer_class = CohortSerializer
    permission_classes = [permissions.AllowAny]

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


class CohortDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Cohort.objects.all()
    serializer_class = CohortSerializer
    permission_classes = [permissions.AllowAny]

    def get_object(self):
        return get_object_or_404(Cohort, slug=self.kwargs["slug"])

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        return custom_response(
            success=True,
            message="Cohort retrieved successfully",
            data=response.data,
            status_code=status.HTTP_200_OK,
        )

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
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
