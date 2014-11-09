# -*- coding: utf-8 -*-

from models import Question, Category, Set, Option
from django.contrib import admin


class QuestionAdmin(admin.ModelAdmin):
    list_display = ('id', 'text')
    search_fields = ('text',)


class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')


class SetAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')


class OptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'question', 'text', 'order', 'correct')
    search_fields = ('text',)


admin.site.register(Question, QuestionAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(Set, SetAdmin)
admin.site.register(Option, OptionAdmin)
