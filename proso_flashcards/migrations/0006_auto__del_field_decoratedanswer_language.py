# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'DecoratedAnswer.language'
        db.delete_column(u'proso_flashcards_decoratedanswer', 'language')


    def backwards(self, orm):

        # User chose to not deal with backwards NULL issues for 'DecoratedAnswer.language'
        raise RuntimeError("Cannot reverse this migration. 'DecoratedAnswer.language' and its values cannot be restored.")
        
        # The following code is provided here to aid in writing a correct migration        # Adding field 'DecoratedAnswer.language'
        db.add_column(u'proso_flashcards_decoratedanswer', 'language',
                      self.gf('django.db.models.fields.CharField')(max_length=50),
                      keep_default=False)


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
        'proso_ab.experiment': {
            'Meta': {'object_name': 'Experiment'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'})
        },
        'proso_ab.value': {
            'Meta': {'object_name': 'Value'},
            'experiment': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['proso_ab.Experiment']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_default': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'probability': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        u'proso_flashcards.category': {
            'Meta': {'unique_together': "(('item', 'language'), ('identifier', 'language'))", 'object_name': 'Category'},
            'context': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': u"orm['proso_flashcards.Context']", 'null': 'True', 'blank': 'True'}),
            'flashcards': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['proso_flashcards.Flashcard']", 'symmetrical': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'identifier': ('django.db.models.fields.SlugField', [], {'default': 'None', 'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'item': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'related_name': "'flashcard_category_set'", 'null': 'True', 'blank': 'True', 'to': "orm['proso_models.Item']"}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'subcategories': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'subcategories_rel_+'", 'to': u"orm['proso_flashcards.Category']"}),
            'type': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'url_name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50'})
        },
        u'proso_flashcards.context': {
            'Meta': {'object_name': 'Context'},
            'file': ('django.db.models.fields.files.ImageField', [], {'max_length': '255'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'identifier': ('django.db.models.fields.SlugField', [], {'default': 'None', 'max_length': '50', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'item': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['proso_models.Item']", 'null': 'True', 'blank': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'proso_flashcards.decoratedanswer': {
            'Meta': {'object_name': 'DecoratedAnswer'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': u"orm['proso_flashcards.Category']", 'null': 'True', 'blank': 'True'}),
            'direction': ('django.db.models.fields.IntegerField', [], {}),
            'general_answer': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'flashcard_decoratedanswer_set'", 'unique': 'True', 'to': "orm['proso_models.Answer']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'options': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'flashcard_decoratedanswer_set'", 'symmetrical': 'False', 'to': "orm['proso_models.Item']"})
        },
        u'proso_flashcards.flashcard': {
            'Meta': {'unique_together': "(('item', 'language'), ('identifier', 'language'))", 'object_name': 'Flashcard'},
            'context': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': u"orm['proso_flashcards.Context']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'identifier': ('django.db.models.fields.SlugField', [], {'default': 'None', 'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'item': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['proso_models.Item']", 'null': 'True', 'blank': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'obverse': ('django.db.models.fields.TextField', [], {}),
            'reverse': ('django.db.models.fields.TextField', [], {}),
            'type': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '50', 'null': 'True', 'blank': 'True'})
        },
        'proso_models.answer': {
            'Meta': {'object_name': 'Answer'},
            'ab_values': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['proso_ab.Value']", 'symmetrical': 'False'}),
            'ab_values_initialized': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'item': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'item_answers'", 'to': "orm['proso_models.Item']"}),
            'item_answered': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'related_name': "'item_answered_answers'", 'null': 'True', 'blank': 'True', 'to': "orm['proso_models.Item']"}),
            'item_asked': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'item_asked_answers'", 'to': "orm['proso_models.Item']"}),
            'pure': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'response_time': ('django.db.models.fields.IntegerField', [], {}),
            'session': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': u"orm['proso_user.Session']", 'null': 'True', 'blank': 'True'}),
            'time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        'proso_models.item': {
            'Meta': {'object_name': 'Item'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
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
        u'proso_user.timezone': {
            'Meta': {'object_name': 'TimeZone'},
            'content': ('django.db.models.fields.TextField', [], {}),
            'content_hash': ('django.db.models.fields.CharField', [], {'max_length': '40', 'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        }
    }

    complete_apps = ['proso_flashcards']