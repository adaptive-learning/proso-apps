# -*- coding: utf-8 -*-

from .models import Subscription, DiscountCode
from django.contrib import admin


class SubscriptionAdmin(admin.ModelAdmin):

    list_display = (
        'user',
        'created',
        'expiration',
        'payment_status'
    )
    search_fields = (
        'user__username',
    )

    def payment_status(self, s):
        return s.payment.status['state'] if s.payment is not None else 'FREE'


class DiscountCodeAdmin(admin.ModelAdmin):

    list_display = (
        'identifier',
        'code',
        'discount_percentage',
        'plan',
        'usage_limit',
    )

admin.site.register(Subscription, SubscriptionAdmin)
admin.site.register(DiscountCode, DiscountCodeAdmin)
