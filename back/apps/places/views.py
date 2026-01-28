# places/views.py
from rest_framework import generics
from .models import Place
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from .serializers import PlaceCreateSerializer, PlaceListSerializer
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from django.db.models import Q


class PlaceListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = PlaceListSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return PlaceCreateSerializer
        return PlaceListSerializer
    
    def get_serializer_context(self):  # 이전 수정사항 유지
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context
    
    def get_queryset(self):
        if self.request.user.is_authenticated:
            # ✅ 두 방식 모두 가능
            return Place.objects.filter(
                Q(is_public=True) | Q(user=self.request.user)
            ).distinct()  # 중복 제거 안전장치
        return Place.objects.filter(is_public=True)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)