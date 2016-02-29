import json
from collections import defaultdict
from hashlib import sha1
from urllib.parse import parse_qs

from django.contrib.auth.models import User
from django.db import models
from django.db.models import Q
from django.db.models.signals import pre_save
from django.dispatch import receiver

from proso.django.util import cache_pure
from proso_flashcards.models import Flashcard
from proso_models.models import Answer


class Tag(models.Model):
    """
    Arbitrary tag for concepts.
    """
    type = models.CharField(max_length=50)
    value = models.CharField(max_length=50)

    class Meta:
        unique_together = ("type", "value")

    def to_json(self, nested=False):
        data = {
            "id": self.pk,
            "object_type": "tag",
            "type": self.type,
            "value": self.value,
        }

        if not nested:
            data["concepts"] = [concept.to_json(nested=True) for concept in self.concepts.all()]

        return data

    def __str__(self):
        return "{}: {}".format(self.type, self.value)


class Concept(models.Model):
    """
    Model concepts for open learner model
    """
    identifier = models.CharField(max_length=20, blank=True)
    query = models.TextField()
    name = models.CharField(max_length=50)
    lang = models.CharField(max_length=2)
    tags = models.ManyToManyField(Tag, related_name="concepts", blank=True)
    active =models.BooleanField(default=True)

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

    @staticmethod
    @cache_pure
    def get_items(concepts=None):
        """
        Get mapping of concepts to items belonging to concept.

        Args:
            concepts (list of Concept): Defaults to None meaning all concepts

        Returns:
            dict: concept (int) -> list of item ids (int)
        """

        # TODO born to be reimplemented, now assuming flashcards
        if concepts is None:
            concepts = Concept.objects.filter(active=True)

        item_lists = {}
        for concept in concepts:
            parameters = {k: json.loads(v[0].replace("'", '"')) for k, v in parse_qs(concept.query).items()}
            _, items = Flashcard.objects.filtered_ids(
                categories=parameters["categories"],
                contexts=parameters["contexts"],
                types=parameters["types"],
                avoid=[],
                language=concept.lang
            )
            item_lists[concept.pk] = items
        return item_lists

    @staticmethod
    @cache_pure
    def get_item_concept_mapping(lang):
        """ Get mapping of items_ids to concepts containing these items
        Args:

            lang (str): language of concepts

        Returns:
            dict: item (int) -> set of concepts (int)

        """
        concepts = Concept.objects.filter(active=True, lang=lang)
        mapping = defaultdict(lambda: set())
        for concept, items in Concept.get_items(concepts).items():
            for item in items:
                mapping[item].add(concept)

        return dict(mapping)

    def __str__(self):
        return self.name

    def __repr__(self):
        return "{}-{}".format(self.identifier, self.lang)


class Action(models.Model):
    """
    Actions which can be done with concept
    """
    concept = models.ForeignKey(Concept, related_name="actions")
    identifier = models.CharField(max_length=50)
    name = models.CharField(max_length=50)
    url = models.CharField(max_length=200)

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


class UserStat(models.Model):
    """
    Represent arbitrary statistic (float) of the user on concept
    """
    concept = models.ForeignKey(Concept)
    user = models.ForeignKey(User, related_name="stats")
    stat = models.CharField(max_length=50)
    time = models.DateTimeField(auto_now=True)
    value = models.FloatField()

    class Meta:
        unique_together = ("concept", "user", "stat")

    def __str__(self):
        return "{} - {}: {}".format(self.user, self.concept, self.value)

    @staticmethod
    def recalculate_concepts(concepts):
        """
        Recalculated given concepts for given users

        Args:
            concepts (dict): user (User or int -> set of concepts to recalculate)
        """
        for user, concepts in concepts.items():
            pass
            # TODO recalculate user stats

    @staticmethod
    def get_user_stats(users, lang, concepts=None):
        """
        Finds all UserStats of given concepts and users.
        Recompute UserStats if necessary

        Args:
            users (Optional[list of users] or [user]): list of primary keys of user or users
                Defaults to None meaning all users.
            lang (string): use only concepts witch the lang
            concepts (Optional[list of concepts]): list of primary keys of concepts or concepts
                Defaults to None meaning all concepts.

        Returns:
            QuerySet: qs of UserStats
        """
        if not isinstance(users, list):
            users = [users]

        concepts_to_recalculate = get_concepts_to_recalculate(users, lang, concepts)
        UserStat.recalculate_concepts(concepts_to_recalculate)

        qs = UserStat.objects.filter(user__in=users)
        if concepts is not None:
            qs = qs.filter(concept__in=concepts)
        if lang is not None:
            qs = qs.filter(concept__lang=lang)
        return qs.select_related("concept")


def get_concepts_to_recalculate(users, lang, concepts=None):
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

    mapping = Concept.get_item_concept_mapping(lang)
    current_user_stats = defaultdict(lambda: {})
    user_stats_qs = UserStat.objects.filter(user__in=users)
    if concepts is not None:
        user_stats_qs = user_stats_qs.filter(concept__in=concepts)
    for user_stat in user_stats_qs:
        current_user_stats[user_stat.pk][user_stat.concept_id] = user_stat

    concepts_to_recalculate = defaultdict(lambda: set())
    for user, item, time in Answer.objects.filter(Q(lang=lang) | Q(lang__isnull=True), user__in=users)\
            .values_list("user_id", "item", "time"):
        if item not in mapping:
            # in reality this should by corner case, so it is efficient to not filter Answers
            continue    # item is not in concept
        for concept in mapping[item]:
            if user in current_user_stats and concept in current_user_stats[user] \
                    and current_user_stats[user][concept].time > time:
                continue    # user stat is actual
            if concepts is None or concept in ([c.pk for c in concepts] if type(concepts[0]) == Concept else Concept):
                concepts_to_recalculate[user].add(concept)

    if only_one_user:
        return concepts_to_recalculate[users[0]]
    return concepts_to_recalculate


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
