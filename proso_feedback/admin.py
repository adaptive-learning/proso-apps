from .models import Rating, Comment
from django.contrib import admin


class RatingAdmin(admin.ModelAdmin):
    list_display = ('user', 'value', 'inserted')


class CommentAdmin(admin.ModelAdmin):
    list_display = ('username', 'text', 'inserted')


admin.site.register(Comment, CommentAdmin)
admin.site.register(Rating, RatingAdmin)
