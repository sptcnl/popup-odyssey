import re
from rest_framework import generics
from rest_framework.decorators import permission_classes
from rest_framework.permissions import AllowAny
from .serializers import (
                            SignupSerializer
                        )
from rest_framework.exceptions import ValidationError

from django.contrib.auth import get_user_model

User = get_user_model()

EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
)

def is_valid_email(email: str) -> bool:
    return bool(EMAIL_REGEX.match(email))


@permission_classes([AllowAny])
class SignupView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = SignupSerializer

    def perform_create(self, serializer):
        try:
            serializer.save()
        except Exception as e:
            raise ValidationError({"detail": f"An error occurred: {str(e)}"})