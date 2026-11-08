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

    def validate_resume(self, f):
        if f:
            if not f.name.lower().endswith(('.pdf', '.doc', '.docx')):
                raise serializers.ValidationError("Resume must be a PDF or Word document.")
            if f.size > 5 * 1024 * 1024:
                raise serializers.ValidationError("Resume must be 5MB or smaller.")
        return f
