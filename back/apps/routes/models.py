from django.db import models
from django.contrib.gis.db import models as gis_models
from django.contrib.auth import get_user_model

User = get_user_model()


class Route(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    points = gis_models.LineStringField()
    total_distance = models.FloatField()
    duration = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)