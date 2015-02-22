from django.core.management.base import BaseCommand
import json
from django.db import connection
from django.core.management import call_command
from contextlib import closing
from django.db import transaction
from collections import defaultdict
from optparse import make_option
from proso_user.models import Location, Session


class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option(
            '--clean',
            action='store_true',
            dest='clean',
            default=False,
            help='Delete all previously loaded data'),
        make_option(
            '--skip-places',
            action='store_true',
            dest='skip_places',
            default=False,
            help='Skip loading of places.'),
        make_option(
            '--skip-answers',
            action='store_true',
            dest='skip_answers',
            default=False,
            help='Skip loading of answers.'),
        make_option(
            '--limit',
            dest='limit',
            default=1000000,
            type=int,
            help='Maximum number of loaded answer'),
        )

    LANGUAGES = {
        0: 'cs',
        1: 'en',
        2: 'es'
    }

    PLACE_TYPES = {
        0: 'unknown',
        1: 'state',
        2: 'city',
        3: 'world',
        4: 'continent',
        5: 'river',
        6: 'lake',
        7: 'region_cz',
        8: 'bundesland',
        9: 'province',
        10: 'region_it',
        11: 'region',
        12: 'autonomous_Comunity',
        13: 'mountains',
        14: 'island'
    }

    REALLY_OLD_TABLES = [
        'core_answer',
        'core_answer_options',
        'core_confusedplaces',
        'core_map',
        'core_map_places',
        'core_place',
        'core_placerelation',
        'core_placerelation_related_places',
        'core_student',
        'core_usersplace'
    ]

    def handle(self, *args, **options):
        with transaction.atomic():
            with closing(connection.cursor()) as cursor:
                cursor.execute('SET CONSTRAINTS ALL DEFERRED;')
            if not options['skip_places']:
                self.migrate_places()
            if not options['skip_answers']:
                self.migrate_answers(clean=options['clean'], limit=options['limit'])
            print ' -- commit transaction'

    def clean_really_old(self):
        with closing(connection.cursor()) as cursor:
            for table in self.REALLY_OLD_TABLES:
                cursor.execute('DROP TABLE IF EXISTS %s;' % table)

    def migrate_answers(self, clean=True, limit=1000000):
        prev_max_answer = 0
        if clean:
            print ' -- delete answers'
            with closing(connection.cursor()) as cursor:
                cursor.execute('TRUNCATE TABLE proso_flashcards_decoratedanswer_options CASCADE')
                cursor.execute('TRUNCATE TABLE proso_flashcards_decoratedanswer CASCADE')
                cursor.execute('TRUNCATE TABLE proso_models_answer_ab_values CASCADE')
                cursor.execute('TRUNCATE TABLE proso_models_answer CASCADE')
                cursor.execute('TRUNCATE TABLE proso_user_session CASCADE')
                cursor.execute('TRUNCATE TABLE proso_user_location CASCADE')
        else:
            with closing(connection.cursor()) as cursor:
                cursor.execute('SELECT MAX(id) FROM proso_flashcards_decoratedanswer')
                prev_max_answer, = cursor.fetchone()
        print ' -- prepare mapping to original places'
        with closing(connection.cursor()) as cursor:
            cursor.execute(
                '''
                SELECT
                    id,
                    code
                FROM geography_place
                ''')
            original_places = dict(cursor.fetchall())
        print ' -- prepare mapping to new places'
        with closing(connection.cursor()) as cursor:
            cursor.execute(
                '''
                SELECT
                    identifier,
                    language,
                    item_id
                FROM proso_flashcards_flashcard
                ''')
            places = dict(map(lambda (x, y, z): ((x, y), z), cursor.fetchall()))
        print ' -- prepare mapping to maps'
        with closing(connection.cursor()) as cursor:
            cursor.execute(
                '''
                SELECT
                    identifier,
                    language,
                    id
                FROM proso_flashcards_category
                ''')
            maps = dict(map(lambda (x, y, z): ((x, y), z), cursor.fetchall()))
        print ' -- load answers where id >', prev_max_answer
        sessions = Sessions()
        with closing(connection.cursor()) as cursor_source:
            cursor_source.execute(
                '''
                SELECT
                    user_id,
                    place_asked_id,
                    place_answered_id,
                    type,
                    inserted,
                    response_time,
                    place_map_id,
                    ip_address,
                    language,
                    id
                FROM geography_answer
                WHERE id > %s
                ORDER BY id
                LIMIT %s
                ''', [prev_max_answer, limit])
            count = 0
            print ' -- migrate', limit, 'answers'
            options_retriever = GeographyOptions()
            ab_values_retriever = GeographyABValues()
            places_mask = lambda i, lang: places[original_places[i], lang] if i else None
            with closing(connection.cursor()) as cursor_dest:
                for row in cursor_source:
                    count += 1
                    if count % 10000 == 0:
                        print count, 'answers processed'
                    lang = self.LANGUAGES[row[8]]
                    item_asked = places_mask(row[1], lang)
                    item_answered = places_mask(row[2], lang)
                    category = maps[original_places[row[6]], lang] if row[6] else None
                    general_answer_id = row[9]
                    cursor_dest.execute(
                        '''
                        INSERT INTO proso_models_answer
                            (id, user_id, item_id, item_asked_id, item_answered_id, time, response_time, ab_values_initialized, session_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ''', [general_answer_id, row[0], item_asked, item_asked, item_answered, row[4], row[5], True, sessions.get_session_id(row[0], row[7], row[4])])
                    cursor_dest.execute(
                        '''
                        INSERT INTO proso_flashcards_decoratedanswer
                            (id, language, direction, general_answer_id, category_id)
                        VALUES (%s, %s, %s, %s, %s)
                        ''', [general_answer_id, lang, row[3], general_answer_id, category])
                    options = options_retriever.get_options(general_answer_id)
                    for item_id in map(lambda i: places_mask(i, lang), options):
                        cursor_dest.execute(
                            '''
                            INSERT INTO proso_flashcards_decoratedanswer_options
                                (decoratedanswer_id, item_id)
                            VALUES (%s, %s)
                            ''', [general_answer_id, item_id])
                    ab_values = ab_values_retriever.get_values(general_answer_id)
                    for value_id in ab_values:
                        cursor_dest.execute(
                            '''
                            INSERT INTO proso_models_answer_ab_values
                                (answer_id, value_id)
                            VALUES (%s, %s)
                            ''', [general_answer_id, value_id])

    def migrate_places(self):
        maps = {}
        places = {}
        with closing(connection.cursor()) as cursor:
            cursor.execute(
                '''
                SELECT
                    geography_place.id,
                    geography_place.code,
                    geography_place.name,
                    geography_place.type,
                    geography_place.name_cs,
                    geography_place.name_en,
                    geography_place.name_es
                FROM geography_place
                INNER JOIN geography_placerelation ON
                    geography_place.id = geography_placerelation.place_id
                ''')
            for row in cursor:
                category_cs = {
                    'identifier': row[1],
                    'type': self.PLACE_TYPES[row[3]],
                    'language': 'cs',
                    'name': row[4]
                }
                category_en = {
                    'identifier': row[1],
                    'type': self.PLACE_TYPES[row[3]],
                    'language': 'en',
                    'name': row[5]
                }
                category_es = {
                    'identifier': row[1],
                    'type': self.PLACE_TYPES[row[3]],
                    'language': 'es',
                    'name': row[6]
                }
                if not category_en['name']:
                    print ' XXX there is no english translation for map', row[1]
                    category_en['name'] = row[2]
                if not category_cs['name']:
                    print ' XXX there is no czech translation for map', row[1]
                    category_cs['name'] = category_en['name']
                if not category_es['name']:
                    print ' XXX there is no spanish translation for map', row['1']
                    category_es['name'] = category_en['name']
                maps[row[0], 'cs'] = category_cs
                maps[row[0], 'en'] = category_en
                maps[row[0], 'es'] = category_es
        with closing(connection.cursor()) as cursor:
            cursor.execute(
                '''
                SELECT
                    id,
                    code,
                    name,
                    type,
                    name_cs,
                    name_en,
                    name_es
                FROM geography_place
                ''')
            for row in cursor:
                place_cs = {
                    'identifier': row[1],
                    'type': self.PLACE_TYPES[row[3]],
                    'language': 'cs',
                    'reverse': row[1],
                    'obverse': row[4],
                    'categories': []
                }
                place_en = {
                    'identifier': row[1],
                    'type': self.PLACE_TYPES[row[3]],
                    'language': 'en',
                    'reverse': row[1],
                    'obverse': row[5],
                    'categories': []
                }
                place_es = {
                    'identifier': row[1],
                    'type': self.PLACE_TYPES[row[3]],
                    'language': 'en',
                    'reverse': row[1],
                    'obverse': row[6],
                    'categories': []
                }
                if not place_en['obverse']:
                    print ' XXX there is no english translation for place', row[1]
                    place_en['obverse'] = row[2]
                if not place_cs['obverse']:
                    print ' XXX there is no czech translation for place', row[1]
                    place_cs['obverse'] = place_en['obverse']
                if not place_es['obverse']:
                    print ' XXX there is no spanish translation for place', row[1]
                    place_es['obverse'] = place_en['obverse']
                places[row[0], 'cs'] = place_cs
                places[row[0], 'en'] = place_en
                places[row[0], 'es'] = place_es
        with closing(connection.cursor()) as cursor:
            cursor.execute(
                '''
                SELECT
                    geography_placerelation.place_id AS map_id,
                    geography_placerelation_related_places.place_id AS place_id
                FROM geography_placerelation
                INNER JOIN geography_placerelation_related_places ON
                    geography_placerelation.id = geography_placerelation_related_places.placerelation_id
                WHERE type = 1
                ''')
            used_maps = set()
            for row in cursor:
                places[row[1], 'cs']['categories'].append(maps[row[0], 'cs']['identifier'])
                places[row[1], 'en']['categories'].append(maps[row[0], 'en']['identifier'])
                places[row[1], 'es']['categories'].append(maps[row[0], 'es']['identifier'])
                used_maps.add((row[0], 'cs'))
                used_maps.add((row[0], 'en'))
                used_maps.add((row[0], 'es'))
        with open('geography-flashcards.json', 'w') as f:
            json.dump({
                'categories': map(lambda used: maps[used], used_maps),
                'flashcards': places.values(),
                'contexts': []
            }, f, indent=2)
        call_command('load_flashcards', 'geography-flashcards.json')


class GeographyOptions:

    def __init__(self, batch_size=100000):
        self._cache = None
        self._max_answer_id = 0
        self._batch_size = batch_size

    def get_options(self, answer_id):
        if answer_id > self._max_answer_id:
            self._load_batch(answer_id)
        return self._cache[answer_id]

    def _load_batch(self, answer_id):
        with closing(connection.cursor()) as cursor:
            cursor.execute(
                '''
                SELECT answer_id, place_id
                FROM geography_answer_options
                WHERE answer_id >= %s AND answer_id <= %s
                ''', [answer_id, answer_id + self._batch_size])
            result = defaultdict(list)
            for row in cursor:
                self._max_answer_id = max(self._max_answer_id, row[0])
                result[row[0]].append(row[1])
            self._cache = result


class Sessions:

    def __init__(self):
        self._sessions = {}

    def get_session_id(self, user, ip_address, time):
        if ip_address is None or ip_address == '':
            return None
        found = self._sessions.get(user)
        if found is None:
            session, session_time = self._new_session(user, ip_address), time
        else:
            session, session_time = found
            if session.location.ip_address != ip_address or (time - session_time).total_seconds() > 30 * 60:
                session = self._new_session(user, ip_address)
        self._sessions[user] = session, time
        return session.id

    def _new_session(self, user, ip_address):
        location = Location(ip_address=ip_address)
        location.save()
        session = Session(location=location, user_id=int(user))
        session.save()
        return session


class GeographyABValues:

    def __init__(self, batch_size=100000):
        self._cache = None
        self._max_answer_id = 0
        self._batch_size = batch_size

    def get_values(self, answer_id):
        if answer_id > self._max_answer_id:
            self._load_batch(answer_id)
        return self._cache[answer_id]

    def _load_batch(self, answer_id):
        with closing(connection.cursor()) as cursor:
            cursor.execute(
                '''
                SELECT answer_id, value_id
                FROM geography_answer_ab_values
                WHERE answer_id >= %s AND answer_id <= %s
                ''', [answer_id, answer_id + self._batch_size])
            result = defaultdict(list)
            for row in cursor:
                self._max_answer_id = max(self._max_answer_id, row[0])
                result[row[0]].append(row[1])
            self._cache = result
