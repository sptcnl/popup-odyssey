from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()

router.register(r'places', views.PlaceViewSet)
router.register(r'categories', views.CategoryViewSet)

urlpatterns = router.urls