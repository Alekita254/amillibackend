from rest_framework import serializers
from django.conf import settings
from urllib.parse import urljoin
from .models import NewsletterSubscriber, ContactMessage, Author, Blog

class NewsletterSubscriberSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewsletterSubscriber
        fields = ['id', 'email', 'subscribed_at']

class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ['id', 'name', 'email', 'message', 'submitted_at']

class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Author
        fields = ['id', 'name', 'email', 'bio', 'profile_picture']

# class BlogSerializer(serializers.ModelSerializer):
#     author = AuthorSerializer(read_only=True)
#     author_id = serializers.PrimaryKeyRelatedField(
#         queryset=Author.objects.all(), write_only=True
#     ) 

#     class Meta:
#         model = Blog
#         fields = ['id', 'title', 'description', 'content', 'cover_image', 'author', 'author_id', 'date', 'category', 'tags', 'slug', 'views']

class BlogSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(read_only=True)
    author_id = serializers.PrimaryKeyRelatedField(
        queryset=Author.objects.all(), write_only=True
    ) 
    cover_image = serializers.SerializerMethodField()

    class Meta:
        model = Blog
        fields = ['id', 'title', 'description', 'content', 'cover_image', 'author', 'author_id', 'date', 'category', 'tags', 'slug', 'views']

    def get_cover_image(self, obj):
        if obj.cover_image:
            image_url = obj.cover_image.url  # Get relative URL
            return urljoin(settings.SITE_DOMAIN, image_url.lstrip('/'))  # Force full URL
        return None
        
        