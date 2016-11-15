from collections import defaultdict
from contextlib import closing
from django.core.cache import cache
from django.db import connection
from proso_common.models import get_config
from proso_models.environment import DatabaseEnvironment as ODatabaseEnvironment
import logging


LOGGER = logging.getLogger('django.request')


class DatabaseEnvironment(ODatabaseEnvironment):

    def confusing_factor_more_items(self, item, items, user=None):
        cached_all = {}
        confusing_factor_cache = cache.get('database_environment__confusing_factor', {})
        for item_secondary in items:
            cache_key = '{}_{}_{}'.format(item, item_secondary, user)
            cached_item = confusing_factor_cache.get(cache_key)
            if cached_item:
                cached_all[item_secondary] = int(cached_item)
        to_find = [i for i in items if i not in list(cached_all.keys())]
        if len(cached_all) != 0:
            LOGGER.debug('cache hit for confusing factor, item {}, {} other items and user {}'.format(item, len(cached_all), user))
        if len(to_find) != 0:
            LOGGER.debug('cache miss for confusing factor, item {}, {} other items and user {}'.format(item, len(to_find), user))
            user_where, user_params = self._column_comparison('user_id', user, force_null=False)
            with closing(connection.cursor()) as cursor:
                cursor.execute(
                    '''
                    SELECT DISTINCT main.item_id, c.identifier
                    FROM proso_flashcards_flashcard AS main
                    INNER JOIN proso_flashcards_flashcard AS fc
                        ON (
                            main.term_id = fc.term_id OR
                            main.term_secondary_id = fc.term_id
                        )
                    INNER JOIN proso_flashcards_context AS c
                        ON c.id = fc.context_id
                    WHERE
                        fc.term_secondary_id IS NULL AND
                        fc.active AND
                        main.item_id IN (''' + ','.join('%s' for _ in [item] + to_find) + ')',
                    [item] + to_find
                )
                context_mapping = defaultdict(set)
                for i, c in cursor:
                    context_mapping[i].add(c)
            with closing(connection.cursor()) as cursor:
                cursor.execute(
                    '''
                    SELECT
                        main.item_answered_id,
                        COUNT(main.id)::float / (open.count + closed.count) as confusing_factor
                    FROM
                        proso_models_answer as main
                    INNER JOIN (
                        SELECT item_asked_id as item, COUNT(*) as count
                        FROM proso_models_answer
                        WHERE item_asked_id = %s AND guess = 0 AND ''' + user_where + '''
                        GROUP BY 1
                    ) AS open ON open.item = main.item_asked_id
                    INNER JOIN (
                        SELECT proso_models_answer.item_asked_id, fc.item_id as item_option_id, COUNT(*) as count
                        FROM proso_models_answer
                        INNER JOIN proso_flashcards_flashcardanswer_options AS options ON proso_models_answer.id = options.flashcardanswer_id
                        INNER JOIN proso_flashcards_flashcard AS fc on fc.id = options.flashcard_id
                        WHERE proso_models_answer.item_asked_id = %s AND ''' + user_where + '''
                        GROUP BY 1, 2
                    ) AS closed ON main.item_asked_id = closed.item_asked_id AND main.item_answered_id = closed.item_option_id
                    WHERE
                        main.item_asked_id = %s
                    AND main.item_answered_id IS NOT NULL
                    AND main.item_asked_id != main.item_answered_id
                    AND ''' + user_where + '''
                    GROUP BY 1, open.count, closed.count
                    ''', [item] + user_params + [item] + user_params + [item] + user_params)
                found = {}
                for item_answered, count in cursor:
                    found[item_answered] = count
                for i in to_find:
                    found[i] = 1000 * (found.get(i, 0.05) + 0 if len(context_mapping[item]) == 0 else (len(context_mapping[i] & context_mapping[item]) / len(context_mapping[i] | context_mapping[item])))
                cache_expiration = get_config('proso_models', 'confusing_factor.cache_expiration', default=24 * 60 * 60)
                # trying to decrease probability of race condition
                confusing_factor_cache = cache.get('database_environment__confusing_factor', {})
                for item_secondary, count in found.items():
                    cache_key = '{}_{}_{}'.format(item, item_secondary, user)
                    confusing_factor_cache[cache_key] = count
                    cached_all[item_secondary] = count
                cache.set('database_environment__confusing_factor', confusing_factor_cache, cache_expiration)
        return [cached_all[i] for i in items]
