from django.db import models
from django.contrib.gis.db import models as gis_models


class Place(models.Model):
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=200)
    location = gis_models.PointField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Category(models.Model):
    name = models.CharField(max_length=50)


class PlaceCategory(models.Model):
    place = models.ForeignKey(Place, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)