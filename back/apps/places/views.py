# places/views.py
from rest_framework import generics
from .models import Place
from .serializers import PlaceSerializer


class PlaceListCreateAPIView(generics.ListCreateAPIView):
    queryset = Place.objects.all()
    serializer_class = PlaceSerializer

    # 예: 로그인 유저만 생성자로 넣고 싶으면 override 가능
    def perform_create(self, serializer):
        # user 필드가 null 허용이라면 다음은 선택사항
        if self.request.user.is_authenticated:
            serializer.save(user=self.request.user)
        else:
            serializer.save()