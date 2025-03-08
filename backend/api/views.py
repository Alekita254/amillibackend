from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from django.core.mail import send_mail
from .models import NewsletterSubscriber, ContactMessage
from .serializers import NewsletterSubscriberSerializer, ContactMessageSerializer

class NewsletterSignupView(generics.CreateAPIView):
    queryset = NewsletterSubscriber.objects.all()
    serializer_class = NewsletterSubscriberSerializer

class ContactFormView(generics.CreateAPIView):
    queryset = ContactMessage.objects.all()
    serializer_class = ContactMessageSerializer

class SendCustomEmailView(APIView):
    def post(self, request):
        subject = request.data.get('subject')
        message = request.data.get('message')
        recipient_list = request.data.get('recipients', [])
        
        if not subject or not message or not recipient_list:
            return Response({'error': 'Missing fields'}, status=status.HTTP_400_BAD_REQUEST)
        
        send_mail(subject, message, 'your_email@example.com', recipient_list)
        return Response({'success': 'Email sent successfully'}, status=status.HTTP_200_OK)
    
    