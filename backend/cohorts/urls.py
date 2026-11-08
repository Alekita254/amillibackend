from django.urls import path
from cohorts.views import CohortListCreateView, CohortDetailView, CohortRegisterView, CohortPeopleView, CohortMemberListCreateView, CohortMemberDetailView

urlpatterns = [
    path("cohorts/", CohortListCreateView.as_view(), name="cohort-list-create"),
    path("cohorts/<slug:slug>/", CohortDetailView.as_view(), name="cohort-detail"),
    path("cohorts/<slug:slug>/register/", CohortRegisterView.as_view(), name="cohort-register"),
    path("cohorts/<slug:slug>/people/", CohortPeopleView.as_view(), name="cohort-people"),
    path("cohorts/<slug:slug>/members/", CohortMemberListCreateView.as_view(), name="cohort-members"),
    path("cohorts/<slug:slug>/members/<int:pk>/", CohortMemberDetailView.as_view(), name="cohort-member"),
]
