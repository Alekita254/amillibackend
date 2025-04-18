from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.core.mail import send_mail
from .models import *
from .utils import custom_response 
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from .serializers import *
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.shortcuts import redirect
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
import json


User = get_user_model()

def standard_response(status=True, message="", data=None, status_code=status.HTTP_200_OK):
    """Standardized API response format"""
    return Response({
        "status": status,
        "message": message,
        "data": data or {}
    }, status=status_code)

class UserCreateView(generics.CreateAPIView):
    """
    Register a new user and send verification email
    Returns user data and tokens if registration succeeds
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        user.send_verification_email()
        
        refresh = RefreshToken.for_user(user)
        
        return standard_response(
            status=True,
            message="Registration successful. Verification email sent.",
            data={
                "user": UserSerializer(user).data,
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                }
            },
            status_code=status.HTTP_201_CREATED
        )


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Authenticate user using email and return JWT tokens with user data
    """
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            return Response({"status": False, "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        user_data = data.pop("user", {})  # remove user data from token section

        return Response({
            "status": True,
            "message": "Login successful",
            "data": {
                "user": user_data,
                "tokens": data
            }
        }, status=status.HTTP_200_OK)
    
class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    Get or update authenticated user's profile
    """
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return standard_response(
            status=True,
            message="Profile retrieved successfully",
            data=serializer.data
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return standard_response(
            status=True,
            message="Profile updated successfully",
            data=serializer.data
        )

class PasswordResetView(generics.GenericAPIView):
    """
    Initiate password reset process
    """
    serializer_class = PasswordResetSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return standard_response(
            status=True,
            message="If this email exists in our system, you'll receive a password reset link",
            status_code=status.HTTP_200_OK
        )

class PasswordResetConfirmView(generics.GenericAPIView):
    """
    Complete password reset process
    """
    serializer_class = PasswordResetConfirmSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Generate new tokens after password reset
        refresh = RefreshToken.for_user(user)
        
        return standard_response(
            status=True,
            message="Password reset successfully",
            data={
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email
                },
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                }
            },
            status_code=status.HTTP_200_OK
        )

class EmailVerificationView(generics.GenericAPIView):
    """
    Verify user's email via token
    Redirects to frontend with verification status
    """
    serializer_class = EmailVerificationSerializer
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        token = request.GET.get('token')
        uidb64 = request.GET.get('uidb64')
        
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is not None and default_token_generator.check_token(user, token):
            user.email_verified = True
            user.save()
            refresh = RefreshToken.for_user(user)
            return redirect(
                f'{settings.FRONTEND_URL}/login?'
                f'verified=true&'
                f'refresh={str(refresh)}&'
                f'access={str(refresh.access_token)}'
            )
        
        return redirect(
            f'{settings.FRONTEND_URL}/error?'
            f'message=Invalid+verification+link'
        )

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
    # serializer_class = BlogSerializer
    permission_classes = [permissions.AllowAny] 

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return BlogCreateUpdateSerializer
        return BlogSerializer


    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return custom_response(
            success=True,
            message="Blogs retrieved successfully",
            data=response.data
        )

    # def create(self, request, *args, **kwargs):
    #     response = super().create(request, *args, **kwargs)
    #     return custom_response(
    #         success=True,
    #         message="Blog created successfully",
    #         data=response.data,
    #         status_code=status.HTTP_201_CREATED
    #     )

    def create(self, request, *args, **kwargs):
        # Parse the JSON data field from form-data
        json_data = json.loads(request.data.get("data", "{}"))

        # Merge the file (cover_image) into the parsed data
        if request.FILES.get("cover_image"):
            json_data["cover_image"] = request.FILES["cover_image"]

        serializer = self.get_serializer(data=json_data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        return custom_response(
            success=True,
            message="Blog created successfully",
            data=serializer.data,
            status_code=status.HTTP_201_CREATED
        )

class BlogDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Blog.objects.all()
    # serializer_class = BlogSerializer
    permission_classes = [permissions.AllowAny] 

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return BlogCreateUpdateSerializer
        return BlogSerializer


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


class CommentListCreateView(APIView):
    """
    List all comments for a specific blog or create a new comment.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, postId=None):
        try:
            # Filter comments by blog ID if postId is provided
            if postId:
                comments = Comment.objects.filter(blog=postId).order_by('-created_at')
            else:
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
                    "parent": comment["parent"],
                    "replies": comment["replies"],  # Ensure nested replies are included
                }
                for comment in serialized_comments
            ]

            response_data = {
                "message": "Comments fetched successfully",
                "data": {
                    "comments": comment_list,
                },
                "status": status.HTTP_200_OK,
            }
            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"message": "Failed to fetch comments", "error": str(e), "status": status.HTTP_500_INTERNAL_SERVER_ERROR},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def post(self, request):
        """
        Create a new comment.
        """
        try:
            serializer = CommentSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                response_data = {
                    "message": "Comment created successfully",
                    "data": serializer.data,
                    "status": status.HTTP_201_CREATED,
                }
                return Response(response_data, status=status.HTTP_201_CREATED)
            else:
                return Response(
                    {"message": "Invalid data", "errors": serializer.errors, "status": status.HTTP_400_BAD_REQUEST},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except Exception as e:
            return Response(
                {"message": "Failed to create comment", "error": str(e), "status": status.HTTP_500_INTERNAL_SERVER_ERROR},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class CommentDetailView(APIView):
    """
    Retrieve, update, or delete a single comment.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        try:
            comment = Comment.objects.get(pk=pk)
            serialized_comment = CommentSerializer(comment).data
            response_data = {
                "message": "Comment fetched successfully",
                "data": serialized_comment,
                "status": status.HTTP_200_OK,
            }
            return Response(response_data, status=status.HTTP_200_OK)
        except Comment.DoesNotExist:
            return Response(
                {"message": "Comment not found", "status": status.HTTP_404_NOT_FOUND},
                status=status.HTTP_404_NOT_FOUND,
            )

    def put(self, request, pk):
        """
        Update a comment.
        """
        try:
            comment = Comment.objects.get(pk=pk)
            serializer = CommentSerializer(comment, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                response_data = {
                    "message": "Comment updated successfully",
                    "data": serializer.data,
                    "status": status.HTTP_200_OK,
                }
                return Response(response_data, status=status.HTTP_200_OK)
            else:
                return Response(
                    {"message": "Invalid data", "errors": serializer.errors, "status": status.HTTP_400_BAD_REQUEST},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except Comment.DoesNotExist:
            return Response(
                {"message": "Comment not found", "status": status.HTTP_404_NOT_FOUND},
                status=status.HTTP_404_NOT_FOUND,
            )

    def delete(self, request, pk):
        """
        Delete a comment.
        """
        try:
            comment = Comment.objects.get(pk=pk)
            comment.delete()
            return Response(
                {"message": "Comment deleted successfully", "status": status.HTTP_204_NO_CONTENT},
                status=status.HTTP_204_NO_CONTENT,
            )
        except Comment.DoesNotExist:
            return Response(
                {"message": "Comment not found", "status": status.HTTP_404_NOT_FOUND},
                status=status.HTTP_404_NOT_FOUND,
            )

class CommentLikeView(APIView):
    """
    Like a comment.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, pk):
        try:
            comment = Comment.objects.get(pk=pk)
            comment.likes += 1
            comment.save()
            response_data = {
                "message": "Comment liked successfully",
                "data": {"likes": comment.likes},
                "status": status.HTTP_200_OK,
            }
            return Response(response_data, status=status.HTTP_200_OK)
        except Comment.DoesNotExist:
            return Response(
                {"message": "Comment not found", "status": status.HTTP_404_NOT_FOUND},
                status=status.HTTP_404_NOT_FOUND,
            )
        

class CommentDislikeView(APIView):
    """
    Dislike a comment.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, pk):
        try:
            comment = Comment.objects.get(pk=pk)
            comment.dislikes += 1
            comment.save()
            response_data = {
                "message": "Comment disliked successfully",
                "data": {"dislikes": comment.dislikes},
                "status": status.HTTP_200_OK,
            }
            return Response(response_data, status=status.HTTP_200_OK)
        except Comment.DoesNotExist:
            return Response(
                {"message": "Comment not found", "status": status.HTTP_404_NOT_FOUND},
                status=status.HTTP_404_NOT_FOUND,
            )
        


class CommunityListCreateView(generics.ListCreateAPIView):
    queryset = Blog.objects.all()
    serializer_class = CommunitySerializer
    permission_classes = [permissions.AllowAny] 

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return custom_response(
            success=True,
            message="Community retrieved successfully",
            data=response.data
        )

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        return custom_response(
            success=True,
            message="Community created successfully",
            data=response.data,
            status_code=status.HTTP_201_CREATED
        )

class CommunityDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Blog.objects.all()
    serializer_class = CommunitySerializer
    permission_classes = [permissions.AllowAny] 

    def get_object(self):
        return get_object_or_404(Blog, slug=self.kwargs["slug"])

    def retrieve(self, request, *args, **kwargs):
        blog = self.get_object()
        blog.views += 1
        blog.save(update_fields=["views"])
        
        response = super().retrieve(request, *args, **kwargs)
        return custom_response(
            success=True,
            message="Community retrieved successfully",
            data=response.data
        )

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        return custom_response(
            success=True,
            message="Community updated successfully",
            data=response.data
        )

    def destroy(self, request, *args, **kwargs):
        super().destroy(request, *args, **kwargs)
        return custom_response(
            success=True,
            message="Community deleted successfully",
            data=None
        )

    
class PopularCommunityView(generics.ListAPIView):
    queryset = Community.objects.all().order_by("-views")[:5]
    serializer_class = CommunitySerializer
    permission_classes = [permissions.AllowAny]

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return custom_response(
            success=True,
            message="Popular events retrieved successfully",
            data=response.data
        )

class CommunityDataView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        categories = Community.objects.values_list("category", flat=True).distinct()

        community = Community.objects.all().order_by('-date')
        serialized_community = CommunitySerializer(community, many=True).data

        community_list = [
            {
                "id": community["id"],
                "title": community["title"],
                "description": community["description"][:100],
                "image": community["cover_image"],
                "category": community["category"],
                "slug": community["slug"],
                "views": community["views"],
            }
            for community in serialized_community
        ]

        popular_community = Community.objects.all().order_by('-views')[:5]
        popular_events = [
            {"id": community.id, "title": community.title, "link": f"/community/{community.slug}/"}
            for community in popular_community
        ]

        # Dynamic Sidebar Content
        sidebar_content = {
            "popularEvents": popular_events,
            "tags": Community.objects.values_list("tags", flat=True).distinct(),  # Get unique tags
        }

        # Construct response
        CommunityData = {
            "categories": list(categories),
            "community": community_list,
            "sidebarContent": sidebar_content,
        }

        return Response(CommunityData, status=200)

