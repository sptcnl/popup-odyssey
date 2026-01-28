from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from .models import Place
import os, environ
from popup_geocoding import geocode_naver_map
from config.settings import BASE_DIR

env = environ.Env()
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

class PlaceCreateSerializer(serializers.ModelSerializer):
    """생성/수정용 Serializer (지오코딩 포함)"""
    class Meta:
        model = Place
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at", "geo_validated")
    
    def to_internal_value(self, data):
        """주소 → 자동 좌표 변환 + 필수 필드 처리"""
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
                print(f"✅ 자동 좌표 변환: {address} → {coords}")
            else:
                print(f"❌ 좌표 변환 실패: {address}")
        
        # 빈 문자열을 None으로 변환 (DateField 호환)
        date_fields = ['start_date', 'end_date']
        for field in date_fields:
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