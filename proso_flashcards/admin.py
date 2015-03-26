from django.contrib import admin
from models import Term, Context, Flashcard, Category


class TermAdmin(admin.ModelAdmin):
    list_display = ('id', 'identifier', 'lang', 'name', 'type')
    search_fields = ('name', 'type')


class ContextAdmin(admin.ModelAdmin):
    list_display = ('id', 'identifier', 'lang', 'name')
    search_fields = ('name', )


class FlashcardAdmin(admin.ModelAdmin):
    list_display = ('id', 'identifier', 'lang', 'term', 'context')


class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'identifier', 'lang', 'name', 'type')
    search_fields = ('name', 'type')


admin.site.register(Term, TermAdmin)
admin.site.register(Context, ContextAdmin)
admin.site.register(Flashcard, FlashcardAdmin)
admin.site.register(Category, CategoryAdmin)
