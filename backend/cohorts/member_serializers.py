from rest_framework import serializers

from .models import CohortMembership


class ProfileSerializer(serializers.ModelSerializer):
    """The only fields a member may change about themselves. Role, status, mentor, notes and email are not here."""

    class Meta:
        model = CohortMembership
        fields = [
            "full_name", "phone", "location", "headline",
            "about", "expertise", "linkedin", "show_publicly",
        ]


def _person(m):
    # What a mentor and their mentee may see of each other. Never phone or LinkedIn.
    return {"full_name": m.full_name, "headline": m.headline, "about": m.about, "email": m.email}


def _date(d):
    return d.isoformat() if d else None


def membership_payload(m):
    """One card of 'My cohort', computed live so approvals and reassignments show on the next load."""
    M = CohortMembership
    mentor, mentees = None, []
    if m.status == M.STATUS_APPROVED:
        if (
            m.role == M.ROLE_MENTEE and m.mentor_id
            and m.mentor.role == M.ROLE_MENTOR and m.mentor.status == M.STATUS_APPROVED
        ):
            mentor = _person(m.mentor)
        if m.role == M.ROLE_MENTOR:
            mentees = [
                _person(x)
                for x in m.mentees.filter(role=M.ROLE_MENTEE, status=M.STATUS_APPROVED).order_by("full_name")
            ]
    cohort = m.cohort
    return {
        "id": m.id,
        "role": m.role,
        "status": m.status,
        "created_at": m.created_at,
        "decided_at": m.decided_at,
        "cohort": {
            "title": cohort.title,
            "slug": cohort.slug,
            "status": cohort.status,
            "start_date": _date(cohort.start_date),
            "end_date": _date(cohort.end_date),
            "duration": cohort.duration,
        },
        "profile": ProfileSerializer(m).data,
        "mentor": mentor,
        "mentees": mentees,
    }
