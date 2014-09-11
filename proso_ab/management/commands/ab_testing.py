# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand, CommandError
from proso_ab.models import Experiment
from optparse import make_option


class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option(
            '--command-help',
            action='store_true',
            dest='command_help',
            help='shows helps for the given command',
        ),
    )

    args = '<command> [command arguments]'

    help = '''
    ----------------------------------------------------------------------------
    command for manipulation with A/B testing groups and values

    the following subcommands are available
        * disable
        * enable
        * init

    to print more help use the following command:

        python manage.py ab_testing <command> --comand-help
    ----------------------------------------------------------------------------
            '''

    def handle(self, *args, **options):
        if not len(args):
            raise CommandError(Command.help)
        command = args[0]
        command_args = args[1:]
        if command == 'disable':
            return self.enable_disable(command_args, options, False)
        elif command == 'enable':
            return self.enable_disable(command_args, options, True)
        elif command == 'init':
            return self.init(command_args, options)
        else:
            raise CommandError('unknow command: ' + command)

    def enable_disable(self, args, options, active):
        if options.get('command_help', False):
            print self.help_enable_disable()
            return
        name = args[0]
        experiment = Experiment.objects.get(name=name)
        experiment.active = active
        experiment.save()

    def init(self, args, options):
        if options.get('command_help', False):
            print self.help_init()
            return
        values = []
        (group_name, default_value) = args[0].split('=')
        prob_value_pairs = args[1:]
        for arg in prob_value_pairs:
            (value, probability) = arg.split('=')
            probability = int(probability.strip())
            value = value.strip()
            values.append((probability, value))
        Experiment.objects.new_experiment(
            group_name,
            values,
            default_value)

    def help_enable_disable(self):
        return '''
    enable/disable the given group

        ./manage.py ab_testing [enable|disable] <group name>
                '''

    def help_init(self):
        return '''
    initilize a new A/B testing group with its values

        ./manage.py ab_testing init <group name>=<default value> [<value>=<percentige>]
                '''
