from rest_framework import serializers
from .models import Place
import os, environ
from popup_geocoding import geocode_naver_map
from config.settings import BASE_DIR

env = environ.Env()
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

class PlaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Place
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")
    
    def to_internal_value(self, data):
        # 주소가 있으면 자동으로 좌표 변환
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
        
        return super().to_internal_value(data)