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
from django.db.models.functions import TruncMonth
from django.db.models import Count
from django.utils.timezone import now



import logging
from rest_framework.throttling import ScopedRateThrottle
from django.db.models import F
from rest_framework.exceptions import ValidationError
from .permissions import IsStaffOrReadOnly

logger = logging.getLogger(__name__)
User = get_user_model()

def _create_payload(request):
    """Multipart forms carry the fields as a JSON string in `data`; plain JSON posts are used as-is."""
    raw = request.data.get("data")
    if raw is None:
        return request.data
    try:
        payload = json.loads(raw)
    except (TypeError, ValueError):
        raise ValidationError({"data": "Must be valid JSON."})
    if not isinstance(payload, dict):
        raise ValidationError({"data": "Must be a JSON object."})
    if request.FILES.get("cover_image"):
        payload["cover_image"] = request.FILES["cover_image"]
    return payload


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
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'email'

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        try:
            user.send_verification_email()
        except Exception:
            logger.exception("Verification email failed for user %s", user.pk)
        
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
    
class MyProfileView(generics.RetrieveUpdateAPIView):
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
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'email'

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
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        subject = request.data.get('subject')
        message = request.data.get('message')
        recipient_list = request.data.get('recipients', [])

        if (not subject or not message or not isinstance(recipient_list, list)
                or not recipient_list or len(recipient_list) > 50):
            return custom_response(
                success=False,
                message="subject, message and 1-50 recipients are required",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, recipient_list)

        return custom_response(
            success=True,
            message="Email sent successfully"
        )


class AuthorListCreateView(generics.ListCreateAPIView):
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer
    permission_classes = [IsStaffOrReadOnly]

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
    permission_classes = [IsStaffOrReadOnly]

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
    queryset = Blog.objects.select_related("author")
    # serializer_class = BlogSerializer
    permission_classes = [IsStaffOrReadOnly]

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

    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=_create_payload(request))
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        return custom_response(
            success=True,
            message="Blog created successfully",
            data=BlogSerializer(serializer.instance, context=self.get_serializer_context()).data,
            status_code=status.HTTP_201_CREATED
        )

class BlogDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Blog.objects.select_related("author")
    # serializer_class = BlogSerializer
    permission_classes = [IsStaffOrReadOnly]

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return BlogCreateUpdateSerializer
        return BlogSerializer


    def get_object(self):
        return get_object_or_404(Blog, slug=self.kwargs["slug"])  # Now it will work

    def retrieve(self, request, *args, **kwargs):
        self.get_object()  # 404 if missing
        self.get_queryset().filter(slug=kwargs["slug"]).update(views=F("views") + 1)

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
        blogs = Blog.objects.select_related("author").order_by('-date')  # Latest blogs first
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
            {"id": blog.id, "title": blog.title, "slug": blog.slug, "link": f"/blog/{blog.slug}/"}
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
            # Top-level only: replies come nested inside their parent
            comments = Comment.objects.filter(parent__isnull=True).prefetch_related('replies').order_by('-created_at')
            if postId:
                comments = comments.filter(blog=postId)

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

        except Exception:
            logger.exception("Comment request failed")
            return Response(
                {"message": "Failed to fetch comments", "status": status.HTTP_500_INTERNAL_SERVER_ERROR},
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
        except Exception:
            logger.exception("Comment request failed")
            return Response(
                {"message": "Failed to create comment", "status": status.HTTP_500_INTERNAL_SERVER_ERROR},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class CommentDetailView(APIView):
    """
    Retrieve, update, or delete a single comment.
    """
    permission_classes = [permissions.AllowAny]

    def get_permissions(self):
        # Anyone can read a comment; only staff can edit or delete
        return [permissions.AllowAny() if self.request.method == "GET" else permissions.IsAdminUser()]

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
            if not Comment.objects.filter(pk=pk).update(likes=F("likes") + 1):
                raise Comment.DoesNotExist
            comment = Comment.objects.get(pk=pk)
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
            if not Comment.objects.filter(pk=pk).update(dislikes=F("dislikes") + 1):
                raise Comment.DoesNotExist
            comment = Comment.objects.get(pk=pk)
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
    queryset = Community.objects.select_related("author")
    # serializer_class = CommunitySerializer
    permission_classes = [IsStaffOrReadOnly]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CommunityCreateUpdateSerializer
        return CommunitySerializer


    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return custom_response(
            success=True,
            message="Community retrieved successfully",
            data=response.data
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=_create_payload(request))
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        return custom_response(
            success=True,
            message="Community created successfully",
            data=CommunitySerializer(serializer.instance, context=self.get_serializer_context()).data,
            status_code=status.HTTP_201_CREATED
        )

class CommunityDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Community.objects.select_related("author")
    # serializer_class = CommunitySerializer
    permission_classes = [IsStaffOrReadOnly]

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return CommunityCreateUpdateSerializer
        return CommunitySerializer


    def get_object(self):
        return get_object_or_404(Community, slug=self.kwargs["slug"])

    def retrieve(self, request, *args, **kwargs):
        self.get_object()  # 404 if missing
        self.get_queryset().filter(slug=kwargs["slug"]).update(views=F("views") + 1)

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

        community = Community.objects.select_related("author").order_by('-date')
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


class UserPublicProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, email):
        # Own profile, or any profile for staff
        if not request.user.is_staff and request.user.email.lower() != email.lower():
            return standard_response(status=False, message="Forbidden", status_code=status.HTTP_403_FORBIDDEN)
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return standard_response(
                status=False,
                message="User not found",
                data={},
                status_code=status.HTTP_404_NOT_FOUND
            )

        serializer = UserPublicProfileSerializer(user)
        return standard_response(
            status=True,
            message="Fetched user profile successfully",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )


class DashboardStatsView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        current_year = now().year

        # 1. Monthly Blog Posts for the current year
        monthly_blog_data = (
            Blog.objects.filter(date__year=current_year)
            .annotate(month=TruncMonth("date"))
            .values("month")
            .annotate(count=Count("id"))
            .order_by("month")
        )

        monthly_blog_posts = {
            entry["month"].strftime("%B"): entry["count"]
            for entry in monthly_blog_data
        }

        # 2. Latest 5 blogs
        latest_blogs = Blog.objects.all().order_by("-date")[:5]
        latest_blogs_data = BlogSummarySerializer(latest_blogs, many=True).data

        # 3. Community event distribution (by category)
        community_distribution = (
            Community.objects.values("category")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        # 4. Totals (optional)
        total_blogs = Blog.objects.count()
        total_communities = Community.objects.count()

        # Construct response
        data = {
            "monthly_blog_posts": monthly_blog_posts,
            "latest_blogs": latest_blogs_data,
            "community_distribution": list(community_distribution),
            "totals": {
                "blogs": total_blogs,
                "communities": total_communities,
            }
        }

        return standard_response(
            status=True,
            message="Dashboard stats fetched successfully",
            data=data,
            status_code=status.HTTP_200_OK
        )