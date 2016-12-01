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
            '--skip-emails-file',
            dest='skip_emails_file',
            default=None
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
            dest='subjects',
            action='append',
            default=[]
        ),
        make_option(
            '--lang',
            dest='langs',
            action='append',
            default=[]
        ),
        make_option(
            '--output',
            dest='output_dir',
            default=None
        ),
        make_option(
            '--dry',
            dest='dry',
            action='store_true',
            default=False
        ),
        make_option(
            '--active-from',
            dest='active_from',
            default=None
        )
    )

    def handle(self, *args, **options):
        if options['template_file'] is None or len(options['subjects']) == 0 or options['from_email'] is None:
            raise CommandError('Template file, subject and FROM e-mail have to be specified.')
        if len(options['langs']) > 0:
            subjects = {sub.split(':')[0]: ':'.join(sub.split(':')[1:]) for sub in options['subjects']}
            for lang in options['langs']:
                if lang not in subjects:
                    raise CommandError('There is no subject for language "{}", please specify it as --subject <LANG>:<SUBJECT>.'.format(lang))
            to_process = [(lang, subjects[lang], options['template_file'].format(lang)) for lang in options['langs']]
        else:
            template_file = options['template_file']
            subject = options['subjects'][0]
            to_process = [(None, subject, template_file)]
        skip_emails = list(options['skip_emails'])
        if options['skip_emails_file'] is not None:
            with open(os.path.realpath(options['skip_emails_file']), 'r') as f:
                skip_emails.append(f.readlines())
        for lang, subject, template_file in to_process:
            if options['dry']:
                print()
            users = ScheduledEmail.objects.schedule_more(
                options['from_email'],
                subject,
                os.path.realpath(template_file),
                emails=None if len(options['emails']) == 0 else options['emails'],
                skip_emails=None if len(skip_emails) == 0 else skip_emails,
                langs=None if lang is None else [lang],
                output_dir=None if options['output_dir'] is None else os.path.realpath(options['output_dir']),
                dry=options['dry'],
                active_from=options['active_from']
            )
            for user in users:
                skip_emails.append(user.email)
            if options['verbosity'] > 1:
                print()
                if len(users) == 0:
                    print('No e-mail [{}] "{}" scheduled'.format(subject, template_file))
                else:
                    print('E-mail [{}] "{}" scheduled for:'.format(subject, template_file))
                for user in users:
                    print('    ', user.email)
