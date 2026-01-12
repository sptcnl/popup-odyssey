from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    email = models.EmailField(max_length=254, unique=True)
    role = models.CharField(max_length=20, default='USER')
    is_active = models.BooleanField(default=True)
    provider = models.CharField(max_length=20, null=True, blank=True)
    provider_id = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_login_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.email