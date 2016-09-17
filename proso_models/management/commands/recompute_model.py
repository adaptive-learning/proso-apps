from clint.textui import progress
from contextlib import closing
from django.conf import settings
from django.core.cache import cache
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db import transaction
from optparse import make_option
from proso_models.models import instantiate_from_config, get_config
from proso.django.config import set_default_config_name
from proso.django.db import is_on_postgresql
from proso.models.environment import InMemoryEnvironment
from proso.time import timer
from proso_common.models import Config
from proso_models.models import EnvironmentInfo, ENVIRONMENT_INFO_CACHE_KEY
from proso_models.models import get_predictive_model
import json
import math
import matplotlib.pyplot as plt
import numpy
import sys


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
        make_option(
            '--validate',
            dest='validate',
            action='store_true',
            default=False),
        make_option(
            '--dry',
            dest='dry',
            action='store_true',
            default=False),
        make_option(
            '--limit',
            dest='limit',
            type=int,
            default=None),
        make_option(
            '--force',
            dest='force',
            action='store_true',
            default=False)
    )

    def handle(self, *args, **options):
        if options['cancel']:
            self.handle_cancel(options)
        elif options['garbage_collector']:
            self.handle_gc(options)
        elif options['dry']:
            self.handle_dry(options)
        else:
            self.handle_recompute(options)
        if options['validate']:
            self.handle_validate(options)

    def handle_validate(self, options):
        timer('recompute_validation')
        info = self.load_environment_info(options['initial'], options['config_name'], False)
        with closing(connection.cursor()) as cursor:
            cursor.execute(
                '''
                SELECT key, user_id, item_primary_id, item_secondary_id
                FROM proso_models_variable
                WHERE info_id = %s
                GROUP BY 1, 2, 3, 4 HAVING COUNT(*) > 1
                ''', [info.id])
            fetched = cursor.fetchall()
            if len(fetched) > 0:
                print(' -- there are {} violations of variable uniqueness:')
                for key, user, primary, secondary in fetched:
                    print('     - ', key, user, primary, secondary)
                sys.exit('canceling due to previous error')
            else:
                print(' -- validation passed:', timer('recompute_validation'), 'seconds')

    def handle_dry(self, options):
        info = self.load_environment_info(options['initial'], options['config_name'], True)
        environment = InMemoryEnvironment(audit_enabled=False)
        predictive_model = get_predictive_model(info.to_json())
        with closing(connection.cursor()) as cursor:
            cursor.execute('SELECT COUNT(*) FROM proso_models_answer')
            answers_total = cursor.fetchone()[0]
            if options['limit'] is not None:
                answers_total = min(answers_total, options['limit'])
            print('total:', answers_total)
            processed = 0
            prediction = numpy.empty(answers_total)
            correct = numpy.empty(answers_total)
            while processed < answers_total:
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
                    ''', [processed, options['batch_size']])
                for (answer_id, user, item, asked, answered, time, response_time, guess) in cursor:
                    correct[processed] = asked == answered
                    prediction[processed] = predictive_model.predict_and_update(
                        environment,
                        user,
                        item,
                        asked == answered,
                        time,
                        item_answered=answered,
                        item_asked=asked,
                        guess=guess,
                        answer_id=answer_id,
                        response_time=response_time,
                    )
                    environment.process_answer(user, item, asked, answered, time, answer_id, response_time, guess)
                    processed += 1
                    if processed >= answers_total:
                        break
                print('processed:', processed)
        filename = settings.DATA_DIR + '/recompute_model_report_{}.json'.format(predictive_model.__class__.__name__)
        model_report = report(prediction, correct)
        with open(filename, 'w') as outfile:
            json.dump(model_report, outfile)
        print('Saving report to:', filename)
        brier_graphs(model_report['brier'], predictive_model)

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
            if is_on_postgresql():
                timer('recompute_vacuum')
                cursor.execute('VACUUM FULL ANALYZE VERBOSE proso_models_variable')
                cursor.execute('VACUUM FULL ANALYZE VERBOSE proso_models_audit')
                print(' -- vacuum phase, time:', timer('recompute_vacuum'), 'seconds')
        print(' -- collecting garbage, time:', timer('recompute_gc'), 'seconds, deleted', variables, 'variables,', audits, 'audit records,', infos, 'environment info records')

    def handle_cancel(self, options):
        info = self.load_environment_info(False, options['config_name'], False)
        print(' -- cancelling')
        info.status = EnvironmentInfo.STATUS_DISABLED
        info.save()

    def handle_recompute(self, options):
        timer('recompute_all')
        info = self.load_environment_info(options['initial'], options['config_name'], False)
        if options['finish']:
            with transaction.atomic():
                to_process = self.number_of_answers_to_process(info)
                if self.number_of_answers_to_process(info) >= options['batch_size'] and not options['force']:
                    raise CommandError("There is more then allowed number of answers (%s) to process." % to_process)
                self.recompute(info, options)
        else:
            self.recompute(info, options)
        print(' -- total time of recomputation:', timer('recompute_all'), 'seconds')

    def recompute(self, info, options):
        print(' -- preparing phase')
        timer('recompute_prepare')
        environment = self.load_environment(info)
        users, items = self.load_user_and_item_ids(info, options['batch_size'])
        environment.prefetch(users, items)
        predictive_model = get_predictive_model(info.to_json())
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
            progress_bar = progress.bar(cursor, every=max(1, cursor.rowcount // 100), expected_size=cursor.rowcount)
            info.load_progress += cursor.rowcount
            for (answer_id, user, item, asked, answered, time, response_time, guess) in progress_bar:
                predictive_model.predict_and_update(
                    environment,
                    user,
                    item,
                    asked == answered,
                    time,
                    item_answered=answered,
                    item_asked=asked,
                    guess=guess,
                    answer_id=answer_id,
                    response_time=response_time,
                )
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

    def load_environment_info(self, initial, config_name, dry):
        set_default_config_name(config_name)
        if hasattr(self, '_environment_info'):
            return self._environment_info
        config = Config.objects.from_content(get_config('proso_models', 'predictive_model', default={}))
        if dry:
            self._environment_info = EnvironmentInfo(config=config)
            return self._environment_info
        if initial:
            if EnvironmentInfo.objects.filter(status=EnvironmentInfo.STATUS_LOADING).count() > 0:
                raise CommandError("There is already one currently loading environment.")
            last_revisions = EnvironmentInfo.objects.filter(config=config).order_by('-revision')[:1]
            if last_revisions:
                new_revision = last_revisions[0].id + 1
            else:
                new_revision = 0
            self._environment_info = EnvironmentInfo.objects.create(config=config, revision=new_revision)
        else:
            self._environment_info = EnvironmentInfo.objects.get(config=config, status=EnvironmentInfo.STATUS_LOADING)
        return self._environment_info

    def load_environment(self, info):
        return instantiate_from_config(
            'proso_models', 'recompute_environment',
            default_class='proso_models.environment.InMemoryDatabaseFlushEnvironment',
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


def report(predictions, real):
    return {
        'rmse': rmse(predictions, real),
        'brier': brier(predictions, real),
    }


def rmse(predictions, real):
    return math.sqrt(numpy.mean((predictions - real) ** 2))


def brier(predictions, real, bins=20):
    counts = numpy.zeros(bins)
    correct = numpy.zeros(bins)
    prediction = numpy.zeros(bins)
    for p, r in zip(predictions, real):
        bin = min(int(p * bins), bins - 1)
        counts[bin] += 1
        correct[bin] += r
        prediction[bin] += p
    prediction_means = prediction / counts
    prediction_means[numpy.isnan(prediction_means)] = ((numpy.arange(bins) + 0.5) / bins)[numpy.isnan(prediction_means)]
    correct_means = correct / counts
    correct_means[numpy.isnan(correct_means)] = 0
    size = len(predictions)
    answer_mean = sum(correct) / size
    return {
        "reliability": sum(counts * (correct_means - prediction_means) ** 2) / size,
        "resolution": sum(counts * (correct_means - answer_mean) ** 2) / size,
        "uncertainty": answer_mean * (1 - answer_mean),
        "detail": {
            "bin_count": bins,
            "bin_counts": list(counts),
            "bin_prediction_means": list(prediction_means),
            "bin_correct_means": list(correct_means),
        }
    }


def brier_graphs(brier, model):
    plt.figure()
    plt.plot(brier['detail']['bin_prediction_means'], brier['detail']['bin_correct_means'])
    plt.plot((0, 1), (0, 1))

    bin_count = brier['detail']['bin_count']
    counts = numpy.array(brier['detail']['bin_counts'])
    bins = (numpy.arange(bin_count) + 0.5) / bin_count
    plt.bar(bins, counts / max(counts), width=(0.5 / bin_count), alpha=0.5)
    plt.title(model.__class__.__name__)
    plt.xlabel('Predicted')
    plt.ylabel('Observed')

    filename = settings.DATA_DIR + '/recompute_model_report_{}.svg'.format(model.__class__.__name__)
    plt.savefig(filename)
    print('Plotting to:', filename)
