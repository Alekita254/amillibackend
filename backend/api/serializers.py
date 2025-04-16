from rest_framework import serializers
from django.conf import settings
from urllib.parse import urljoin
from .models import NewsletterSubscriber, ContactMessage, Author, Blog, Comment
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.forms import PasswordResetForm
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.core.validators import validate_email
from django.core.exceptions import ValidationError as DjangoValidationError


User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
        min_length=8,
        style={'input_type': 'password'},
        help_text="Minimum 8 characters"
    )
    email = serializers.EmailField(
        validators=[validate_email],
        help_text="Must be a valid email address"
    )

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'first_name', 'last_name']
        extra_kwargs = {
            'username': {
                'help_text': '150 characters or fewer. Letters, digits and @/./+/-/_ only.'
            }
        }

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return value.lower()

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', '')
        )
        return user

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 
            'first_name', 'last_name', 
            'email_verified', 'date_joined'
        ]
        read_only_fields = [
            'id', 'username', 'email', 
            'email_verified', 'date_joined'
        ]

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        
        if not self.user.email_verified:
            raise serializers.ValidationError({
                'email': 'Email not verified. Please check your inbox.'
            })
            
        # Add custom claims
        refresh = self.get_token(self.user)
        data['refresh'] = str(refresh)
        data['access'] = str(refresh.access_token)
        data['user'] = UserProfileSerializer(self.user).data
        
        return data

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['username'] = user.username
        token['email'] = user.email
        token['email_verified'] = user.email_verified
        return token

class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField(
        required=True,
        help_text="Registered email address"
    )

    def validate_email(self, value):
        try:
            validate_email(value)
            if not User.objects.filter(email__iexact=value).exists():
                raise serializers.ValidationError("No account found with this email.")
            return value.lower()
        except DjangoValidationError:
            raise serializers.ValidationError("Enter a valid email address.")

    def save(self):
        request = self.context.get('request')
        email = self.validated_data['email']
        
        form = PasswordResetForm({'email': email})
        if form.is_valid():
            form.save(
                request=request,
                use_https=request.is_secure(),
                email_template_name='users/password_reset_email.html',
                subject_template_name='users/password_reset_subject.txt',
                extra_email_context={
                    'support_email': settings.DEFAULT_FROM_EMAIL
                }
            )

class PasswordResetConfirmSerializer(serializers.Serializer):
    new_password = serializers.CharField(
        write_only=True,
        required=True,
        min_length=8,
        style={'input_type': 'password'},
        help_text="Minimum 8 characters"
    )
    uid = serializers.CharField(
        required=True,
        write_only=True,
        help_text="User identifier from reset link"
    )
    token = serializers.CharField(
        required=True,
        write_only=True,
        help_text="Token from reset link"
    )

    def validate(self, attrs):
        try:
            uid = force_str(urlsafe_base64_decode(attrs['uid']))
            user = User.objects.get(pk=uid)
            
            if not default_token_generator.check_token(user, attrs['token']):
                raise serializers.ValidationError({
                    'token': 'Invalid or expired token'
                })
                
            attrs['user'] = user
            return attrs
            
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise serializers.ValidationError({
                'uid': 'Invalid user identifier'
            })

    def save(self):
        user = self.validated_data['user']
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user

class EmailVerificationSerializer(serializers.Serializer):
    token = serializers.CharField(
        required=True,
        help_text="Verification token from email"
    )
    uidb64 = serializers.CharField(
        required=True,
        help_text="User identifier from verification link"
    )

    def validate(self, attrs):
        try:
            uid = force_str(urlsafe_base64_decode(attrs['uidb64']))
            user = User.objects.get(pk=uid)
            
            if not default_token_generator.check_token(user, attrs['token']):
                raise serializers.ValidationError({
                    'token': 'Invalid or expired verification token'
                })
                
            attrs['user'] = user
            return attrs
            
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise serializers.ValidationError({
                'uidb64': 'Invalid user identifier'
            })
        

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
        
class CommentSerializer(serializers.ModelSerializer):
    replies = serializers.SerializerMethodField()  # Fetch nested replies

    class Meta:
        model = Comment
        fields = ['id', 'name', 'email', 'message', 'blog', 'parent', 'likes', 'dislikes', 'created_at', 'replies']
        read_only_fields = ['id', 'created_at', 'likes', 'dislikes']  # These fields shouldn't be modified directly

    def get_replies(self, obj):
        """Fetch only direct replies to this comment."""
        replies = obj.replies.all()
        return CommentSerializer(replies, many=True).data     
    
class CommunitySerializer(serializers.ModelSerializer):
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
            image_url = obj.cover_image.url 
            return urljoin(settings.SITE_DOMAIN, image_url.lstrip('/'))
        return None
    