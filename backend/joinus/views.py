from rest_framework import generics
from .models import JoinUsPageConfig, JoinUsSubmission
from .serializers import JoinUsPageConfigSerializer, JoinUsSubmissionSerializer
from rest_framework import status, generics, permissions
from rest_framework.views import APIView
from api.utils import custom_response
from django.core.mail import send_mail
from django.conf import settings
import logging
from django.core.mail import EmailMultiAlternatives
from datetime import datetime
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)    

class JoinUsConfigView(generics.RetrieveAPIView):
    queryset = JoinUsPageConfig.objects.all()
    serializer_class = JoinUsPageConfigSerializer

    def get_object(self):
        return self.get_queryset().first()
    
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



class JoinUsSubmissionView(generics.CreateAPIView):
    queryset = JoinUsSubmission.objects.all()
    serializer_class = JoinUsSubmissionSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        try:
            response = super().create(request, *args, **kwargs)
            submitted_data = response.data

            full_name = f"{submitted_data.get('first_name')} {submitted_data.get('last_name')}"

            # Email context
            context = {
                "full_name": full_name,
                "year": datetime.now().year,
            }

            subject = "🎉 Thank you for joining us!"
            from_email = settings.DEFAULT_FROM_EMAIL
            to_email = [submitted_data.get("email")]

            html_content = render_to_string("join_us_confirmation_email.html", context)
            text_content = (
                f"Hi {full_name},\n\n"
                "Thank you for showing interest in joining our community at amilliontechies!\n\n"
                "We've received your submission and will be in touch soon.\n\n"
                "Stay inspired and keep building! 🚀\n\n"
                "— The Team @amilliontechies"
            )

            email = EmailMultiAlternatives(subject, text_content, from_email, to_email)
            email.attach_alternative(html_content, "text/html")
            email.send()

            return custom_response(
                success=True,
                message="Your join request has been submitted successfully!",
                data=submitted_data,
                status_code=status.HTTP_201_CREATED
            )

        except Exception as e:
            logger.error("Error handling JoinUs submission: %s", str(e))
            return custom_response(
                success=False,
                message="There was an error processing your submission. Please try again later.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        