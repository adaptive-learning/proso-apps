# -*- coding: utf-8 -*-

from .models import Subscription, DiscountCode
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _


class PaymentStatusListFilter(admin.SimpleListFilter):
    title = _('Payment status')
    parameter_name = 'payment_status'

    def lookups(self, request, model_admin):
        return (
            ('PAID', _('Paid')),
            ('FREE', _('Free')),
            ('TIMEOUTED', _('Timeouted')),
            ('CREATED', _('Created')),
        )

    def queryset(self, request, queryset):
        if self.value() == 'FREE':
            return queryset.filter(payment__isnull=True)
        elif self.value() is not None:
            return queryset.filter(payment__state=self.value())
        else:
            return queryset


class SubscriptionAdmin(admin.ModelAdmin):

    list_display = (
        'user',
        'plan_description',
        'discount',
        'created',
        'expiration',
        'payment_status'
    )
    search_fields = (
        'user__username',
    )
    list_filter = (
        PaymentStatusListFilter,
        'plan_description',
        'discount',
    )
    raw_id_fields = (
        "session",
        "user",
        "referral",
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
    list_filter = (
        'plan',
        'discount_percentage',
    )


admin.site.register(Subscription, SubscriptionAdmin)
admin.site.register(DiscountCode, DiscountCodeAdmin)
