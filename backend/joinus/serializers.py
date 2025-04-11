from rest_framework import serializers
from .models import JoinUsPageConfig, JoinUsSubmission

class JoinUsPageConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = JoinUsPageConfig
        fields = '__all__'

class JoinUsSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = JoinUsSubmission
        fields = '__all__'
