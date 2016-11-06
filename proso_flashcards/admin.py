from django.contrib import admin
from .models import Term, Context, Flashcard, Category, FlashcardAnswer
from proso_models.admin import pretty_date


class TermAdmin(admin.ModelAdmin):
    list_display = ('id', 'identifier', 'lang', 'name')
    search_fields = ('identifier', 'name')
    list_filter = ('lang',)


class ContextAdmin(admin.ModelAdmin):
    list_display = ('id', 'identifier', 'lang', 'name')
    search_fields = ('name', )
    list_filter = ('lang',)


class FlashcardAdmin(admin.ModelAdmin):
    list_display = ('id', 'identifier', 'lang', 'term', 'context')
    search_fields = ('identifier', 'term__name', 'context__name')
    list_filter = ('lang',)


class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'identifier', 'lang', 'name')
    search_fields = ('name',)
    list_filter = ('lang',)


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

    def context_wrapped(self, a):
        return str(a.context).replace(',', ', ')
    context_wrapped.short_description = 'Context'

    list_display = (
        'user',
        'item_asked',
        'item_answered',
        'context_wrapped',
        'is_correct',
        'options_count',
        'type',
        'time',
        'asked_ago',
    )
    raw_id_fields = (
        'config',
        'context',
        'item',
        'item_answered',
        'item_asked',
        'metainfo',
        'options',
        'practice_set',
        'session',
        'user',
    )
    search_fields = ('user__username',)


admin.site.register(Term, TermAdmin)
admin.site.register(Context, ContextAdmin)
admin.site.register(Flashcard, FlashcardAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(FlashcardAnswer, AnswerAdmin)
