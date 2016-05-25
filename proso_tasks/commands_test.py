from django.core.management import call_command
from proso.django.test import TestCase
from proso_tasks.models import Task, TaskInstance, Skill, Context


class LoadTasksTest(TestCase):

    def test_load(self):
        call_command('load_tasks', 'testproject/test_data/tasks/tasks.json')
        self.assertEquals(Skill.objects.all().count(), 2 * 4, "All skills are loaded.")
        self.assertEquals(Context.objects.all().count(), 2, "All contexts are loaded.")
        self.assertEquals(Task.objects.all().count(), 2 * 2, "All tasks are created.")
        self.assertEquals(TaskInstance.objects.all().count(), 2 * 2, "All isntances are created.")
