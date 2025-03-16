from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.core.mail import send_mail
from .models import NewsletterSubscriber, ContactMessage, Author, Blog, Comment
from .serializers import (NewsletterSubscriberSerializer, ContactMessageSerializer, AuthorSerializer,
                          BlogSerializer, CommentSerializer)
from .utils import custom_response 
from django.shortcuts import get_object_or_404


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

    def get_object(self):
        return get_object_or_404(Blog, slug=self.kwargs["slug"])  # Now it will work

    def retrieve(self, request, *args, **kwargs):
        blog = self.get_object()
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
                "description": blog["description"][:100],
                "image": blog["cover_image"],
                "category": blog["category"],
                "slug": blog["slug"],
                "views": blog["views"],
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

#
# class CommentListCreateView(generics.ListCreateAPIView):
#     """
#     List all comments or create a new comment.
#     If a `parent` is provided, it will be a reply to another comment.
#     """
#     queryset = Comment.objects.all()
#     serializer_class = CommentSerializer
#     permission_classes = [permissions.AllowAny]  # Open for all users
#
#     def perform_create(self, serializer):
#         """Automatically associate the comment with a blog."""
#         serializer.save()
#
#
# class CommentDetailView(generics.RetrieveUpdateDestroyAPIView):
#     """
#     Retrieve, update, or delete a single comment.
#     """
#     queryset = Comment.objects.all()
#     serializer_class = CommentSerializer
#     permission_classes = [permissions.AllowAny]

class CommentListCreateView(APIView):
    """
    List all comments or create a new comment.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        # Get all comments ordered by creation date (latest first)
        comments = Comment.objects.all().order_by('-created_at')
        serialized_comments = CommentSerializer(comments, many=True).data

        # Format comments to ensure a clean response
        comment_list = [
            {
                "id": comment["id"],
                "name": comment["name"],
                "message": comment["message"],
                "blog": comment["blog"],
                "likes": comment["likes"],
                "dislikes": comment["dislikes"],
                "created_at": comment["created_at"],
                "replies": comment["replies"],  # Ensure nested replies are included
            }
            for comment in serialized_comments
        ]

        return Response({"comments": comment_list}, status=200)

    def post(self, request):
        """
        Create a new comment.
        """
        serializer = CommentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)


class CommentDetailView(APIView):
    """
    Retrieve, update, or delete a single comment.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        try:
            comment = Comment.objects.get(pk=pk)
            serialized_comment = CommentSerializer(comment).data
            return Response(serialized_comment, status=200)
        except Comment.DoesNotExist:
            return Response({"error": "Comment not found"}, status=404)

    def put(self, request, pk):
        """
        Update a comment.
        """
        try:
            comment = Comment.objects.get(pk=pk)
            serializer = CommentSerializer(comment, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=200)
            return Response(serializer.errors, status=400)
        except Comment.DoesNotExist:
            return Response({"error": "Comment not found"}, status=404)

    def delete(self, request, pk):
        """
        Delete a comment.
        """
        try:
            comment = Comment.objects.get(pk=pk)
            comment.delete()
            return Response({"message": "Comment deleted successfully"}, status=204)
        except Comment.DoesNotExist:
            return Response({"error": "Comment not found"}, status=404)
