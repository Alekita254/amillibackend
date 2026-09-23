from django.contrib import admin
from cohorts.models import Cohort


@admin.register(Cohort)
class CohortAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "program_type", "featured", "published", "created_at")
    list_filter = ("status", "featured", "published", "program_type")
    search_fields = ("title", "slug", "program_type")
    prepopulated_fields = {"slug": ("title",)}
