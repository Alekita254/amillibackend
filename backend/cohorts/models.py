from django.db import models
from api.utils import unique_slug


class Cohort(models.Model):
    STATUS_UPCOMING = "UPCOMING"
    STATUS_ACTIVE = "ACTIVE"
    STATUS_COMPLETED = "COMPLETED"

    STATUS_CHOICES = [
        (STATUS_UPCOMING, "Upcoming"),
        (STATUS_ACTIVE, "Active"),
        (STATUS_COMPLETED, "Completed"),
    ]

    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    short_description = models.TextField(blank=True)
    description = models.TextField(blank=True)
    program_type = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_UPCOMING)
    duration = models.CharField(max_length=120, blank=True)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    learner_count = models.PositiveIntegerField(default=0)
    mentor_count = models.PositiveIntegerField(default=0)
    featured = models.BooleanField(default=False)
    published = models.BooleanField(default=False)
    registration_open = models.BooleanField(default=False)
    capacity = models.PositiveIntegerField(blank=True, null=True, help_text="Mentee seats. Empty = no limit.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self, self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    def _approved(self, role):
        return self.memberships.filter(role=role, status=CohortMembership.STATUS_APPROVED).count()

    @property
    def seats_taken(self):
        return self._approved(CohortMembership.ROLE_MENTEE)

    @property
    def mentor_total(self):
        return self._approved(CohortMembership.ROLE_MENTOR)

    @property
    def seats_left(self):
        if self.capacity is None:
            return None
        return max(self.capacity - self.seats_taken, 0)

    @property
    def registration_state(self):
        if not self.published or not self.registration_open or self.status == self.STATUS_COMPLETED:
            return "closed"
        if self.seats_left == 0:
            return "full"
        return "open"


class CohortMembership(models.Model):
    ROLE_MENTEE = "MENTEE"
    ROLE_MENTOR = "MENTOR"
    ROLE_CHOICES = [(ROLE_MENTEE, "Mentee"), (ROLE_MENTOR, "Mentor")]

    STATUS_PENDING = "PENDING"
    STATUS_APPROVED = "APPROVED"
    STATUS_REJECTED = "REJECTED"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
    ]

    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE, related_name="memberships")
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    full_name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    location = models.CharField(max_length=100, blank=True)
    headline = models.CharField(max_length=150, blank=True, help_text="Public title, e.g. Backend developer")
    about = models.TextField(max_length=2000)
    expertise = models.TextField(max_length=1000, blank=True)
    linkedin = models.URLField(blank=True)
    show_publicly = models.BooleanField(default=False)
    mentor = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="mentees"
    )
    admin_note = models.TextField(max_length=2000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["cohort", "email"], name="uniq_cohort_email"),
        ]

    def save(self, *args, **kwargs):
        self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.full_name} ({self.get_role_display()}, {self.cohort})"


class LoginLink(models.Model):
    """A one-time sign-in link. Only the SHA-256 of the token is stored."""

    email = models.EmailField(db_index=True)
    token_hash = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Sign-in link for {self.email}"
