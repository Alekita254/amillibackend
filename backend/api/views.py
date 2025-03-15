from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.core.mail import send_mail
from .models import NewsletterSubscriber, ContactMessage, Author, Blog
from .serializers import NewsletterSubscriberSerializer, ContactMessageSerializer, AuthorSerializer, BlogSerializer
from .utils import custom_response 


class NewsletterSignupView(generics.CreateAPIView):
    queryset = NewsletterSubscriber.objects.all()
    serializer_class = NewsletterSubscriberSerializer
    permission_classes = [permissions.AllowAny] 

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        return custom_response(
            success=True,
            message="Successfully subscribed to the newsletter",
            data=response.data,
            status_code=status.HTTP_201_CREATED
        )

class ContactFormView(generics.CreateAPIView):
    queryset = ContactMessage.objects.all()
    serializer_class = ContactMessageSerializer
    permission_classes = [permissions.AllowAny] 

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        return custom_response(
            success=True,
            message="Your message has been received",
            data=response.data,
            status_code=status.HTTP_201_CREATED
        )

class SendCustomEmailView(APIView):
    
    permission_classes = [permissions.AllowAny] 

    def post(self, request):
        subject = request.data.get('subject')
        message = request.data.get('message')
        recipient_list = request.data.get('recipients', [])

        if not subject or not message or not recipient_list:
            return custom_response(
                success=False,
                message="Missing required fields",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        send_mail(subject, message, 'your_email@example.com', recipient_list)

        return custom_response(
            success=True,
            message="Email sent successfully"
        )


class AuthorListCreateView(generics.ListCreateAPIView):
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer
    permission_classes = [permissions.AllowAny] 

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return custom_response(
            success=True,
            message="Authors retrieved successfully",
            data=response.data
        )

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        return custom_response(
            success=True,
            message="Author created successfully",
            data=response.data,
            status_code=status.HTTP_201_CREATED
        )



class AuthorDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer
    permission_classes = [permissions.AllowAny] 

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        return custom_response(
            success=True,
            message="Author retrieved successfully",
            data=response.data
        )

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        return custom_response(
            success=True,
            message="Author updated successfully",
            data=response.data
        )

    def destroy(self, request, *args, **kwargs):
        super().destroy(request, *args, **kwargs)
        return custom_response(
            success=True,
            message="Author deleted successfully",
            data=None
        )


class BlogListCreateView(generics.ListCreateAPIView):
    queryset = Blog.objects.all()
    serializer_class = BlogSerializer
    permission_classes = [permissions.AllowAny] 

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return custom_response(
            success=True,
            message="Blogs retrieved successfully",
            data=response.data
        )

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        return custom_response(
            success=True,
            message="Blog created successfully",
            data=response.data,
            status_code=status.HTTP_201_CREATED
        )



class BlogDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Blog.objects.all()
    serializer_class = BlogSerializer
    permission_classes = [permissions.AllowAny] 

    def retrieve(self, request, *args, **kwargs):
        blog =self.get_object()
        blog.views += 1
        blog.save(update_fields=["views"])
        
        response = super().retrieve(request, *args, **kwargs)
        return custom_response(
            success=True,
            message="Blog retrieved successfully",
            data=response.data
        )

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        return custom_response(
            success=True,
            message="Blog updated successfully",
            data=response.data
        )

    def destroy(self, request, *args, **kwargs):
        super().destroy(request, *args, **kwargs)
        return custom_response(
            success=True,
            message="Blog deleted successfully",
            data=None
        )
    
class PopularBlogsView(generics.ListAPIView):
    queryset = Blog.objects.all().order_by("-views")[:5]
    serializer_class = BlogSerializer
    permission_classes = [permissions.AllowAny]

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return custom_response(
            success=True,
            message="Popular blogs retrieved successfully",
            data=response.data
        )

class BlogDataView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        # Get all unique categories from Blog model
        categories = Blog.objects.values_list("category", flat=True).distinct()

        # Get all blogs
        blogs = Blog.objects.all().order_by('-date')  # Latest blogs first
        serialized_blogs = BlogSerializer(blogs, many=True).data

        # Format blog list
        blog_list = [
            {
                "id": blog["id"],
                "title": blog["title"],
                "description": blog["content"][:100],  # Short description preview
                "image": blog["cover_image"],  # Assuming 'cover_image' holds image URLs
                "category": blog["category"],
                "views": blog["views"],  # Include view count
            }
            for blog in serialized_blogs
        ]

        # Fetch top 5 most popular blogs by views
        popular_blogs = Blog.objects.all().order_by('-views')[:5]
        popular_posts = [
            {"id": blog.id, "title": blog.title, "link": f"/blog/{blog.slug}/"}
            for blog in popular_blogs
        ]

        # Dynamic Sidebar Content
        sidebar_content = {
            "popularPosts": popular_posts,
            "tags": Blog.objects.values_list("tags", flat=True).distinct(),  # Get unique tags
        }

        # Construct response
        blogData = {
            "categories": list(categories),
            "blogs": blog_list,
            "sidebarContent": sidebar_content,
        }

        return Response(blogData, status=200)

