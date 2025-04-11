
from django.contrib import admin
from django.urls import path, include, re_path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from api.views import (NewsletterSignupView, ContactFormView, SendCustomEmailView, AuthorListCreateView, BlogDataView,
                       AuthorDetailView, BlogListCreateView, BlogDetailView, PopularBlogsView,   CommentListCreateView,
                       CommentDetailView, CommentLikeView, CommentDislikeView, CommunityListCreateView, CommunityDetailView,
                       CommunityDataView, PopularCommunityView)
from django.conf import settings
from django.conf.urls.static import static

# Swagger schema view
schema_view = get_schema_view(
    openapi.Info(
        title="A million Techies Backedn APIs",
        default_version='v1',
        description="API documentation for managing newsletter signups and contact form submissions",
    ),
    public=True,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/newsletter/', NewsletterSignupView.as_view(), name='newsletter_signup'),
    path('api/contact/', ContactFormView.as_view(), name='contact_form'),
    path('api/send-email/', SendCustomEmailView.as_view(), name='send_custom_email'),
    path('api/authors/', AuthorListCreateView.as_view(), name='author_list_create'),
    path('api/authors/<int:pk>/', AuthorDetailView.as_view(), name='author_detail'),
    path('api/blogs/', BlogListCreateView.as_view(), name='blog_list_create'),
    path('api/blogs/<slug:slug>/', BlogDetailView.as_view(), name='blog_detail'),
    path("api/blog-data/", BlogDataView.as_view(), name="blog-data"),
    path("api/popularBlogs/", PopularBlogsView.as_view(), name="blog-data"),
    path('api/comments/', CommentListCreateView.as_view(), name='comment_list_create'),
    path('api/comments/blog/<int:postId>/', CommentListCreateView.as_view(), name='comment_list_by_blog'),
    path('api/comments/<int:pk>/', CommentDetailView.as_view(), name='comment_detail'),
    path('api/comments/<int:pk>/like/', CommentLikeView.as_view(), name='comment_like_detail'),
    path('api/comments/<int:pk>/dislike/', CommentDislikeView.as_view(), name='comment_dislike_detail'),
    path('api/community/', CommunityListCreateView.as_view(), name='community_list_create'),
    path('api/community/<slug:slug>/', CommunityDetailView.as_view(), name='community_detail'),
    path("api/community-data/", CommunityDataView.as_view(), name="community-data"),
    path("api/popularCommunity/", PopularCommunityView.as_view(), name="community-data"),
    path("api/joinus/", include("joinus.urls")),



    # Swagger endpoints
    re_path(r'^swagger/$', schema_view.with_ui('swagger', cache_timeout=0), name='swagger-ui'),
    re_path(r'^redoc/$', schema_view.with_ui('redoc', cache_timeout=0), name='redoc-ui'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

