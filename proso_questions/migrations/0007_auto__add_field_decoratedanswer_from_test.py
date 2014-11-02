# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'DecoratedAnswer.from_test'
        db.add_column(u'proso_questions_decoratedanswer', 'from_test',
                      self.gf('django.db.models.fields.related.ForeignKey')(default=None, to=orm['proso_questions.Set'], null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'DecoratedAnswer.from_test'
        db.delete_column(u'proso_questions_decoratedanswer', 'from_test_id')


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
            'Meta': {'unique_together': "(('experiment', 'is_default'),)", 'object_name': 'Value'},
            'experiment': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['proso_ab.Experiment']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_default': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'probability': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        'proso_models.answer': {
            'Meta': {'object_name': 'Answer'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'item': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'item_answers'", 'to': "orm['proso_models.Item']"}),
            'item_answered': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'related_name': "'item_answered_answers'", 'null': 'True', 'blank': 'True', 'to': "orm['proso_models.Item']"}),
            'item_asked': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'item_asked_answers'", 'to': "orm['proso_models.Item']"}),
            'response_time': ('django.db.models.fields.IntegerField', [], {}),
            'time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        'proso_models.item': {
            'Meta': {'object_name': 'Item'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'proso_questions.category': {
            'Meta': {'object_name': 'Category'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'item': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['proso_models.Item']", 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'questions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['proso_questions.Question']", 'symmetrical': 'False'}),
            'url_name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50'})
        },
        u'proso_questions.decoratedanswer': {
            'Meta': {'object_name': 'DecoratedAnswer'},
            'ab_values': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['proso_ab.Value']", 'symmetrical': 'False'}),
            'from_test': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': u"orm['proso_questions.Set']", 'null': 'True', 'blank': 'True'}),
            'general_answer': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['proso_models.Answer']", 'unique': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip_address': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '39', 'null': 'True', 'blank': 'True'})
        },
        u'proso_questions.image': {
            'Meta': {'object_name': 'Image'},
            'file': ('django.db.models.fields.files.ImageField', [], {'max_length': '255'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'option': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'related_name': "'option_images'", 'null': 'True', 'blank': 'True', 'to': u"orm['proso_questions.Option']"}),
            'question': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'related_name': "'question_images'", 'null': 'True', 'blank': 'True', 'to': u"orm['proso_questions.Question']"}),
            'resource': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'related_name': "'resource_images'", 'null': 'True', 'blank': 'True', 'to': u"orm['proso_questions.Resource']"})
        },
        u'proso_questions.option': {
            'Meta': {'object_name': 'Option'},
            'correct': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'item': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['proso_models.Item']", 'unique': 'True', 'null': 'True'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'question': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'question_options'", 'to': u"orm['proso_questions.Question']"}),
            'text': ('django.db.models.fields.TextField', [], {})
        },
        u'proso_questions.question': {
            'Meta': {'object_name': 'Question'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'identifier': ('django.db.models.fields.SlugField', [], {'default': 'None', 'max_length': '50', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'item': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['proso_models.Item']", 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'resource': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'related_name': "'resource_questions'", 'null': 'True', 'blank': 'True', 'to': u"orm['proso_questions.Resource']"}),
            'text': ('django.db.models.fields.TextField', [], {})
        },
        u'proso_questions.resource': {
            'Meta': {'object_name': 'Resource'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'identifier': ('django.db.models.fields.SlugField', [], {'default': 'None', 'max_length': '50', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'item': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['proso_models.Item']", 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'text': ('django.db.models.fields.TextField', [], {})
        },
        u'proso_questions.set': {
            'Meta': {'object_name': 'Set'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'item': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['proso_models.Item']", 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'questions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['proso_questions.Question']", 'symmetrical': 'False'})
        }
    }

    complete_apps = ['proso_questions']