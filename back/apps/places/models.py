from django.db import models
from django.contrib.gis.db import models as gis_models
from django.contrib.postgres import indexes


class Category(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class Place(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='places', null=True, blank=True)
    is_public = models.BooleanField(default=True)
    name = models.CharField(max_length=100)
    image = models.ImageField(null=True, blank=True)
    address = models.CharField(max_length=200)
    location = gis_models.PointField(
        srid=4326,
        null=True, 
        blank=True,
        geography=True
    )
    status = models.CharField(max_length=50, null=True, blank=True)
    start_date = models.DateField(max_length=100, null=True, blank=True)
    end_date = models.DateField(max_length=100, null=True, blank=True)
    geo_x = models.FloatField(null=True, blank=True)  # 경도 (longitude)
    geo_y = models.FloatField(null=True, blank=True)  # 위도 (latitude)
    geo_validated = models.BooleanField(default=False)
    link = models.URLField(max_length=500, null=True, blank=True, verbose_name="상세 링크")
    is_popup = models.BooleanField()
    detail_category = models.CharField(max_length=100, null=True, blank=True, verbose_name="상세 카테고리")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class PlaceCategory(models.Model):
    id = models.AutoField(primary_key=True)
    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name='categories')
    category = models.ForeignKey(Category, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('place', 'category')


class PlaceLike(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    place = models.ForeignKey(Place, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'place')


class PlaceVisit(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    place = models.ForeignKey(Place, on_delete=models.CASCADE)
    route = models.ForeignKey('routes.Route', on_delete=models.SET_NULL, null=True, blank=True)
    visited_at = models.DateTimeField()

    class Meta:
        indexes = [
            models.Index(fields=['place', 'visited_at'])
        ]