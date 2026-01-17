from django.urls import path
from .views import PlaceListCreateAPIView

urlpatterns = [
    path("", PlaceListCreateAPIView.as_view(), name="place-list-create"),
]