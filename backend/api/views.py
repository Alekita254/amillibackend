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
