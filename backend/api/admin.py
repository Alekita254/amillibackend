from django.contrib import admin
from .models import NewsletterSubscriber, ContactMessage, Author, Blog, Comment, Community

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
