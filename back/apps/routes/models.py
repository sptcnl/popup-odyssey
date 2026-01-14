import json, hashlib
from django.db import models
from django.contrib.gis.db import models as gis_models
from django.contrib.postgres import fields


class Route(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='routes', null=True, blank=True)
    
    # 핵심 좌표 정보
    points = gis_models.LineStringField(srid=4326)  # 최적화된 경로 LineString
    original_coordinates = fields.ArrayField(  # 원본 입력 좌표 JSON 저장
        gis_models.PointField(srid=4326), size=50
    )
    
    # 계산 결과
    total_distance = models.FloatField()  # km
    duration = models.FloatField()        # 분
    optimal_order = fields.ArrayField(    # [0,2,1,3] 최적 순서
        models.IntegerField(), size=50
    )
    
    # 메타데이터
    locations_count = models.PositiveSmallIntegerField(default=0)
    walking_mode = models.BooleanField(default=True)  # 도보/자동차 구분
    
    # 인덱스 최적화 필드
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # 캐싱/재계산용
    hash_key = models.CharField(max_length=64, unique=True, db_index=True)  # 좌표 해시
    is_dirty = models.BooleanField(default=False)  # 재계산 필요 플래그
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['hash_key']),
            models.Index(fields=['walking_mode', 'locations_count']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Route #{self.id} ({self.locations_count}pts) by {self.user.email}"
    
    @property
    def walking_time_hours(self):
        return round(self.duration / 60, 1)
    
    def get_original_coords(self):
        """원본 좌표 리스트 반환"""
        return [(p.x, p.y) for p in self.original_coordinates]
    
    def save(self, *args, **kwargs):
        if not self.hash_key:
            self.hash_key = self._generate_hash()
        super().save(*args, **kwargs)
    
    def _generate_hash(self):
        """좌표 해시 생성 (중복 방지)"""
        coords_str = json.dumps(self.get_original_coords(), sort_keys=True)
        return hashlib.md5(coords_str.encode()).hexdigest()


class UserHistory(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    route = models.ForeignKey(Route, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)