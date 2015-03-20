# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'ExtendedTerm'
        db.create_table(u'testapp_extendedterm', (
            (u'term_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['proso_flashcards.Term'], unique=True, primary_key=True)),
            ('extra_info', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal(u'testapp', ['ExtendedTerm'])

        # Adding model 'ExtendedContext'
        db.create_table(u'testapp_extendedcontext', (
            (u'context_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['proso_flashcards.Context'], unique=True, primary_key=True)),
            ('extra_info', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal(u'testapp', ['ExtendedContext'])


    def backwards(self, orm):
        # Deleting model 'ExtendedTerm'
        db.delete_table(u'testapp_extendedterm')

        # Deleting model 'ExtendedContext'
        db.delete_table(u'testapp_extendedcontext')


    models = {
        u'proso_flashcards.context': {
            'Meta': {'object_name': 'Context'},
            'content': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'identifier': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'item': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'related_name': "'flashcard_contexts'", 'null': 'True', 'to': "orm['proso_models.Item']"}),
            'lang': ('django.db.models.fields.CharField', [], {'max_length': '2'}),
            'name': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        },
        u'proso_flashcards.term': {
            'Meta': {'object_name': 'Term'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'identifier': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'item': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'related_name': "'flashcard_terms'", 'null': 'True', 'to': "orm['proso_models.Item']"}),
            'lang': ('django.db.models.fields.CharField', [], {'max_length': '2'}),
            'name': ('django.db.models.fields.TextField', [], {})
        },
        'proso_models.item': {
            'Meta': {'object_name': 'Item'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'testapp.extendedcontext': {
            'Meta': {'object_name': 'ExtendedContext', '_ormbases': [u'proso_flashcards.Context']},
            u'context_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['proso_flashcards.Context']", 'unique': 'True', 'primary_key': 'True'}),
            'extra_info': ('django.db.models.fields.TextField', [], {})
        },
        u'testapp.extendedterm': {
            'Meta': {'object_name': 'ExtendedTerm', '_ormbases': [u'proso_flashcards.Term']},
            'extra_info': ('django.db.models.fields.TextField', [], {}),
            u'term_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['proso_flashcards.Term']", 'unique': 'True', 'primary_key': 'True'})
        }
    }

    complete_apps = ['testapp']