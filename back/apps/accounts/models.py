from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    email = models.EmailField(unique=True)
    nickname = models.CharField(max_length=50)
    role = models.CharField(max_length=20, default='USER')
    is_active = models.BooleanField(default=True)
    provider = models.CharField(max_length=20, blank=True, null=True)
    provider_id = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_login_at = models.DateTimeField(blank=True, null=True)