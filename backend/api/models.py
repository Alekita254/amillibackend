from django.db import models
from django.utils.text import slugify

class Author(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    bio = models.TextField(blank=True)
    profile_picture = models.ImageField(upload_to='authors/', blank=True, null=True)

    def __str__(self):
        return self.name
    

class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email

class ContactMessage(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField()
    message = models.TextField()
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message from {self.name}"
    
class Blog(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    content = models.TextField()
    cover_image = models.ImageField(upload_to='blogs/', blank=True, null=True)
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name='blogs')
    date = models.DateTimeField(auto_now_add=True)
    category = models.CharField(max_length=100)
    tags = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title
    