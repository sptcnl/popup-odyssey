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
    address = models.CharField(max_length=200)
    location = gis_models.PointField(
        srid=4326,
        null=True, 
        blank=True,
        geography=True
    )
    geo_x = models.FloatField(null=True, blank=True)  # 경도 (longitude)
    geo_y = models.FloatField(null=True, blank=True)  # 위도 (latitude)
    link = models.URLField(max_length=500, null=True, blank=True, verbose_name="상세 링크")
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


class PopgaPopup(models.Model):
    id = models.CharField(max_length=50, primary_key=True)
    popup_name = models.CharField(max_length=500)
    category = models.CharField(max_length=100, null=True, blank=True)
    status = models.CharField(max_length=50, null=True, blank=True)
    popup_date = models.CharField(max_length=100, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    opening_hours = models.TextField(null=True, blank=True)
    notice = models.TextField(null=True, blank=True)
    detail_link = models.TextField(null=True, blank=True)
    image_url = models.TextField(null=True, blank=True)
    image_path = models.TextField(null=True, blank=True)
    visit_events = models.TextField(null=True, blank=True)
    on_site_events = models.TextField(null=True, blank=True)
    purchase_events = models.TextField(null=True, blank=True)
    other_events = models.TextField(null=True, blank=True)
    location = gis_models.PointField(
        srid=4326,
        null=True, 
        blank=True,
        geography=True
    )
    geo_x = models.FloatField(null=True, blank=True)  # 경도 (longitude)
    geo_y = models.FloatField(null=True, blank=True)  # 위도 (latitude)
    geo_validated = models.BooleanField(default=False)
    crawled_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.popup_name

    class Meta:
        db_table = 'popga_popups'


class PlaceLike(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    place = models.ForeignKey(Place, on_delete=models.CASCADE)
    popup_id = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'place', 'popup_id')


class PlaceVisit(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    place = models.ForeignKey(Place, on_delete=models.CASCADE)
    popup_id = models.CharField(max_length=50)
    route = models.ForeignKey('routes.Route', on_delete=models.SET_NULL, null=True, blank=True)
    visited_at = models.DateTimeField()

    class Meta:
        indexes = [
            models.Index(fields=['place', 'visited_at', 'popup_id'])
        ]