from clint.textui import progress
from django.core.cache import cache
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from jsonschema import validate
import json
import os

from proso_models.models import Item
from proso_tasks.models import Skill, Task, Context, TaskInstance


class Command(BaseCommand):
    help = "Load tasks from JSON file"

    def add_arguments(self, parser):
        parser.add_argument('filename', nargs='+', type=str)

    def handle(self, *args, **options):
        with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "schema.json"), "r", encoding='utf8') as schema_file:
            schema = json.load(schema_file)
        with transaction.atomic():
            for filename in options['filename']:
                with open(filename, 'r', encoding='utf8') as json_file:
                    data = json.load(json_file)
                    validate(data, schema)
                    if "skills" in data:
                        self._load_skills(data["skills"])
                    if "contexts" in data:
                        self._load_contexts(data["contexts"])
                    if "tasks" in data:
                        self._load_tasks(data["tasks"])
                    if "instances" in data:
                        self._load_instances(data["instances"])
            self.stdout.write('Filling item types')
            call_command('fill_item_types')
            self.stdout.write(self.style.SUCCESS('All work is finished'))
            cache.clear()

    def _load_skills(self, skills):
        self.stdout.write('Loading skills')

        self.stdout.write('- objects')
        db_skills = {(skill.identifier, skill.lang): skill for skill in Skill.objects.all().select_related('item')}
        items = {}
        for skill in progress.bar(skills, every=max(1, len(skills) // 100)):
            new_skills = {}
            for lang, name in skill['names'].items():
                new_skills[(skill['id'], lang)] = {"name": name, 'active': True if 'active' not in skill else skill['active']}
            items[skill['id']] = (self._update_or_create_objects(Skill, db_skills, new_skills, ["name", "active"]),
                                  [] if 'parents' not in skill else skill['parents'])

        self.stdout.write('- item relations')
        parent_subgraph = {}
        for item, parents in items.values():
            parent_subgraph[item.pk] = [items[parent][0].pk for parent in parents]
        Item.objects.override_parent_subgraph(parent_subgraph)

        self.stdout.write(self.style.SUCCESS('Skills loaded \n'))

    def _load_tasks(self, tasks):
        self.stdout.write('Loading tasks')

        self.stdout.write('- objects')
        db_tasks = {(task.identifier, task.lang): task for task in Task.objects.all().select_related('item')}
        items = {}
        for task in progress.bar(tasks, every=max(1, len(tasks) // 100)):
            new_tasks = {}
            for lang, content in task['contents'].items():
                new_tasks[(task['id'], lang)] = {"content": content, 'active': True if 'active' not in task else task['active']}
            items[task['id']] = (self._update_or_create_objects(Task, db_tasks, new_tasks, ["content", "active"]),
                                 [] if 'skills' not in task else task['skills'])

        self.stdout.write('- item relations')
        skill_items = {skill.identifier: skill.item_id for skill in Skill.objects.all()}
        parent_subgraph = {}
        for item, parents in items.values():
            parent_subgraph[item.pk] = [skill_items[parent] for parent in parents]
        Item.objects.override_parent_subgraph(parent_subgraph)

        self.stdout.write(self.style.SUCCESS('Tasks loaded \n'))

    def _load_contexts(self, contexts):
        self.stdout.write('Loading contexts')

        self.stdout.write('- objects')
        db_tasks = {(context.identifier, context.lang): context
                    for context in Context.objects.all().select_related('item')}
        items = {}
        for context in progress.bar(contexts, every=max(1, len(contexts) // 100)):
            new_contexts = {}
            for lang, name in context['names'].items():
                new_contexts[(context['id'], lang)] = {"name": name, "content": context["contents"][lang], 'active': True if 'active' not in context else context['active']}
            items[context['id']] = self._update_or_create_objects(Context, db_tasks,
                                                                  new_contexts, ["name", "content", "active"]), []

        self.stdout.write(self.style.SUCCESS('Contexts loaded \n'))

    def _load_instances(self, instances):
        self.stdout.write('Loading instances')

        tasks = {(task.identifier, task.lang): task for task in Task.objects.all()}
        contexts = {(context.identifier, context.lang): context for context in Context.objects.all()}
        task_items = {task.identifier: task.item_id for task in tasks.values()}
        context_items = {context.identifier: context.item_id for context in contexts.values()}

        self.stdout.write('- objects')
        db_instances = {(task.identifier, task.lang): task for task in
                        TaskInstance.objects.all().select_related('item')}
        parent_subgraph = {}
        invisible_edges = []
        for instance in progress.bar(instances, every=max(1, len(instances) // 100)):
            new_instances = {}
            for lang, description in instance['descriptions'].items():
                new_instances[(instance['id'], lang)] = {
                    'description': description,
                    'task': tasks[(instance['task'], lang)],
                    'context': contexts[(instance['context'], lang)],
                    'active': True if 'active' not in instance else instance['active']
                }
            item = self._update_or_create_objects(TaskInstance, db_instances, new_instances,
                                                  ["description", "task", "context", 'active'])
            parent_subgraph[item.pk] = [task_items[instance['task']], context_items[instance['context']]]
            invisible_edges.append((item.pk, context_items[instance['context']]))

        self.stdout.write('- item relations')
        Item.objects.override_parent_subgraph(parent_subgraph, invisible_edges=invisible_edges)

        self.stdout.write(self.style.SUCCESS('Instances loaded \n'))

    def _update_or_create_objects(self, cls, currents, new, params):
        item = None
        to_create = []
        for (identifier, lang), obj in new.items():
            if (identifier, lang) in currents:
                current = currents[(identifier, lang)]
                if item is not None and item != current.item:
                    raise CommandError('Invalid item for {}'.format(current))
                item = current.item
                changed = False
                for param in params:
                    if getattr(current, param) != obj[param]:
                        setattr(current, param, obj[param])
                        changed = True
                if changed:
                    current.save()
            else:
                to_create.append(((identifier, lang), obj))

        if item is None:
            item = Item(active='active' not in params or list(new.values())[0]['active'])
            item.save()

        new_objects = []
        for (identifier, lang), obj in to_create:
            kwargs = {'item': item, 'identifier': identifier, "lang": lang}
            for param in params:
                kwargs[param] = obj[param]
            new_objects.append(cls(**kwargs))
        cls.objects.bulk_create(new_objects)

        return item
