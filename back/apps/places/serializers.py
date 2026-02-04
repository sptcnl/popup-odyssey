from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from .models import Place
import os, environ
from popup_geocoding import geocode_naver_map
from config.settings import BASE_DIR
import logging

logger = logging.getLogger(__name__)

env = environ.Env()
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

class PlaceCreateSerializer(serializers.ModelSerializer):
    """생성/수정용 Serializer (지오코딩 포함)"""
    is_popup = serializers.BooleanField(required=False)
    is_public = serializers.BooleanField(required=False)
    
    class Meta:
        model = Place
        fields = [
            'id', 'name', 'address', 'image', 'status', 'start_date', 'end_date',
            'is_popup', 'detail_category', 'is_public', 'geo_validated', 'created_at',
            'geo_x', 'geo_y'
        ]
        read_only_fields = ("id", "created_at", "updated_at", "geo_validated")
    
    def to_internal_value(self, data):
        # data 복사
        data = data.copy()

        # 🔹 Boolean 필드 강제 변환
        for bool_field in ['is_popup', 'is_public']:
            if bool_field in data:
                value = data[bool_field]
                if isinstance(value, str):
                    data[bool_field] = value.lower() == 'true'
                else:
                    data[bool_field] = bool(value)

        # 🔹 주소 → 좌표 변환
        address = data.get('address')
        if address:
            coords = geocode_naver_map(
                address=address,
                client_id=env("NAVER_GEO_CLIENT_ID"),
                client_secret=env("NAVER_GEO_CLIENT_SECRET")
            )
            if coords:
                data['geo_x'] = coords['geo_x']
                data['geo_y'] = coords['geo_y']
                data['geo_validated'] = True
                logger.info(f"✅ 자동 좌표 변환: {address} → {coords}")
            else:
                logger.info(f"❌ 좌표 변환 실패: {address}")

        # 🔹 빈 문자열 → None 처리 (DateField 호환)
        for field in ['start_date', 'end_date']:
            if data.get(field) == '':
                data[field] = None

        return super().to_internal_value(data)


class PlaceListSerializer(serializers.ModelSerializer):
    """목록 조회용 Serializer (접근제어 포함)"""
    my_place = serializers.SerializerMethodField()

    class Meta:
        model = Place
        fields = [
            'id', 'name', 'address', 'image', 'status', 'start_date', 'end_date',
            'is_popup', 'detail_category', 'is_public', 'geo_validated', 'created_at',
            'geo_x', 'geo_y', 'my_place'
        ]
    
    def get_my_place(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.user_id == request.user.id
        return False