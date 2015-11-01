from models import UserProfile, Session
from django.contrib import admin


class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'send_emails', 'public')
    search_fields = ('user__username',)


class SessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'time_zone', 'http_user_agent', 'location',
                    'locale', 'display_width', 'display_height')
    search_fields = ('user__username',)
    list_filter = ('time_zone', 'locale',)


admin.site.register(Session, SessionAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
