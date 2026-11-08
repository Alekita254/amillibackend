from django.urls import path
from cohorts.views import CohortListCreateView, CohortDetailView, CohortRegisterView

urlpatterns = [
    path("cohorts/", CohortListCreateView.as_view(), name="cohort-list-create"),
    path("cohorts/<slug:slug>/", CohortDetailView.as_view(), name="cohort-detail"),
    path("cohorts/<slug:slug>/register/", CohortRegisterView.as_view(), name="cohort-register"),
]
