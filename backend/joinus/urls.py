from django.urls import path
from .views import JoinUsConfigView, JoinUsSubmissionView

urlpatterns = [
    path('config/', JoinUsConfigView.as_view(), name='joinus-config'),
    path('submit/', JoinUsSubmissionView.as_view(), name='joinus-submit'),
]

