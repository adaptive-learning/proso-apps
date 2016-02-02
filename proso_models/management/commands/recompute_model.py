from django.core.management.base import BaseCommand, CommandError
from contextlib import closing
from django.db import connection
from optparse import make_option
from proso_common.models import Config
from proso_models.models import EnvironmentInfo, ENVIRONMENT_INFO_CACHE_KEY
from proso.django.config import instantiate_from_config, set_default_config_name, get_config
from django.db import transaction
from proso.util import timer
from proso_models.models import get_predictive_model
from clint.textui import progress
from django.core.cache import cache


class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option(
            '--initial',
            dest='initial',
            action='store_true',
            default=False),
        make_option(
            '--config-name',
            dest='config_name',
            type=str,
            default='default'),
        make_option(
            '--batch-size',
            dest='batch_size',
            type=int,
            default=100000),
        make_option(
            '--cancel',
            dest='cancel',
            action='store_true',
            default=False),
        make_option(
            '--garbage-collector',
            dest='garbage_collector',
            action='store_true',
            default=False),
        make_option(
            '--finish',
            dest='finish',
            action='store_true',
            default=False),
    )

    def handle(self, *args, **options):
        if options['cancel']:
            self.handle_cancel(options)
        elif options['garbage_collector']:
            self.handle_gc(options)
        else:
            self.handle_recompute(options)

    def handle_gc(self, options):
        timer('recompute_gc')
        print(' -- collecting garbage')
        to_gc = [str(x.id) for x in EnvironmentInfo.objects.filter(status=EnvironmentInfo.STATUS_DISABLED).all()]
        if not to_gc:
            print(' -- no environment info to collect')
            return
        to_gc_str = ','.join(to_gc)
        with closing(connection.cursor()) as cursor:
            cursor.execute('DELETE FROM proso_models_variable WHERE info_id IN (%s)' % to_gc_str)
            variables = cursor.rowcount
            cursor.execute('DELETE FROM proso_models_audit WHERE info_id IN (%s)' % to_gc_str)
            audits = cursor.rowcount
            cursor.execute('DELETE FROM proso_models_environmentinfo WHERE id IN (%s)' % to_gc_str)
            infos = cursor.rowcount
        print(' -- collecting garbage, time:', timer('recompute_gc'), 'seconds, deleted', variables, 'variables,', audits, 'audit records,', infos, 'environment info records')

    def handle_cancel(self, options):
        info = self.load_environment_info(False, options['config_name'])
        print(' -- cancelling')
        info.status = EnvironmentInfo.STATUS_DISABLED
        info.save()

    def handle_recompute(self, options):
        timer('recompute_all')
        info = self.load_environment_info(options['initial'], options['config_name'])
        if options['finish']:
            with transaction.atomic():
                to_process = self.number_of_answers_to_process(info)
                if self.number_of_answers_to_process(info) >= options['batch_size']:
                    raise CommandError("There is more then allowed number of answers (%s) to process." % to_process)
                self.recompute(info, options)
        else:
            self.recompute(info, options)
        print(' -- total time:', timer('recompute_all'), 'seconds')

    def recompute(self, info, options):
        print(' -- preparing phase')
        timer('recompute_prepare')
        environment = self.load_environment(info)
        users, items = self.load_user_and_item_ids(info, options['batch_size'])
        environment.prefetch(users, items)
        predictive_model = get_predictive_model()
        print(' -- preparing phase, time:', timer('recompute_prepare'), 'seconds')
        timer('recompute_model')
        print(' -- model phase')
        with closing(connection.cursor()) as cursor:
            cursor.execute(
                '''
                SELECT
                    id,
                    user_id,
                    item_id,
                    item_asked_id,
                    item_answered_id,
                    time,
                    response_time,
                    guess
                FROM proso_models_answer
                ORDER BY id
                OFFSET %s LIMIT %s
                ''', [info.load_progress, options['batch_size']])
            progress_bar = progress.bar(cursor, every=max(1, cursor.rowcount / 100), expected_size=cursor.rowcount)
            info.load_progress += cursor.rowcount
            for (answer_id, user, item, asked, answered, time, response_time, guess) in progress_bar:
                predictive_model.predict_and_update(
                    environment,
                    user,
                    item,
                    asked == answered,
                    time.replace(tzinfo=None),
                    item_answered=answered,
                    item_asked=asked,
                    guess=guess,
                    answer_id=answer_id)
                environment.process_answer(user, item, asked, answered, time, answer_id, response_time, guess)
        print(' -- model phase, time:', timer('recompute_model'), 'seconds')
        timer('recompute_flush')
        print(' -- flushing phase')
        environment.flush(clean=options['finish'])
        print(' -- flushing phase, time:', timer('recompute_flush'), 'seconds, total number of answers:', info.load_progress)
        if options['finish']:
            timer('recompute_finish')
            print(' -- finishing phase')
            try:
                previous_info = EnvironmentInfo.objects.get(status=EnvironmentInfo.STATUS_ACTIVE)
                previous_info.status = EnvironmentInfo.STATUS_DISABLED
                previous_info.save()
                cache.delete(ENVIRONMENT_INFO_CACHE_KEY)
            except EnvironmentInfo.DoesNotExist:
                pass
            info.status = EnvironmentInfo.STATUS_ACTIVE
            print(' -- finishing phase, time:', timer('recompute_finish'), 'seconds')
        info.save()

    def load_environment_info(self, initial, config_name):
        set_default_config_name(config_name)
        config = Config.objects.from_content(get_config('proso_models', 'predictive_model', default={}))
        if initial:
            if EnvironmentInfo.objects.filter(status=EnvironmentInfo.STATUS_LOADING).count() > 0:
                raise CommandError("There is already one currently loading environment.")
            last_revisions = EnvironmentInfo.objects.filter(config=config).order_by('-revision')[:1]
            if last_revisions:
                new_revision = last_revisions[0].id + 1
            else:
                new_revision = 0
            return EnvironmentInfo.objects.create(config=config, revision=new_revision)
        else:
            return EnvironmentInfo.objects.get(config=config, status=EnvironmentInfo.STATUS_LOADING)

    def load_environment(self, info):
        return instantiate_from_config(
            'proso_models', 'recompute_environment',
            default_class='proso_models.models.InMemoryDatabaseFlushEnvironment',
            pass_parameters=[info])

    def load_user_and_item_ids(self, info, batch_size):
        with closing(connection.cursor()) as cursor:
            cursor.execute(
                '''
                SELECT
                    user_id,
                    item_id,
                    item_asked_id,
                    item_answered_id
                FROM proso_models_answer
                ORDER BY id
                OFFSET %s LIMIT %s
                ''', [info.load_progress, batch_size])
            unzipped = list(zip(*cursor.fetchall()))
            if len(unzipped) == 0:
                return [], []
            else:
                return list(set(unzipped[0])), [x for x in list(set(unzipped[1]) | set(unzipped[2]) | set(unzipped[3])) if x is not None]

    def number_of_answers_to_process(self, info):
        with closing(connection.cursor()) as cursor:
            cursor.execute(
                '''
                SELECT COUNT(id)
                FROM proso_models_answer
                OFFSET %s
                ''', [info.load_progress])
            fetched = cursor.fetchone()
            if fetched is None:
                return 0
            else:
                return fetched[0]
