from rest_framework import serializers
from .models import Route


class RouteSerializer(serializers.ModelSerializer):
    user_nickname = serializers.CharField(source='user.nickname', read_only=True)
    
    class Meta:
        model = Route
        fields = [
            'id', 'user_nickname', 'points', 'total_distance', 
            'duration', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']