from django.contrib import admin
from cohorts.models import Cohort, CohortMembership


@admin.register(Cohort)
class CohortAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "program_type", "featured", "published", "created_at")
    list_filter = ("status", "featured", "published", "program_type")
    search_fields = ("title", "slug", "program_type")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(CohortMembership)
class CohortMembershipAdmin(admin.ModelAdmin):
    list_display = ("full_name", "email", "cohort", "role", "status", "show_publicly")
    list_filter = ("cohort", "role", "status")
    search_fields = ("full_name", "email")
