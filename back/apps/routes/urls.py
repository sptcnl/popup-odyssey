from django.urls import path
from . import views

urlpatterns = [
    path('compute/', views.RouteOptimizationView.as_view(), name='compute-route'),
]