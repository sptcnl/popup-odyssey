from rest_framework import serializers
from .models import Place

class PlaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Place
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")