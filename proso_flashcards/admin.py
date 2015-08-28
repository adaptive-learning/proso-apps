from django.contrib import admin
from models import Term, Context, Flashcard, Category, FlashcardAnswer
from proso_models.admin import pretty_date


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
    raw_id_fields = ('terms', 'subcategories', 'flashcards', 'contexts')


class AnswerAdmin(admin.ModelAdmin):

    def is_correct(self, a):
        return a.item_answered == a.item_asked
    is_correct.short_description = 'Correct'
    is_correct.boolean = True

    def asked_ago(self, a):
        return pretty_date(a.time)
    asked_ago.short_description = 'When Asked'

    def options_count(self, a):
        return a.options.count()

    list_display = (
        'user',
        'item_asked',
        'item_answered',
        'is_correct',
        'direction',
        'options_count',
        'asked_ago')
    raw_id_fields = ("options",)


admin.site.register(Term, TermAdmin)
admin.site.register(Context, ContextAdmin)
admin.site.register(Flashcard, FlashcardAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(FlashcardAnswer, AnswerAdmin)
