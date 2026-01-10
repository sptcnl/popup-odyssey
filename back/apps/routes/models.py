from django.db import models
from django.contrib.gis.db import models as gis_models


class Route(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='routes')
    points = gis_models.LineStringField(srid=4326)
    total_distance = models.FloatField()
    duration = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Route {self.id} by {self.user.email}"


class UserHistory(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    route = models.ForeignKey(Route, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)