from django.db import models
from django.contrib.auth.models import User

class Device(models.Model):
    ship_name = models.CharField(max_length=100)
    owner_name = models.CharField(max_length=100)
    read_key = models.CharField(max_length=50)
    channel_id = models.CharField(max_length=50)

    def __str__(self):
        return self.ship_name