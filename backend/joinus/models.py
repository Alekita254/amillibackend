from django.db import models

class JoinUsPageConfig(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    highlights = models.TextField(help_text="Add highlights separated by line breaks")
    thank_you_message = models.TextField()

    def get_highlights_list(self):
        return self.highlights.splitlines()


class JoinUsSubmission(models.Model):
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    location = models.CharField(max_length=100, blank=True)
    area_of_interest = models.CharField(max_length=100)
    about = models.TextField()
    contribution = models.TextField()
    resume = models.FileField(upload_to='resumes/', blank=True, null=True)
    linkedin = models.URLField(blank=True)
    heard_from = models.CharField(max_length=100, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
