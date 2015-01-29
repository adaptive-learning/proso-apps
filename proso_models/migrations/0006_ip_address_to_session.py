# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models
from django.db import connection
from contextlib import closing
from proso_user.models import Location, Session


class Migration(DataMigration):

    def forwards(self, orm):
        locations = {}
        sessions = {}
        with closing(connection.cursor()) as cursor_source:
            cursor_source.execute(
                '''
                SELECT
                    id,
                    user_id,
                    ip_address
                FROM
                    proso_models_answer
                ''')
            with closing(connection.cursor()) as cursor_dest:
                for (answer_id, user_id, ip_address) in cursor_source:
                    if ip_address is None:
                        continue
                    if (ip_address, user_id) not in sessions:
                        if ip_address not in locations:
                            locations[ip_address] = Location.objects.from_ip_address(ip_address)
                        location = locations[ip_address]
                        session = Session(location=location, user_id=user_id)
                        session.save()
                        sessions[ip_address, user_id] = session
                    cursor_dest.execute(
                        '''
                        UPDATE proso_models_answer
                        SET session_id = %s
                        WHERE id = %s
                        ''', [sessions[ip_address, user_id].id, answer_id])

    def backwards(self, orm):
        pass

    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'proso_user.httpuseragent': {
            'Meta': {'object_name': 'HttpUserAgent'},
            'browser_family': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '39', 'null': 'True', 'blank': 'True'}),
            'browser_version': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '39', 'null': 'True', 'blank': 'True'}),
            'content': ('django.db.models.fields.TextField', [], {}),
            'content_hash': ('django.db.models.fields.CharField', [], {'max_length': '40', 'db_index': 'True'}),
            'device_family': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '50', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'os_family': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '39', 'null': 'True', 'blank': 'True'}),
            'os_version': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '39', 'null': 'True', 'blank': 'True'})
        },
        u'proso_user.location': {
            'Meta': {'object_name': 'Location'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip_address': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '39', 'null': 'True', 'blank': 'True'})
        },
        u'proso_user.session': {
            'Meta': {'object_name': 'Session'},
            'display_height': ('django.db.models.fields.IntegerField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'display_width': ('django.db.models.fields.IntegerField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'http_user_agent': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': u"orm['proso_user.HttpUserAgent']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'locale': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'location': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': u"orm['proso_user.Location']", 'null': 'True', 'blank': 'True'}),
            'time_zone': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': u"orm['proso_user.TimeZone']", 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'proso_user.sessionmanager': {
            'Meta': {'object_name': 'SessionManager'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'proso_user.timezone': {
            'Meta': {'object_name': 'TimeZone'},
            'content': ('django.db.models.fields.TextField', [], {}),
            'content_hash': ('django.db.models.fields.CharField', [], {'max_length': '40', 'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        }
    }

    complete_apps = ['proso_user']
    symmetrical = True

