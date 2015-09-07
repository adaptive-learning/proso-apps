from collections import defaultdict
from django.conf import settings
from django.db import models
from django.db.models import Q, Count
import itertools
from proso_models.models import Item, Answer, get_environment, get_item_selector, get_option_selector
from django.db.models.signals import pre_save, m2m_changed, post_save, pre_delete
from django.dispatch import receiver
from proso.django.util import disable_for_loaddata, cache_pure
from proso.django.config import get_config
import random
import logging


LOGGER = logging.getLogger('django.request')


class Term(models.Model):
    identifier = models.SlugField()
    item = models.ForeignKey(Item, null=True, default=None, related_name="flashcard_terms")

    lang = models.CharField(max_length=2)
    name = models.TextField()
    type = models.CharField(max_length=50, null=True, blank=True)

    def to_json(self, nested=False):
        json = {
            "id": self.pk,
            "identifier": self.identifier,
            "item_id": self.item_id,
            "object_type": "fc_term",
            "lang": self.lang,
            "name": self.name,
            "type": self.type,
        }
        if not nested:
            json["parents"] = [parent.to_json(nested=True) for parent in self.parents.all()]
        return json

    def __unicode__(self):
        return u"{0.lang} - {0.name}".format(self)


class Context(models.Model):
    identifier = models.SlugField()
    item = models.ForeignKey(Item, null=True, default=None, related_name="flashcard_contexts")

    lang = models.CharField(max_length=2)
    name = models.TextField(null=True, blank=True)
    content = models.TextField(null=True, blank=True)

    def to_json(self, nested=False, with_content=True):
        json = {
            "id": self.pk,
            "identifier": self.identifier,
            "item_id": self.item_id,
            "object_type": "fc_context",
            "lang": self.lang,
            "name": self.name,
        }
        if with_content:
            json['content'] = self.content
        if not nested:
            json["categories"] = [category.to_json(nested=True) for category in self.categories.all()]
        return json

    def __unicode__(self):
        return u"{0.lang} - {0.name}".format(self)


class FlashcardQuerySet(models.query.QuerySet):
    def filter_fc(self, categories, contexts, types, avoid, language=None):
        qs = self.filter(Q(active=True) & ~Q(id__in=avoid))
        if language is not None:
            qs = qs.filter(lang=language)
        if isinstance(contexts, list) and len(contexts) > 0:
            qs = qs.filter(reduce(lambda a, b: a | b, map(lambda id:
                                  _create_q('context_id', id) if isinstance(id, int) else _create_q('context__identifier', id), contexts)))
        if isinstance(categories, list) and len(categories) > 0:
            if not isinstance(categories[0], list):
                categories = [categories]
            intersection = []
            for cats in categories:
                union = []
                for id, type in zip(cats, Category.objects.children_types(cats)):
                    union.append(self._get_filter(id, type))
                intersection.append(reduce(lambda a, b: a | b, union))
            qs = qs.filter(reduce(lambda a, b: a & b, intersection))
        if isinstance(types, list) and len(types) > 0:
            qs = qs.filter(reduce(lambda a, b: a | b, map(lambda type: _create_q('term__type', type), types)))
        return qs

    def _get_filter(self, id, type):
        if type is None or type not in [Category.TERMS, Category.FLASHCARDS, Category.CONTEXTS]:
            LOGGER.warn('Trying to filter by a category of categories, which is not supported. Returning FALSE condition.')
            q = Q(pk=False)
            _, negation = _get_value_without_negation(id)
            return ~q if negation else q
        if isinstance(id, int):
            if type == Category.TERMS:
                return _create_q('term__parents__id', id)
            elif type == Category.FLASHCARDS:
                return _create_q('categories__id', id)
            if type == Category.CONTEXTS:
                return _create_q('context__categories__id', id)
        else:
            if type == Category.TERMS:
                return _create_q('term__parents__identifier', id)
            if type == Category.FLASHCARDS:
                return _create_q('categories__identifier', id)
            if type == Category.CONTEXTS:
                return _create_q('context__categories__identifier', id)
        if q is None:
            q = Q(pk=False)


class FlashcardManager(models.Manager):
    def get_queryset(self):
        return FlashcardQuerySet(self.model, using=self._db)

    def candidates_to_practice(self, categories, contexts, types, avoid, language, limit=100):
        item_ids = list(self.filtered_ids(categories, contexts, types, avoid, language)[1])
        if len(item_ids) > limit:
            return random.sample(item_ids, limit)
        else:
            return item_ids

    @cache_pure
    def filtered_ids(self, categories, contexts, types, avoid, language):
        i = tuple(zip(*self.get_queryset().filter_fc(
            categories, contexts, types, avoid, language).values_list("pk", "item_id")))
        if len(i) != 2:
            return [], []
        return i

    @cache_pure
    def filtered_ids_group(self, data, language):
        all_items = []
        items_map = {}
        for identifier, filter in data.items():
            categories = filter.get("categories", [])
            contexts = filter.get("contexts", [])
            types = filter.get("types", [])
            language = filter.get("language", language)
            _, items = Flashcard.objects.filtered_ids(categories, contexts, types, [], language)
            if len(items) > 0:
                items_map[identifier] = items
                all_items += items

        all_items = list(set(all_items))
        return all_items, items_map

    def practice(self, environment, user, time, limit, items, practice_context, language=None, with_contexts=True, items_in_queue=0):
        # prepare
        item_selector = get_item_selector()
        option_selector = get_option_selector(item_selector)

        selected_items, meta = item_selector.select(environment, user, items, time, practice_context, limit, items_in_queue=items_in_queue)

        # get selected flashcards
        flashcards = Flashcard.objects.filter(item_id__in=selected_items).prefetch_related(Flashcard.related_term())
        if with_contexts:
            flashcards = flashcards.prefetch_related(Flashcard.related_context())
        if language is not None:
            flashcards = flashcards.filter(lang=language)
        flashcards = sorted(flashcards, key=lambda fc: selected_items.index(fc.item_id))
        for f, m in zip(flashcards, meta):
            if m is not None:
                f.practice_meta = m

        test_position = self._test_index(meta)
        if test_position is None:
            return self._load_options(
                option_selector, selected_items, flashcards, environment,
                user, time, limit, items, practice_context, language,
                with_contexts)
        else:
            selected_items.pop(test_position)
            test_flashcard = flashcards.pop(test_position)
            test_flashcard.direction = FlashcardAnswer.FROM_TERM
            if len(selected_items) > 0:
                other = self._load_options(
                    option_selector, selected_items, flashcards, environment,
                    user, time, limit, items, practice_context, language,
                    with_contexts)
            else:
                other = []
            return other[:test_position] + [test_flashcard] + other[test_position:]

    @cache_pure
    def under_categories_as_items(self, categories):
        return list(self.under_categories(categories).values_list("item_id", flat=True))

    def under_categories(self, categories):
        all_categories = Category.objects.subcategories(categories)
        return self.filter(
            Q(categories__pk__in=all_categories) |
            Q(context__pk__in=Category.objects.subcontexts(all_categories)) |
            Q(term__pk__in=Category.objects.subterms(all_categories))
        )

    @cache_pure
    def under_terms_as_items(self, terms):
        return list(self.under_terms(terms).values_list("item_id", flat=True))

    def under_terms(self, terms):
        return self.filter(term__in=terms)

    @cache_pure
    def in_contexts_as_items(self, contexts):
        return list(self.in_contexts(contexts).values_list("item_id", flat=True))

    def in_contexts(self, contexts):
        return self.filter(context__in=contexts)

    def number_of_answers_per_fc(self, flashcards_ids, user):
        counts = defaultdict(lambda: 0)
        for f in self.filter(pk__in=flashcards_ids, item__item_answers__user=user) \
                .annotate(answer_count=Count("item__item_answers")).values_list("pk", "answer_count"):
            counts[f[0]] = f[1]
        return counts

    def _load_options(self, option_selector, selected_items, flashcards, environment, user, time, limit, items, practice_context, language, with_contexts):
        from proso_flashcards.flashcard_construction import get_option_set, get_direction

        # option sets
        option_sets = get_option_set().get_option_for_flashcards(flashcards)

        # select direction
        direction = get_direction()
        allow_zero_option = {}
        for flashcard in flashcards:
            force_direction = get_config('proso_flashcards', 'empty_option_set.force_direction', default=None)
            if force_direction is None or len(option_sets[flashcard.item_id]) > 0:
                flashcard.direction = direction.get_direction(flashcard)
            elif force_direction == 't2d':
                flashcard.direction = FlashcardAnswer.FROM_TERM
            elif force_direction == 'd2t':
                force_direction = FlashcardAnswer.FROM_DESCRIPTION
            else:
                raise Exception('Only "t2d" or "d2t" are allowed values for "proso_flashcards.empty_option_set.force_direction"!')
            flashcard.direction = FlashcardAnswer.FROM_TERM if len(option_sets[flashcard.item_id]) == 0 else direction.get_direction(flashcard)
            allow_zero_option[flashcard.item_id] = flashcard.direction == FlashcardAnswer.FROM_TERM

        # select options
        options = option_selector.select_options_more_items(environment, user, selected_items, time, option_sets,
                                                            allow_zero_options=allow_zero_option)
        all_options = {}
        db_options = Flashcard.objects.filter(lang=language, item_id__in=set(itertools.chain(*options)))
        db_options = db_options.prefetch_related(Flashcard.related_term(), "context")
        if with_contexts:
            db_options = db_options.prefetch_related(Flashcard.related_context())
        for option in db_options:
            all_options[option.item_id] = option
        options = dict(zip(selected_items, options))

        for flashcard in flashcards:
            if len(options[flashcard.item_id]) > 0:
                flashcard.options = map(lambda id: all_options[id], options[flashcard.item_id])

        return flashcards

    def _test_index(self, meta):
        check = map(lambda m: m is not None and 'without_options' in m.get('test', ''), meta)
        return check.index(True) if any(check) else None


class Flashcard(models.Model):
    identifier = models.SlugField()
    item = models.ForeignKey(Item, null=True, default=None, related_name="flashcards")

    lang = models.CharField(max_length=2)
    term = models.ForeignKey(Term, related_name="flashcards")
    context = models.ForeignKey(Context, related_name="flashcards")
    description = models.TextField(null=True, blank=True)
    active = models.BooleanField(default=True)

    objects = FlashcardManager()

    def to_json(self, nested=False, categories=True, contexts=True):
        data = {
            "id": self.pk,
            "identifier": self.identifier,
            "item_id": self.item_id,
            "object_type": "fc_flashcard",
            "active": self.active,
            "lang": self.lang,
            "term": self.get_term().to_json(nested=True),
            "description": self.description
        }
        if hasattr(self, "options"):
            data["options"] = map(lambda o: o.to_json(nested=True), sorted(self.options, key=lambda f: f.term.name))
        if hasattr(self, "direction"):
            data["direction"] = self.direction
        if hasattr(self, 'practice_meta'):
            data['practice_meta'] = self.practice_meta
        if not nested and categories:
            data["categories"] = [category.to_json(nested=True) for category in self.categories.all()]
        if not nested and contexts:
            data["context"] = self.get_context().to_json(nested=True)
        else:
            data["context_id"] = self.context_id
        return data

    def get_term(self):
        extension = settings.PROSO_FLASHCARDS.get("term_extension", None)
        if extension is None:
            return self.term
        else:
            return getattr(self.term, extension.__name__.lower())

    def get_context(self):
        extension = settings.PROSO_FLASHCARDS.get("context_extension", None)
        if extension is None:
            return self.context
        else:
            return getattr(self.context, extension.__name__.lower())

    @staticmethod
    def related_term():
        extension = settings.PROSO_FLASHCARDS.get("term_extension", None)
        if extension is None:
            return "term"
        else:
            return "term__{}".format(extension.__name__.lower())

    @staticmethod
    def related_context():
        extension = settings.PROSO_FLASHCARDS.get("context_extension", None)
        if extension is None:
            return "context"
        else:
            return "context__{}".format(extension.__name__.lower())

    def __unicode__(self):
        return u"{0.term} - {0.context}".format(self)


class CategoryManager(models.Manager):
    def subcategories(self, categories):
        subcategories = set(categories)
        while len(categories) > 0:
            categories = self.filter(parents__pk__in=categories).values_list("pk", flat=True)
            subcategories |= set(categories)
        return list(subcategories)

    def subcontexts(self, categories):
        return Context.objects.filter(categories__pk__in=categories)

    def subterms(self, categories):
        return Term.objects.filter(parents__pk__in=categories)

    @cache_pure
    def children_types(self, category_ids):
        types = []
        for id in category_ids:
            if isinstance(id, int):
                id = abs(id)
                types.append(self.filter(pk=id).values_list("children_type", flat=True))
            else:
                if id is not None and id.startswith('-'):
                    id = id[1:]
                types.append(self.filter(identifier=id).values_list("children_type", flat=True))
        types = map(lambda l: l[0] if len(l) > 0 else None, types)
        return types


class Category(models.Model):
    class Meta:
        verbose_name_plural = "categories"

    CATEGORIES = "c"
    TERMS = "t"
    FLASHCARDS = "f"
    CONTEXTS = "x"
    TYPES = (
        (CATEGORIES, "categories"),
        (TERMS, "terms"),
        (FLASHCARDS, "flashcards"),
        (CONTEXTS, "contexts"),
    )

    identifier = models.SlugField()
    item = models.ForeignKey(Item, null=True, default=None, related_name="flashcard_categories")

    lang = models.CharField(max_length=2)
    name = models.TextField()
    type = models.CharField(max_length=50, null=True, blank=True)
    subcategories = models.ManyToManyField("self", related_name="parents", symmetrical=False)
    terms = models.ManyToManyField(Term, related_name="parents")
    flashcards = models.ManyToManyField(Flashcard, related_name="categories")
    contexts = models.ManyToManyField(Context, related_name="categories")
    not_in_model = models.BooleanField(default=False)
    children_type = models.CharField(max_length=1, choices=TYPES, null=True, verbose_name="Category of")

    objects = CategoryManager()

    def to_json(self, nested=False):
        return {
            "id": self.pk,
            "identifier": self.identifier,
            "item_id": self.item_id,
            "object_type": "fc_category",
            "lang": self.lang,
            "name": self.name,
            "type": self.type,
            "not-in-model": self.not_in_model,
        }

    def __unicode__(self):
        return u"{0.lang} - {0.name}".format(self)


class FlashcardAnswer(Answer):
    FROM_TERM = "t2d"
    FROM_DESCRIPTION = "d2t"
    DIRECTIONS = (
        (FROM_TERM, "From term to description"),
        (FROM_DESCRIPTION, "From description to term"),
    )

    direction = models.CharField(choices=DIRECTIONS, max_length=3)
    options = models.ManyToManyField(Flashcard, related_name="answers_with_this_as_option")

    def to_json(self, nested=False):
        json = Answer.to_json(self)
        json['direction'] = self.direction
        json['object_type'] = "fc_answer"
        if not nested:
            json["options"] = [flashcard.to_json(nested=True) for flashcard in self.options.all()]
        return json


@receiver(pre_save, sender=Term)
@receiver(pre_save, sender=Context)
@receiver(pre_save, sender=Flashcard)
@receiver(pre_save, sender=Category)
@disable_for_loaddata
def create_items(sender, instance, **kwargs):
    if instance.item_id is None and instance.item is None:
        item = Item()
        item.save()
        instance.item = item


PROSO_MODELS_TO_EXPORT = [Category, Flashcard, FlashcardAnswer,
                          settings.PROSO_FLASHCARDS.get("context_extension", Context),
                          settings.PROSO_FLASHCARDS.get("term_extension", Term)]


@receiver(m2m_changed, sender=Category.terms.through)
@receiver(m2m_changed, sender=Category.subcategories.through)
@disable_for_loaddata
def update_parents(sender, instance, action, reverse, model, pk_set, **kwargs):
    environment = get_environment()
    parent_items = []
    child_items = []

    if action == "pre_clear":
        if not reverse:
            parent_items = [instance.item_id]
            children = instance.terms if model == Term else instance.subcategories
            child_items = children.all().values_list("item_id", flat=True)
        else:
            parent_items = instance.parents.all().values_list("item_id", flat=True)
            child_items = [instance.item_id]

    if action == "post_add" and not reverse and instance.not_in_model:
        return

    if action == "post_add" or action == "post_remove":
        if not reverse:
            parent_items = [instance.item_id]
            child_items = model.objects.filter(pk__in=pk_set).values_list("item_id", flat=True)
        else:
            parent_items = Category.objects.filter(pk__in=pk_set, not_in_model=False).values_list("item_id", flat=True)
            child_items = [instance.item_id]

    if action == "post_add":
        for parent_item in parent_items:
            for child_item in child_items:
                environment.write("child", 1, item=parent_item, item_secondary=child_item, symmetric=False,
                                  permanent=True)
                environment.write("parent", 1, item=child_item, item_secondary=parent_item, symmetric=False,
                                  permanent=True)
        return

    if action == "post_remove" or "pre_clear":
        for parent_item in parent_items:
            for child_item in child_items:
                environment.delete("child", item=parent_item, item_secondary=child_item, symmetric=False)
                environment.delete("parent", item=child_item, item_secondary=parent_item, symmetric=False)
        return


def _get_value_without_negation(value):
    if isinstance(value, int):
        return abs(value), value < 0
    else:
        if value is not None and value.startswith('-'):
            return value[1:], True
        else:
            return value, False


def _create_q(column, value):
    value, negation = _get_value_without_negation(value)
    q = Q(**{column: value})
    return ~q if negation else q


@receiver(post_save, sender=Flashcard)
@disable_for_loaddata
def add_parent(sender, instance, **kwargs):
    environment = get_environment()
    parent = instance.term.item_id
    child = instance.item_id
    environment.write("child", 1, item=parent, item_secondary=child, symmetric=False, permanent=True)
    environment.write("parent", 1, item=child, item_secondary=parent, symmetric=False, permanent=True)


@receiver(pre_delete, sender=Flashcard)
@disable_for_loaddata
def delete_parent(sender, instance, **kwargs):
    environment = get_environment()
    parent = instance.term.item_id
    child = instance.item_id
    environment.delete("child", 1, item=parent, item_secondary=child, symmetric=False)
    environment.delete("parent", 1, item=child, item_secondary=parent, symmetric=False)
