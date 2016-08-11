from jsonfield import JSONField
from django.db import models
from proso.django.models import ModelDiffMixin
from proso_models.models import Item, ItemRelation, Answer
from django.db.models.signals import pre_save, post_save, pre_delete
from django.dispatch import receiver
from proso.django.models import disable_for_loaddata
import logging


LOGGER = logging.getLogger('django.request')


class TaskManager(models.Manager):

    def prepare_related(self):
        return self


class Task(models.Model, ModelDiffMixin):
    identifier = models.SlugField()
    item = models.ForeignKey(Item, null=True, default=None, related_name="task_tasks")
    lang = models.CharField(max_length=2)
    content = JSONField()
    active = models.BooleanField(default=True)

    objects = TaskManager()

    class Meta:
        unique_together = ('identifier', 'lang')

    def to_json(self, nested=False):
        json = {
            "id": self.pk,
            "identifier": self.identifier,
            "item_id": self.item_id,
            "object_type": "task_task",
            "lang": self.lang,
            "content": self.content,
        }

        return json

    def __str__(self):
        return "Task {0.pk} ({0.lang})".format(self)


class ContextManager(models.Manager):

    def prepare_related(self):
        return self


class Context(models.Model, ModelDiffMixin):
    identifier = models.SlugField()
    item = models.ForeignKey(Item, null=True, default=None, related_name="task_contexts")
    lang = models.CharField(max_length=2)
    name = models.TextField()
    content = JSONField(null=True, blank=True)
    active = models.BooleanField(default=True)

    objects = ContextManager()

    class Meta:
        unique_together = ('identifier', 'lang')

    def to_json(self, nested=False, with_content=True):
        json = {
            "id": self.pk,
            "identifier": self.identifier,
            "item_id": self.item_id,
            "object_type": "task_context",
            "lang": self.lang,
            "name": self.name,
        }
        if with_content:
            json['content'] = self.content
        return json

    def __str__(self):
        return "{0.name} ({0.lang})".format(self)


class TaskInstanceManager(models.Manager):

    def prepare_related(self):
        return self.select_related('context', 'task')


class TaskInstance(models.Model, ModelDiffMixin):
    identifier = models.SlugField()
    item = models.ForeignKey(Item, null=True, default=None, related_name="task_instances")
    lang = models.CharField(max_length=2)
    task = models.ForeignKey(Task, related_name="instances")
    context = models.ForeignKey(Context, related_name="instances")
    description = JSONField(null=True, blank=True)
    active = models.BooleanField(default=True)

    objects = TaskInstanceManager()

    class Meta:
        unique_together = ('identifier', 'lang')

    def to_json(self, nested=False, contexts=True):
        data = {
            "id": self.pk,
            "identifier": self.identifier,
            "item_id": self.item_id,
            "object_type": "task_instance",
            "active": self.active,
            "lang": self.lang,
            "task": self.task.to_json(nested=True),
            "description": self.description
        }
        if not nested and contexts:
            data["context"] = self.context.to_json(nested=True)
        else:
            data["context_id"] = self.context_id
        return data

    def __str__(self):
        return "{0.task} - {0.context}".format(self)


class SkillManager(models.Manager):

    def prepare_related(self):
        return self


class Skill(models.Model, ModelDiffMixin):
    identifier = models.SlugField()
    item = models.ForeignKey(Item, null=True, default=None, related_name="task_skills")
    lang = models.CharField(max_length=2)
    name = models.TextField()
    active = models.BooleanField(default=True)

    objects = SkillManager()

    class Meta:
        unique_together = ('identifier', 'lang')

    def to_json(self, nested=False):
        json = {
            "id": self.pk,
            "identifier": self.identifier,
            "item_id": self.item_id,
            "object_type": "task_skill",
            "lang": self.lang,
            "name": self.name,
        }
        return json

    def __str__(self):
        return "{0.name} ({0.lang})".format(self)


class TaskAnswerManager(models.Manager):

    def prepare_related(self):
        return self.select_related('context', 'metainfo')

    def from_json(self, json_object, practice_context, practice_set, user_id):
        json_object = dict(json_object)
        task_instance = TaskInstance.objects.get(pk=json_object['task_instance_id'])
        json_object['item_id'] = task_instance.item_id
        json_object['item_asked_id'] = task_instance.item_id
        json_object['item_answered_id'] = task_instance.item_id if json_object['correct'] else None
        json_object['lang'] = task_instance.lang
        answer = Answer.objects.from_json(json_object, practice_context, practice_set, user_id, object_class=TaskAnswer)
        if 'question' in json_object:
            answer.question = json_object['question']
        if 'answer' in json_object:
            answer.answer = json_object['answer']
        answer.save()
        return answer


class TaskAnswer(Answer):
    question = models.CharField(max_length=255, null=True, blank=True)
    answer = models.CharField(max_length=255, null=True, blank=True)

    objects = TaskAnswerManager()

    def to_json(self, nested=False):
        json = Answer.to_json(self, nested=nested)
        json['object_type'] = "task_answer"
        return json


@receiver(pre_save, sender=Task)
@receiver(pre_save, sender=Context)
@receiver(pre_save, sender=TaskInstance)
@receiver(pre_save, sender=Skill)
@disable_for_loaddata
def create_items(sender, instance, **kwargs):
    """
    When one of the defined objects is created, initialize also its item.
    """
    if instance.item_id is None and instance.item is None:
        item = Item()
        if hasattr(instance, 'active'):
            item.active = getattr(instance, 'active')
        item.save()
        instance.item = item


@receiver(pre_save, sender=Task)
@receiver(pre_save, sender=Context)
@receiver(pre_save, sender=TaskInstance)
@receiver(pre_save, sender=Skill)
@disable_for_loaddata
def change_activity(sender, instance, **kwargs):
    if 'active' in instance.diff:
        instance.item.active = instance.active
        instance.item.save()


@receiver(post_save, sender=TaskInstance)
@disable_for_loaddata
def add_parent(sender, instance, **kwargs):
    """
    When a task instance is created, create also an item relation.
    """
    if not kwargs['created']:
        return
    for att in ['task', 'context']:
        parent = getattr(instance, att).item_id
        child = instance.item_id
        ItemRelation.objects.get_or_create(
            parent_id=parent,
            child_id=child,
            visible=True,
        )


@receiver(pre_save, sender=TaskInstance)
@disable_for_loaddata
def change_parent(sender, instance, **kwargs):
    """
    When the given task instance has changed. Look at task and context and change
    the corresponding item relation.
    """
    if instance.id is None:
        return
    if len({'task', 'task_id'} & set(instance.changed_fields)) != 0:
        diff = instance.diff
        parent = diff['task'][0] if 'task' in diff else diff['task_id'][0]
        parent_id = parent.item_id if isinstance(parent, Task) else Task.objects.get(pk=parent).item_id
        child_id = instance.item_id
        ItemRelation.objects.filter(parent_id=parent_id, child_id=child_id).delete()
        ItemRelation.objects.create(parent_id=instance.task.item_id, child_id=child_id, visible=True)
    if len({'context', 'context_id'} & set(instance.changed_fields)) != 0:
        diff = instance.diff
        parent = diff['context'][0] if 'context' in diff else diff['context_id'][0]
        parent_id = parent.item_id if isinstance(parent, Context) else Context.objects.get(pk=parent).item_id
        child_id = instance.item_id
        ItemRelation.objects.filter(parent_id=parent_id, child_id=child_id).delete()
        ItemRelation.objects.create(parent_id=instance.context.item_id, child_id=child_id, visible=False)


@receiver(pre_delete, sender=TaskInstance)
@disable_for_loaddata
def delete_parent(sender, instance, **kwargs):
    """
    When the given task instance is deleted, delete also the corresponding item
    relations.
    """
    ItemRelation.objects.filter(child_id=instance.item_id).delete()
