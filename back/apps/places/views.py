from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Count
from django_filters.rest_framework import DjangoFilterBackend
from .models import Place, PlaceLike, PlaceVisit, Category
from .serializers import PlaceSerializer, PopularPlaceSerializer, CategorySerializer
from drf_spectacular.utils import extend_schema_field, extend_schema, OpenApiExample, OpenApiParameter


class PlaceViewSet(viewsets.ModelViewSet):
    queryset = Place.objects.all()
    serializer_class = PlaceSerializer
    filter_backends = []
    filterset_fields = []
    
    @extend_schema(
        summary="인기 장소 랭킹 TOP N",
        description="방문수 + 좋아요수 기준 인기 랭킹. ?limit=10 으로 개수 조절",
        responses={200: PopularPlaceSerializer(many=True)},
        examples=[
            OpenApiExample(
                'Top 3 랭킹',
                value=[
                    {"id": 1, "name": "신세계 팝업", "rank": 1, "popularity_score": 214},
                    {"id": 2, "name": "롯데월드몰 팝업", "rank": 2, "popularity_score": 189},
                    {"id": 3, "name": "현대백화점 팝업", "rank": 3, "popularity_score": 167},
                ]
            )
        ],
        parameters=[
            OpenApiParameter(
                name='limit',
                type=int,
                location=OpenApiParameter.QUERY,
                description='표시할 랭킹 개수 (기본값: 20, 최대: 50)',
            )
        ]
    )

    def get_permissions(self):
        if self.action in ['like', 'visit']:
            return [IsAuthenticated()]
        return [AllowAny()]
    
    @action(detail=True, methods=['post'], url_path='like')
    def like(self, request, pk=None):
        """장소 좋아요 토글"""
        place = self.get_object()
        user = request.user
        
        like, created = PlaceLike.objects.get_or_create(
            user=user, place=place, defaults={'created_at': None}
        )
        
        if not created:
            like.delete()
            return Response({'message': '좋아요 취소됨'}, status=status.HTTP_200_OK)
        
        return Response({'message': '좋아요 완료'}, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'], url_path='visit')
    def visit(self, request, pk=None):
        """장소 방문 체크"""
        place = self.get_object()
        user = request.user
        
        PlaceVisit.objects.get_or_create(
            user=user, place=place,
            defaults={'route': None, 'visited_at': None}
        )
        
        return Response({'message': '방문 기록됨'}, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'])
    def popular(self, request):
        """인기 장소 랭킹 TOP 20"""
        limit = int(request.query_params.get('limit', 20))
        
        popular_places = (
            Place.objects
            .annotate(
                num_visits=Count('place_visits', distinct=True),
                num_likes=Count('place_likes', distinct=True),
            )
            .order_by('-num_visits', '-num_likes')
            [:limit]
        )
        
        # 순위 부여
        for idx, place in enumerate(popular_places, 1):
            place._rank = idx
        
        serializer = PopularPlaceSerializer(popular_places, many=True)
        return Response(serializer.data)


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer