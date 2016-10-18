from collections import defaultdict
from datetime import datetime, timedelta
from django.contrib.auth.models import User
from django.db import models
from django.db.models import Q, Count, Sum, Max, Min
from django.db.models.signals import pre_save
from django.dispatch import receiver
from hashlib import sha1
from proso.dict import group_keys_by_value_lists
from proso.django.cache import cache_pure
from proso.list import flatten
from proso_common.models import get_config
from proso_models.models import Answer, Item, get_environment, get_mastery_trashold, get_predictive_model, get_time_for_knowledge_overview
from time import time as time_lib
import json
import logging

LOGGER = logging.getLogger('django.request')


class TagManager(models.Manager):
    def prepare_related(self):
        return self.prefetch_related('concepts')


class Tag(models.Model):
    """
    Arbitrary tag for concepts.
    """
    type = models.CharField(max_length=50)
    value = models.CharField(max_length=200)
    lang = models.CharField(max_length=2)
    type_name = models.CharField(max_length=100)
    value_name = models.CharField(max_length=100)

    objects = TagManager()

    class Meta:
        unique_together = ("type", "value", "lang")

    def to_json(self, nested=False):
        data = {
            "id": self.pk,
            "object_type": "tag",
            "type": self.type,
            "value": self.value,
            "lang": self.lang,
            "type_name": self.type_name,
            "value_name": self.value_name,
        }

        if not nested:
            data["concepts"] = [concept.to_json(nested=True) for concept in self.concepts.all()]

        return data

    def __str__(self):
        return "{}: {}".format(self.type, self.value)


class ConceptManager(models.Manager):
    def prepare_related(self):
        return self.prefetch_related('tags', 'actions')

    @cache_pure()
    def get_concept_item_mapping(self, concepts=None, lang=None):
        """
        Get mapping of concepts to items belonging to concept.

        Args:
            concepts (list of Concept): Defaults to None meaning all concepts
            lang (str): language of concepts, if None use language of concepts

        Returns:
            dict: concept (int) -> list of item ids (int)
        """
        if concepts is None:
            concepts = self.filter(active=True)
            if lang is not None:
                concepts = concepts.filter(lang=lang)
        if lang is None:
            languages = set([concept.lang for concept in concepts])
            if len(languages) > 1:
                raise Exception('Concepts has multiple languages')
            lang = list(languages)[0]
        item_lists = Item.objects.filter_all_reachable_leaves_many([json.loads(concept.query)
                                                                    for concept in concepts], lang)
        return dict(zip([c.pk for c in concepts], item_lists))

    @cache_pure()
    def get_item_concept_mapping(self, lang):
        """ Get mapping of items_ids to concepts containing these items

        Args:
            lang (str): language of concepts

        Returns:
            dict: item (int) -> set of concepts (int)

        """
        concepts = self.filter(active=True, lang=lang)
        return group_keys_by_value_lists(Concept.objects.get_concept_item_mapping(concepts, lang))

    def get_concepts_to_recalculate(self, users, lang, concepts=None):
        """
        Get concept which have same changes and have to be recalculated

        Args:
            users (list of users or user): users whose user stats we are interesting in
            lang (str): language of used concepts
            concepts (Optional[list of concepts]): list of primary keys of concepts or concepts
                Defaults to None meaning all concepts.

        Returns:
            dict: user -> set of concepts (int) - in case of list of users
            list of stats (str) - in case of one user
        """
        only_one_user = False
        if not isinstance(users, list):
            only_one_user = True
            users = [users]

        mapping = self.get_item_concept_mapping(lang)
        current_user_stats = defaultdict(lambda: {})
        user_stats_qs = UserStat.objects.filter(user__in=users, stat="answer_count")     # we need only one type
        if concepts is not None:
            user_stats_qs = user_stats_qs.filter(concept__in=concepts)
        for user_stat in user_stats_qs:
            current_user_stats[user_stat.user_id][user_stat.concept_id] = user_stat

        concepts_to_recalculate = defaultdict(lambda: set())
        for user, item, time in Answer.objects.filter(user__in=users)\
                .values_list("user_id", "item").annotate(Max("time")):
            if item not in mapping:
                # in reality this should by corner case, so it is efficient to not filter Answers
                continue    # item is not in concept
            time_expiration_lower_bound = get_config('proso_models', 'knowledge_overview.time_shift_hours', default=4)
            time_expiration_factor = get_config('proso_models', 'knowledge_overview.time_expiration_factor', default=2)
            for concept in mapping[item]:
                if user in current_user_stats and concept in current_user_stats[user] \
                        and current_user_stats[user][concept].time > time:
                    if not self.has_time_expired(current_user_stats[user][concept].time, time, time_expiration_lower_bound, time_expiration_factor):
                        continue  # cache is up to date

                if concepts is None or concept in ([c.pk for c in concepts] if type(concepts[0]) == Concept else Concept):
                    concepts_to_recalculate[user].add(concept)

        if only_one_user:
            return concepts_to_recalculate[users[0]]
        return concepts_to_recalculate

    def has_time_expired(self, cache_time, last_answer_time, lower_bound, expiration_factor):
        cache_timedelta = cache_time - last_answer_time
        if cache_timedelta > timedelta(days=365):
            return False
        if cache_timedelta < timedelta(hours=lower_bound):
            return False
        return cache_timedelta < expiration_factor * (datetime.now() - cache_time)


class Concept(models.Model):
    """
    Model concepts for open learner model
    """
    identifier = models.CharField(max_length=20, blank=True)
    query = models.TextField()
    name = models.CharField(max_length=200)
    lang = models.CharField(max_length=2)
    tags = models.ManyToManyField(Tag, related_name="concepts", blank=True)
    active = models.BooleanField(default=True)

    objects = ConceptManager()

    class Meta:
        unique_together = ("identifier", "lang")

    def to_json(self, nested=False):
        data = {
            "id": self.pk,
            "object_type": "concept",
            "identifier": self.identifier,
            "name": self.name,
            "query": self.query,
            "lang": self.lang,
        }
        if not nested:
            data["tags"] = [tag.to_json(nested=True) for tag in self.tags.all()]
            data["actions"] = [action.to_json(nested=True) for action in self.actions.all()]

        return data

    @staticmethod
    def create_identifier(query):
        """
        Crete identifier of concept

        Args:
            query (str): query defining concept

        Returns:
            str: identifier of length 20
        """
        return sha1(query.encode()).hexdigest()[:20]

    def __str__(self):
        return self.name

    def __repr__(self):
        return "{}-{}".format(self.identifier, self.lang)


class ActionManager(models.Manager):
    def prepare_related(self):
        return self.select_related('concept')


class Action(models.Model):
    """
    Actions which can be done with concept
    """
    concept = models.ForeignKey(Concept, related_name="actions")
    identifier = models.CharField(max_length=50)
    name = models.CharField(max_length=200)
    url = models.CharField(max_length=200)

    objects = ActionManager()

    def to_json(self, nested=False):
        data = {
            "id": self.pk,
            "object_type": "action",
            "identifier": self.identifier,
            "name": self.name,
            "url": self.url,
        }

        if not nested:
            data["concept"] = self.concept.to_json(nested=True)

        return data

    def __str__(self):
        return "{} - {}".format(self.concept, self.name)


class UserStatManager(models.Manager):
    def prepare_related(self):
        return self.select_related('concept')

    def recalculate_concepts(self, concepts, lang=None):
        """
        Recalculated given concepts for given users

        Args:
            concepts (dict): user id (int -> set of concepts to recalculate)
            lang(Optional[str]): language used to get items in all concepts (cached).
                Defaults to None, in that case are get items only in used concepts
        """
        if len(concepts) == 0:
            return

        if lang is None:
            items = Concept.objects.get_concept_item_mapping(concepts=Concept.objects.filter(pk__in=set(flatten(concepts.values()))))
        else:
            items = Concept.objects.get_concept_item_mapping(lang=lang)

        environment = get_environment()
        mastery_threshold = get_mastery_trashold()
        for user, concepts in concepts.items():
            all_items = list(set(flatten([items[c] for c in concepts])))
            answer_counts = environment.number_of_answers_more_items(all_items, user)
            correct_answer_counts = environment.number_of_correct_answers_more_items(all_items, user)
            predictions = dict(list(zip(all_items, get_predictive_model().
                                        predict_more_items(environment, user, all_items, time=get_time_for_knowledge_overview()))))
            new_user_stats = []
            stats_to_delete_condition = Q()
            for concept in concepts:
                answer_aggregates = Answer.objects.filter(user=user, item__in=items[concept]).aggregate(
                    time_spent=Sum("response_time"),
                    sessions=Count("session", True),
                    time_first=Min("time"),
                    time_last=Max("time"),
                )
                stats = {
                    "answer_count": sum(answer_counts[i] for i in items[concept]),
                    "correct_answer_count": sum(correct_answer_counts[i] for i in items[concept]),
                    "item_count": len(items[concept]),
                    "practiced_items_count": sum([answer_counts[i] > 0 for i in items[concept]]),
                    "mastered_items_count": sum([predictions[i] >= mastery_threshold for i in items[concept]]),
                    "prediction": sum([predictions[i] for i in items[concept]]) / len(items[concept]),
                    "time_spent": answer_aggregates["time_spent"] / 1000,
                    "session_count": answer_aggregates["sessions"],
                    "time_first": answer_aggregates["time_first"].timestamp(),
                    "time_last": answer_aggregates["time_last"].timestamp(),
                }
                stats_to_delete_condition |= Q(user=user, concept=concept)
                for stat_name, value in stats.items():
                    new_user_stats.append(UserStat(user_id=user, concept_id=concept, stat=stat_name, value=value))
            self.filter(stats_to_delete_condition).delete()
            self.bulk_create(new_user_stats)

    def get_user_stats(self, users, lang=None, concepts=None, since=None, recalculate=True):
        """
        Finds all UserStats of given concepts and users.
        Recompute UserStats if necessary

        Args:
            users (Optional[list of users] or [user]): list of primary keys of user or users
                Defaults to None meaning all users.
            lang (string): use only concepts witch the lang. Defaults to None meaning all languages.
            concepts (Optional[list of concepts]): list of primary keys of concepts or concepts
                Defaults to None meaning all concepts.

        Returns:
            dict: user_id  -> dict (concept_identifier - > (stat_name  -> value)) -- for more users
            dict: concept_identifier - > (stat_name  -> value) -- for one user
        """
        only_one_user = False
        if not isinstance(users, list):
            users = [users]
            only_one_user = True

        if recalculate:
            if lang is None:
                raise ValueError('Recalculation without lang is not supported.')
            time_start = time_lib()
            concepts_to_recalculate = Concept.objects.get_concepts_to_recalculate(users, lang, concepts)
            LOGGER.debug("user_stats - getting identifying concepts to recalculate: %ss", (time_lib() - time_start))
            time_start = time_lib()
            self.recalculate_concepts(concepts_to_recalculate, lang)
            LOGGER.debug("user_stats - recalculating concepts: %ss", (time_lib() - time_start))

        qs = self.prepare_related().filter(user__in=users, concept__active=True)
        if concepts is not None:
            qs = qs.filter(concept__in=concepts)
        if lang is not None:
            qs = qs.filter(concept__lang=lang)
        if since is not None:
            qs = qs.filter(time__gte=since)

        data = defaultdict(lambda: defaultdict(lambda: {}))
        for user_stat in qs:
            data[user_stat.user_id][user_stat.concept.identifier][user_stat.stat] = user_stat.value
        if only_one_user:
            return data[users[0].pk if type(users[0]) == User else users[0]]
        return data


class UserStat(models.Model):
    """
    Represent arbitrary statistic (float) of the user on concept
    """
    concept = models.ForeignKey(Concept)
    user = models.ForeignKey(User, related_name="stats")
    stat = models.CharField(max_length=50)
    time = models.DateTimeField(auto_now=True)
    value = models.FloatField()

    objects = UserStatManager()

    class Meta:
        unique_together = ("concept", "user", "stat")

    def __str__(self):
        return "{} - {}: {}".format(self.stat, self.concept, self.value)


@receiver(pre_save, sender=Concept)
def generate_identifier(sender, instance, **kwargs):
    """
    Generate and set identifier of concept before saving object to DB

    Args:
        sender (class): should be Concept
        instance (Concept): saving concept
    """
    identifier = Concept.create_identifier(instance.query)
    qs = Concept.objects.filter(identifier=identifier, lang=instance.lang)
    if instance.pk:
        qs = qs.exclude(pk=instance.pk)
    if qs.count() > 0:
        raise ValueError("Concept identifier conflict")
    instance.identifier = identifier
