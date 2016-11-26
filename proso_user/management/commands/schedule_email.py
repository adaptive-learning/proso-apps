from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
from proso_user.models import ScheduledEmail
import os


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option(
            '--skip-email',
            dest='skip_emails',
            action='append',
            default=[]
        ),
        make_option(
            '--email',
            dest='emails',
            action='append',
            default=[]
        ),
        make_option(
            '--template-file',
            dest='template_file'
        ),
        make_option(
            '--from-email',
            dest='from_email'
        ),
        make_option(
            '--subject',
            dest='subject'
        ),
        make_option(
            '--lang',
            dest='langs',
            action='append',
            default=[]
        ),
    )

    def handle(self, *args, **options):
        if options['template_file'] is None or options['subject'] is None or options['from_email'] is None:
            raise CommandError('Template file, subject and FROM e-mail have to be specified.')
        users = ScheduledEmail.objects.schedule_more(
            options['from_email'], options['subject'], os.path.realpath(options['template_file']),
            emails=None if len(options['emails']) == 0 else options['emails'],
            skip_emails=None if len(options['skip_emails']) == 0 else options['skip_emails'],
            langs=None if len(options['langs']) == 0 else options['langs']
        )
        if options['verbosity'] > 1:
            print('E-mail scheduled for:')
            for user in users:
                print('    ', user.email)
