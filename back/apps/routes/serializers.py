from rest_framework import serializers

class RouteRequestSerializer(serializers.Serializer):
    coordinates = serializers.ListField(
        child=serializers.ListField(child=serializers.FloatField()),
        min_length=2,
        max_length=30
    )