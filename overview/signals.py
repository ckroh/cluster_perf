from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import *

#@receiver(pre_save, sender=Result)
#def submit_batchsystem(sender, instance, **kwargs):
#    instance.profile.save()
