# Generated manually for cohorts app

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Cohort",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("slug", models.SlugField(blank=True, unique=True)),
                ("short_description", models.TextField(blank=True)),
                ("description", models.TextField(blank=True)),
                ("program_type", models.CharField(blank=True, max_length=120)),
                (
                    "status",
                    models.CharField(
                        choices=[("UPCOMING", "Upcoming"), ("ACTIVE", "Active"), ("COMPLETED", "Completed")],
                        default="UPCOMING",
                        max_length=20,
                    ),
                ),
                ("duration", models.CharField(blank=True, max_length=120)),
                ("start_date", models.DateField(blank=True, null=True)),
                ("end_date", models.DateField(blank=True, null=True)),
                ("learner_count", models.PositiveIntegerField(default=0)),
                ("mentor_count", models.PositiveIntegerField(default=0)),
                ("featured", models.BooleanField(default=False)),
                ("published", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
