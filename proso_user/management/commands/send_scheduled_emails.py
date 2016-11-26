from django.core.management.base import BaseCommand
from proso_user.models import ScheduledEmail
from optparse import make_option


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option(
            '--n',
            dest='n',
            action='store',
            default=100
        ),
        make_option(
            '--auth-user',
            dest='auth_user',
            action='store',
            default=None
        ),
        make_option(
            '--auth-password',
            dest='auth_password',
            action='store',
            default=None
        ),
    )

    def handle(self, *args, **options):
        ScheduledEmail.objects.send(
            n=options['n'],
            auth_user=options['auth_user'],
            auth_password=options['auth_password']
        )
