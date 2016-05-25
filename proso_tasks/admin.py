from django.contrib import admin
from proso_tasks.models import Task, TaskInstance, Skill, Context


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('id', 'identifier', 'lang', 'content', 'active')
    search_fields = ('identifier', 'content')
    list_filter = ('lang',)


@admin.register(TaskInstance)
class TaskInstanceAdmin(admin.ModelAdmin):
    list_display = ('id', 'identifier', 'task', 'context', 'description', 'active')
    search_fields = ('identifier', 'description')
    list_filter = ('lang',)


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ('id', 'identifier', 'name', 'active')
    search_fields = ('identifier', 'name')
    list_filter = ('lang',)


@admin.register(Context)
class ContextAdmin(admin.ModelAdmin):
    list_display = ('id', 'identifier', 'lang', 'name', 'content', 'active')
    search_fields = ('identifier', 'name', 'content')
    list_filter = ('lang',)
