from django.db import models
from django.contrib.auth.models import User
from datetime import datetime
from proso_user.models import Session
from django.db.models.signals import pre_save
from django.dispatch import receiver
from proso.django.util import disable_for_loaddata


class Comment(models.Model):

    username = models.CharField(null=True, blank=True, max_length=100)
    email = models.EmailField(null=True, blank=True, max_length=200)
    text = models.TextField(null=False, blank=False)
    inserted = models.DateTimeField(auto_now_add=True)
    session = models.ForeignKey(Session)


class Rating(models.Model):
    UNKNOWN = 0
    EASY = 1
    RIGHT = 2
    HARD = 3
    VALUES = (
        (UNKNOWN, 'Unknown'),
        (EASY, 'Too Easy'),
        (RIGHT, 'Just Right'),
        (HARD, 'Too Hard'),
    )
    user = models.ForeignKey(User)
    inserted = models.DateTimeField(default=datetime.now)
    value = models.SmallIntegerField(choices=VALUES, default=UNKNOWN)


@receiver(pre_save, sender=Comment)
@disable_for_loaddata
def init_comment_session(sender, instance, **kwargs):
    instance.session = Session.objects.get_current_session()
