from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()

router.register(r'profiles', views.UserProfileViewSet)

urlpatterns = router.urls