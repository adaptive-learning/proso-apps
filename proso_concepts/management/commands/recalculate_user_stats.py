from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from time import time as time_lib

from social.apps.django_app.default.models import UserSocialAuth

from proso_concepts.models import Concept, UserStat


class Command(BaseCommand):
    help = "Recalculate student stats for new data of group of students"

    def __init__(self, stdout=None, stderr=None, no_color=False):
        super().__init__(stdout=None, stderr=None, no_color=False)
        self.tags = {}
        self.concepts = {}

    def add_arguments(self, parser):
        parser.add_argument('user_group', nargs=1, type=str)

    def handle(self, *args, **options):
        user_group = options['user_group'][0]
        print(user_group)
        if user_group == 'edookit':
            users = list(User.objects.filter(social_auth__provider='edookit'))
        else:
            raise Exception('Unknown user group "{}"'.format(user_group))

        lang = settings.LANGUAGES[0][0]

        time_start = time_lib()
        self.stdout.write("Users: {}".format(len(users)))
        concepts_to_recalculate = Concept.objects.get_concepts_to_recalculate(users, lang)
        self.stdout.write("Identifying concepts to recalculate: {}s".format((time_lib() - time_start)))

        time_start = time_lib()
        self.stdout.write("Concepts to recalculate: {}".format(sum(map(len, concepts_to_recalculate.values()))))
        UserStat.objects.recalculate_concepts(concepts_to_recalculate, lang)
        self.stdout.write("Recalculating concepts: {}s".format(time_lib() - time_start))

        if user_group == 'edookit':
            # TODO remember last successful push time and push all newer stats, no only just recalculated
            for user, concepts in concepts_to_recalculate.items():
                if len(concepts) == 0:
                    continue
                UserStat.objects.filter(user=user, concept__in=concepts)
                user = UserSocialAuth.objects.get(provider='edookit', user_id=user)
                self.stdout.write("Pushing stats about {} concepts for user {}".format(len(concepts), user))
                # TODO push info to edookit
