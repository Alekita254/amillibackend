from django.conf import settings
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.template.response import TemplateResponse
from django.urls import path
from .models import *

class CustomUserAdmin(UserAdmin):
    # Fields to display in the user list
    list_display = ('username', 'email', 'first_name', 'last_name', 'email_verified', 'is_staff')
    list_filter = ('email_verified', 'is_staff', 'is_superuser', 'is_active')
    
    # Fields shown when editing a user
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
        ('Verification', {'fields': ('email_verified',)}),
    )
    
    # Fields shown when creating a user
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2'),
        }),
    )
    
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('username',)
    filter_horizontal = ('groups', 'user_permissions',)

    def get_urls(self):
        return [
            path('send-test-email/', self.admin_site.admin_view(self.send_test_email), name='send_test_email'),
        ] + super().get_urls()

    def send_test_email(self, request):
        """Send a short test message through the real email settings, to check that delivery works."""
        sent_to = error = None
        if request.method == 'POST':
            user = request.user
            # Only superusers may pick another address; everyone else can only mail themselves.
            to = (request.POST.get('to', '').strip() if user.is_superuser else '') or user.email
            try:
                if not to:
                    raise ValueError('Your account has no email address. Add one to your user first.')
                validate_email(to)
                send_mail(
                    'Test email from A Million Techies',
                    f'If you can read this, sending email works.\n\nSent by {user.username} from the admin panel.',
                    settings.DEFAULT_FROM_EMAIL, [to], fail_silently=False,
                )
                sent_to = to
            except ValidationError:
                error = 'Enter a valid email address.'
            except Exception as e:  # show the SMTP problem instead of a 500; only staff can reach this page
                error = f'{type(e).__name__}: {e}'
        return TemplateResponse(request, 'admin/send_test_email.html', {
            **self.admin_site.each_context(request),
            'title': 'Send test email',
            'default_to': request.user.email,
            'can_choose': request.user.is_superuser,
            'sent_to': sent_to,
            'error': error,
            'from_email': settings.DEFAULT_FROM_EMAIL,
            'host': settings.EMAIL_HOST,
        })

# Register your custom User model with the custom admin class
admin.site.register(User, CustomUserAdmin)

@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ('email', 'subscribed_at')
    search_fields = ('email',)
    list_filter = ('subscribed_at',)

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'submitted_at')
    search_fields = ('name', 'email')
    list_filter = ('submitted_at',)  
    readonly_fields = ('submitted_at',)

@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ('name', 'email')
    search_fields = ('name', 'email')

@admin.register(Blog)
class BlogAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'date', 'category', 'slug')
    search_fields = ('title', 'author__name', 'category', 'tags')
    list_filter = ('date', 'category')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('date',)

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'blog', 'parent', 'created_at', 'likes', 'dislikes')
    search_fields = ('name', 'email', 'blog__title', 'message')
    list_filter = ('created_at', 'blog', 'parent')
    readonly_fields = ('created_at',)

    def get_queryset(self, request):
        # Optimize the queryset to reduce the number of database queries
        return super().get_queryset(request).select_related('blog', 'parent')
    
@admin.register(Community)
class CommunityAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'date', 'category', 'slug')
    search_fields = ('title', 'author__name', 'category', 'tags')
    list_filter = ('date', 'category')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('date',)
