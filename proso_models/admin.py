# -*- coding: utf-8 -*-

from models import Answer
from django.contrib import admin


def pretty_date(time=False):
    """
    Get a datetime object or a int() Epoch timestamp and return a
    pretty string like 'an hour ago', 'Yesterday', '3 months ago',
    'just now', etc
    """
    from datetime import datetime
    from django.utils import timezone
    now = timezone.now()
    if isinstance(time, int):
        diff = now - datetime.fromtimestamp(time)
    elif isinstance(time, datetime):
        diff = now - time
    elif not time:
        diff = now - now
    second_diff = diff.seconds
    day_diff = diff.days

    if day_diff < 0:
        return ''

    if day_diff == 0:
        if second_diff < 10:
            return "just now"
        if second_diff < 60:
            return str(second_diff) + " seconds ago"
        if second_diff < 120:
            return "a minute ago"
        if second_diff < 3600:
            return str(second_diff / 60) + " minutes ago"
        if second_diff < 7200:
            return "an hour ago"
        if second_diff < 86400:
            return str(second_diff / 3600) + " hours ago"
    if day_diff == 1:
        return "Yesterday"
    if day_diff < 7:
        return str(day_diff) + " days ago"
    if day_diff < 31:
        return str(day_diff / 7) + " weeks ago"
    if day_diff < 365:
        return str(day_diff / 30) + " months ago"
    return str(day_diff / 365) + " years ago"


class AnswerAdmin(admin.ModelAdmin):

    def is_correct(self, a):
        return a.item_answered == a.item_asked
    is_correct.short_description = 'Correct'
    is_correct.boolean = True

    def asked_ago(self, a):
        return pretty_date(a.time)
    asked_ago.short_description = 'When Asked'

    list_display = (
        'user',
        'item_asked',
        'item_answered',
        'is_correct',
        'asked_ago')


admin.site.register(Answer, AnswerAdmin)
