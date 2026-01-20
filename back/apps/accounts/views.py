import re
import requests
import logging
from rest_framework import generics
from rest_framework.decorators import permission_classes
from rest_framework.permissions import AllowAny
from .serializers import SignupSerializer
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from config.settings import BASE_DIR
from django.contrib.auth import get_user_model
import os, environ

# 로깅 설정
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

env = environ.Env()
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

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
        logger.info(f"Signup attempt - Data: {dict(serializer.validated_data)}")
        try:
            serializer.save()
            logger.info("User successfully created via signup")
        except Exception as e:
            logger.error(f"Signup error: {str(e)}", exc_info=True)
            raise ValidationError({"detail": f"An error occurred: {str(e)}"})


class KakaoLoginAPIView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        logger.info(f"Kakao JS SDK login - IP: {request.META.get('REMOTE_ADDR')}")
        
        access_token = request.data.get('access_token')
        if not access_token:
            logger.warning("No access_token provided")
            return Response({'error': 'Kakao access_token required'}, status=400)

        # 1. 카카오 사용자 정보 조회 (JS SDK access_token 사용)
        logger.info("Fetching Kakao user profile with JS SDK token")
        profile_req = requests.get(
            'https://kapi.kakao.com/v2/user/me',
            headers={'Authorization': f'Bearer {access_token}'}
        )
        
        if profile_req.status_code != 200:
            logger.error(f"Kakao profile fetch failed - Status: {profile_req.status_code}, Response: {profile_req.text}")
            return Response({'error': 'Invalid Kakao access token'}, status=401)

        profile_json = profile_req.json()
        kakao_account = profile_json.get('kakao_account', {})
        properties = profile_json.get('properties', {})
        kakao_id = profile_json.get('id')

        logger.info(f"Kakao user - ID: {kakao_id}, Nickname: {properties.get('nickname', 'N/A')}")

        # 2. 사용자 생성/조회
        user, created = User.objects.get_or_create(
            provider_id=kakao_id,
            provider='kakao',
            defaults={
                'username': f'kakao_{kakao_id}',
                'first_name': properties.get('nickname', ''),
                'email': kakao_account.get('email', f'kakao_{kakao_id}@example.com')
            }
        )
        
        if created:
            logger.info(f"New Kakao user created - ID: {user.id}")
            user.provider = 'kakao'  # 명시적 설정
            user.provider_id = kakao_id
            user.save()
        else:
            logger.info(f"Existing Kakao user logged in - ID: {user.id}")

        # 3. JWT 토큰 발급
        refresh = RefreshToken.for_user(user)
        response_data = {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': {
                'id': user.id,
                'username': user.username,
                'nickname': properties.get('nickname', user.first_name),
                'email': user.email or ''
            }
        }
        
        logger.info(f"Kakao login successful - User ID: {user.id}")
        return Response(response_data, status=200)