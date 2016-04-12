from django.contrib import admin
from proso_concepts.models import Concept, Tag, Action


class ActionInline(admin.TabularInline):
    model = Action


@admin.register(Concept)
class ConceptAdmin(admin.ModelAdmin):
    list_display = ('identifier', 'name', 'query', 'lang')
    search_fields = ('identifier', 'name', 'query', 'lang')
    inlines = [ActionInline, ]

    def get_readonly_fields(self, request, obj=None):
        return self.readonly_fields + ('identifier', )


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('type', 'value', 'lang')
    search_fields = ('type', 'value', 'lang')
