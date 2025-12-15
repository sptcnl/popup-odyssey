from rest_framework import serializers
from apps.routes.serializers import RouteSerializer
from .models import UserProfile, UserHistory


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = '__all__'


class UserHistorySerializer(serializers.ModelSerializer):
    user_nickname = serializers.CharField(source='user.nickname', read_only=True)
    route_distance = serializers.FloatField(source='route.total_distance', read_only=True)
    route_duration = serializers.FloatField(source='route.duration', read_only=True)
    
    class Meta:
        model = UserHistory
        fields = [
            'id', 'user_nickname', 'route', 'route_distance', 
            'route_duration', 'created_at'
        ]
        read_only_fields = '__all__'

class UserHistoryDetailSerializer(serializers.ModelSerializer):
    """히스토리 상세 - 경로 내 장소 정보 포함"""
    user_nickname = serializers.CharField(source='user.nickname', read_only=True)
    route = RouteSerializer(read_only=True)
    
    class Meta:
        model = UserHistory
        fields = '__all__'