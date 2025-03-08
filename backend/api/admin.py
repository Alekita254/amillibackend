from django.contrib import admin
from .models import NewsletterSubscriber, ContactMessage

@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ('email', 'subscribed_at')  # Display these fields in the admin list view
    search_fields = ('email',)  # Enable searching by email
    list_filter = ('subscribed_at',)  # Add filtering options

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'submitted_at')  # Show these fields in list view
    search_fields = ('name', 'email')  # Allow searching by name and email
    list_filter = ('submitted_at',)  # Filter messages by submission date
    readonly_fields = ('submitted_at',)  # Prevent editing of submission date
