from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Route
from .serializers import RouteSerializer
from apps.users.models import UserHistory


class RouteViewSet(viewsets.ModelViewSet):
    queryset = Route.objects.all()
    serializer_class = RouteSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        route = serializer.save(user=self.request.user)
        
        # 히스토리 자동 생성
        UserHistory.objects.get_or_create(
            user=self.request.user,
            route=route,
            defaults={'created_at': None}
        )