from django.core.management.base import BaseCommand
import json
from django.db import connection
from django.core.management import call_command
from contextlib import closing
from django.db import transaction
from proso_flashcards.models import DecoratedAnswer


class Command(BaseCommand):

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
            self.migrate_places()
            self.migrate_answers()

    def clean_really_old(self):
        with closing(connection.cursor()) as cursor:
            for table in self.REALLY_OLD_TABLES:
                cursor.execute('DROP TABLE IF EXISTS %s;' % table)

    def migrate_answers(self):
        print ' -- delete answers'
        with closing(connection.cursor()) as cursor:
            cursor.execute('DELETE FROM proso_flashcards_decoratedanswer CASCADE')
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
        print ' -- load answers'
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
                    language
                FROM geography_answer
                LIMIT 100000
                ''')
            count = 0
            print ' -- migrate answers'
            with closing(connection.cursor()) as cursor_dest:
                for row in cursor_source:
                    count += 1
                    if count % 10000 == 0:
                        print count, 'answers processed'
                    lang = self.LANGUAGES[row[8]]
                    item_asked = places[original_places[row[1]], lang] if row[1] else None
                    item_answered = places[original_places[row[2]], lang] if row[2] else None
                    category = maps[original_places[row[6]], lang] if row[6] else None
                    cursor_dest.execute(
                        '''
                        INSERT INTO proso_models_answer
                            (user_id, item_id, item_asked_id, item_answered_id, time, response_time)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        RETURNING id
                        ''', [row[0], item_asked, item_asked, item_answered, row[4], row[5]])
                    general_answer_id = cursor_dest.fetchone()[0]
                    decorated_answer = DecoratedAnswer(
                        ip_address=row[7],
                        language=lang,
                        direction=row[3],
                        general_answer_id=general_answer_id,
                        category_id=category)
                    decorated_answer.save()

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
            for row in cursor:
                places[row[1], 'cs']['categories'].append(maps[row[0], 'cs']['identifier'])
                places[row[1], 'en']['categories'].append(maps[row[0], 'en']['identifier'])
                places[row[1], 'es']['categories'].append(maps[row[0], 'es']['identifier'])
        with open('geography-flashcards.json', 'w') as f:
            json.dump({'categories': maps.values(), 'flashcards': places.values()}, f, indent=2)
        call_command('load_flashcards', 'geography-flashcards.json')
