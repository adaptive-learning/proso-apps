from .models import UserProfile, UserProfileProperty, Session, Class
from django.contrib import admin


class UserProfilePropertyAdmin(admin.ModelAdmin):
    list_display = ('user_profile', 'name', 'value')
    search_fields = ('user_profile__user__username', 'name')
    list_filter = ('name',)


class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'send_emails', 'public')
    search_fields = ('user__username',)


class SessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'time_zone', 'http_user_agent', 'location',
                    'locale', 'display_width', 'display_height')
    search_fields = ('user__username',)
    list_filter = ('time_zone', 'locale',)


class ClassAdmin(admin.ModelAdmin):
    list_display = ('code', 'name')
    search_fields = ('code', 'name',)

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == 'owner':
            kwargs["queryset"] = UserProfile.objects.all().select_related('user').order_by('user__username')
        return super(ClassAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_manytomany(self, db_field, request=None, **kwargs):
        if db_field.name == "members":
            kwargs["queryset"] = UserProfile.objects.all().select_related('user').order_by('user__username')
        return super(ClassAdmin, self).formfield_for_manytomany(db_field, request, **kwargs)


admin.site.register(Session, SessionAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(UserProfileProperty, UserProfilePropertyAdmin)
admin.site.register(Class, ClassAdmin)
