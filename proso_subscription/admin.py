# -*- coding: utf-8 -*-

from .models import Subscription
from django.contrib import admin


class SubscriptionAdmin(admin.ModelAdmin):

    list_display = (
        'user',
        'created',
        'expiration',
        'payment_status'
    )

    def payment_status(self, s):
        return s.payment.status['state']


admin.site.register(Subscription, SubscriptionAdmin)
