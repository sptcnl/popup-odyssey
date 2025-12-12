from django.db import models
from django.contrib.gis.db import models as gis_models
from apps.routes.models import Route
from django.contrib.auth import get_user_model

User = get_user_model()


class Place(models.Model):
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=200)
    location = gis_models.PointField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # 인기 랭킹용 속성 접근 헬퍼
    @property
    def popularity_score(self):
        visits = getattr(self, "num_visits", 0)
        likes = getattr(self, "num_likes", 0)
        return visits + likes


class Category(models.Model):
    name = models.CharField(max_length=50)


class PlaceCategory(models.Model):
    place = models.ForeignKey(Place, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)


class PlaceLike(models.Model):
    """
    유저가 장소에 '좋아요'를 누른 기록
    한 유저가 한 장소에 한 번만 좋아요 가능하게 unique_together 설정
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='place_likes')
    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name='place_likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'place')


class PlaceVisit(models.Model):
    """
    유저가 장소를 방문했다고 기록하는 로그
    - Route와 연결해두면 '이 경로를 실제로 실행했다'는 이벤트 때,
      포함된 장소들을 PlaceVisit으로 bulk_create해서 랭킹에 활용 가능
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='place_visits')
    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name='place_visits')
    route = models.ForeignKey(Route, on_delete=models.SET_NULL, blank=True, null=True, related_name='place_visits')
    visited_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['place', 'visited_at']),
        ]