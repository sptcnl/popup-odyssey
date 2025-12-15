from rest_framework import serializers
from django.contrib.gis import serializers as gis_serializers
from django.contrib.auth import get_user_model
from .models import Place, Category, PlaceCategory, PlaceLike, PlaceVisit
from drf_spectacular.utils import extend_schema_field, extend_schema, OpenApiExample

User = get_user_model()


class PlaceSerializer(serializers.ModelSerializer):
    categories = serializers.StringRelatedField(
        many=True, source='place_categories.category', read_only=True
    )
    num_likes = serializers.SerializerMethodField()
    num_visits = serializers.SerializerMethodField()
    popularity_score = serializers.SerializerMethodField()

    class Meta:
        model = Place
        fields = ['id', 'name', 'address', 'location', 'created_at', 'updated_at',
                  'categories', 'num_likes', 'num_visits', 'popularity_score']
        read_only_fields = ['location']

    def get_num_likes(self, obj):
        return obj.place_likes.count()

    def get_num_visits(self, obj):
        return obj.place_visits.count()

    def get_popularity_score(self, obj):
        return obj.place_likes.count() + obj.place_visits.count()
    
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if instance.location:
            representation['location'] = {
                'type': 'Point',
                'coordinates': [instance.location.x, instance.location.y]
            }
        return representation
        
    examples = OpenApiExample(
        '인기 팝업 예시',
        value={
            "id": 1,
            "name": "신세계 백화점 X 브랜드 팝업",
            "address": "서울특별시 강남구 테헤란로 123",
            "location": {
                "type": "Point",
                "coordinates": [127.024612, 37.497947]
            },
            "created_at": "2025-12-12T07:00:00Z",
            "updated_at": "2025-12-12T10:30:00Z",
            "categories": [
                "구매형 사은품"
            ],
            "num_likes": 125,
            "num_visits": 89,
            "popularity_score": 214
        },
        summary="인기 팝업스토어 예시"
    )


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'
    
    examples = OpenApiExample(
        '카테고리 예시',
        value={
            "id": 1,
            "name": "구매형 사은품",
            "description": "구매 금액에 따른 사은품 제공 팝업스토어",
            "created_at": "2025-12-12T07:00:00Z",
            "updated_at": "2025-12-12T07:00:00Z"
        },
        summary="팝업스토어 카테고리 예시"
    )


class PlaceCategorySerializer(serializers.ModelSerializer):
    place_name = serializers.CharField(source='place.name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = PlaceCategory
        fields = '__all__'
    
    examples = OpenApiExample(
        '장소-카테고리 관계 예시',
        value={
            "id": 1,
            "place": 1,
            "place_name": "신세계 백화점 X 브랜드 팝업",
            "category": 1,
            "category_name": "구매형 사은품",
            "created_at": "2025-12-12T07:00:00Z",
            "updated_at": "2025-12-12T07:00:00Z"
        },
        summary="팝업스토어와 카테고리 연결 예시"
    )


class PlaceLikeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlaceLike
        fields = '__all__'

    examples = OpenApiExample(
        '좋아요 예시',
        value={
            "id": 1,
            "place": 1,
            "place_name": "신세계 백화점 X 브랜드 팝업",
            "user": 1,
            "user_email": "user@example.com",
            "created_at": "2025-12-12T08:00:00Z"
        },
        summary="장소 좋아요 기록 예시"
    )

class PlaceVisitSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlaceVisit
        fields = '__all__'
    
    examples = OpenApiExample(
        '방문 예시',
        value={
            "id": 1,
            "place": 1,
            "place_name": "신세계 백화점 X 브랜드 팝업",
            "user": 1,
            "user_email": "user@example.com",
            "visited_at": "2025-12-12T09:30:00Z"
        },
        summary="장소 방문 기록 예시"
    )


class PopularPlaceSerializer(PlaceSerializer):
    """인기 장소 랭킹용 - 집계된 순위 포함"""
    rank = serializers.SerializerMethodField()
    
    class Meta(PlaceSerializer.Meta):
        fields = PlaceSerializer.Meta.fields + ['rank']
    
    def get_rank(self, obj):
        # View에서 미리 계산해서 context로 넘김
        return getattr(obj, '_rank', None)
    
    examples = OpenApiExample(
        '인기 팝업 예시',
        value={
            "id": 1,
            "name": "신세계 백화점 X 브랜드 팝업",
            "address": "서울특별시 강남구 테헤란로 123",
            "location": {
                "type": "Point",
                "coordinates": [127.024612, 37.497947]
            },
            "created_at": "2025-12-12T07:00:00Z",
            "updated_at": "2025-12-12T10:30:00Z",
            "categories": ["구매형 사은품", "한정판 굿즈"],
            "num_likes": 125,
            "num_visits": 89,
            "popularity_score": 214,
            "rank": 1
        },
        summary="인기 팝업스토어 랭킹 예시"
    )