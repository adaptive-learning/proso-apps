# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Flashcard'
        db.create_table(u'proso_flashcards_flashcard', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('identifier', self.gf('django.db.models.fields.SlugField')(default=None, max_length=50, null=True, blank=True)),
            ('item', self.gf('django.db.models.fields.related.ForeignKey')(default=None, to=orm['proso_models.Item'], null=True, blank=True)),
            ('language', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('reverse', self.gf('django.db.models.fields.TextField')()),
            ('obverse', self.gf('django.db.models.fields.TextField')()),
            ('type', self.gf('django.db.models.fields.CharField')(default=None, max_length=50, null=True, blank=True)),
        ))
        db.send_create_signal(u'proso_flashcards', ['Flashcard'])

        # Adding unique constraint on 'Flashcard', fields ['item', 'language']
        db.create_unique(u'proso_flashcards_flashcard', ['item_id', 'language'])

        # Adding unique constraint on 'Flashcard', fields ['identifier', 'language']
        db.create_unique(u'proso_flashcards_flashcard', ['identifier', 'language'])

        # Adding model 'Category'
        db.create_table(u'proso_flashcards_category', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('identifier', self.gf('django.db.models.fields.SlugField')(default=None, max_length=50, null=True, blank=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('type', self.gf('django.db.models.fields.CharField')(default=None, max_length=20, null=True, blank=True)),
            ('language', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('item', self.gf('django.db.models.fields.related.ForeignKey')(default=None, related_name='flashcard_category_set', null=True, blank=True, to=orm['proso_models.Item'])),
            ('url_name', self.gf('django.db.models.fields.SlugField')(unique=True, max_length=50)),
        ))
        db.send_create_signal(u'proso_flashcards', ['Category'])

        # Adding unique constraint on 'Category', fields ['item', 'language']
        db.create_unique(u'proso_flashcards_category', ['item_id', 'language'])

        # Adding unique constraint on 'Category', fields ['identifier', 'language']
        db.create_unique(u'proso_flashcards_category', ['identifier', 'language'])

        # Adding M2M table for field flashcards on 'Category'
        m2m_table_name = db.shorten_name(u'proso_flashcards_category_flashcards')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('category', models.ForeignKey(orm[u'proso_flashcards.category'], null=False)),
            ('flashcard', models.ForeignKey(orm[u'proso_flashcards.flashcard'], null=False))
        ))
        db.create_unique(m2m_table_name, ['category_id', 'flashcard_id'])

        # Adding model 'DecoratedAnswer'
        db.create_table(u'proso_flashcards_decoratedanswer', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('general_answer', self.gf('django.db.models.fields.related.ForeignKey')(related_name='flashcard_decoratedanswer_set', unique=True, to=orm['proso_models.Answer'])),
            ('ip_address', self.gf('django.db.models.fields.CharField')(default=None, max_length=39, null=True, blank=True)),
            ('language', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('direction', self.gf('django.db.models.fields.IntegerField')()),
            ('category', self.gf('django.db.models.fields.related.ForeignKey')(default=None, to=orm['proso_flashcards.Category'], null=True, blank=True)),
        ))
        db.send_create_signal(u'proso_flashcards', ['DecoratedAnswer'])

        # Adding M2M table for field ab_values on 'DecoratedAnswer'
        m2m_table_name = db.shorten_name(u'proso_flashcards_decoratedanswer_ab_values')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('decoratedanswer', models.ForeignKey(orm[u'proso_flashcards.decoratedanswer'], null=False)),
            ('value', models.ForeignKey(orm['proso_ab.value'], null=False))
        ))
        db.create_unique(m2m_table_name, ['decoratedanswer_id', 'value_id'])

        # Adding M2M table for field options on 'DecoratedAnswer'
        m2m_table_name = db.shorten_name(u'proso_flashcards_decoratedanswer_options')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('decoratedanswer', models.ForeignKey(orm[u'proso_flashcards.decoratedanswer'], null=False)),
            ('item', models.ForeignKey(orm['proso_models.item'], null=False))
        ))
        db.create_unique(m2m_table_name, ['decoratedanswer_id', 'item_id'])


    def backwards(self, orm):
        # Removing unique constraint on 'Category', fields ['identifier', 'language']
        db.delete_unique(u'proso_flashcards_category', ['identifier', 'language'])

        # Removing unique constraint on 'Category', fields ['item', 'language']
        db.delete_unique(u'proso_flashcards_category', ['item_id', 'language'])

        # Removing unique constraint on 'Flashcard', fields ['identifier', 'language']
        db.delete_unique(u'proso_flashcards_flashcard', ['identifier', 'language'])

        # Removing unique constraint on 'Flashcard', fields ['item', 'language']
        db.delete_unique(u'proso_flashcards_flashcard', ['item_id', 'language'])

        # Deleting model 'Flashcard'
        db.delete_table(u'proso_flashcards_flashcard')

        # Deleting model 'Category'
        db.delete_table(u'proso_flashcards_category')

        # Removing M2M table for field flashcards on 'Category'
        db.delete_table(db.shorten_name(u'proso_flashcards_category_flashcards'))

        # Deleting model 'DecoratedAnswer'
        db.delete_table(u'proso_flashcards_decoratedanswer')

        # Removing M2M table for field ab_values on 'DecoratedAnswer'
        db.delete_table(db.shorten_name(u'proso_flashcards_decoratedanswer_ab_values'))

        # Removing M2M table for field options on 'DecoratedAnswer'
        db.delete_table(db.shorten_name(u'proso_flashcards_decoratedanswer_options'))


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
        u'proso_flashcards.category': {
            'Meta': {'unique_together': "(('item', 'language'), ('identifier', 'language'))", 'object_name': 'Category'},
            'flashcards': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['proso_flashcards.Flashcard']", 'symmetrical': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'identifier': ('django.db.models.fields.SlugField', [], {'default': 'None', 'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'item': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'related_name': "'flashcard_category_set'", 'null': 'True', 'blank': 'True', 'to': "orm['proso_models.Item']"}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'type': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'url_name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50'})
        },
        u'proso_flashcards.decoratedanswer': {
            'Meta': {'object_name': 'DecoratedAnswer'},
            'ab_values': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'flashcard_decoratedanswer_set'", 'symmetrical': 'False', 'to': "orm['proso_ab.Value']"}),
            'category': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': u"orm['proso_flashcards.Category']", 'null': 'True', 'blank': 'True'}),
            'direction': ('django.db.models.fields.IntegerField', [], {}),
            'general_answer': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'flashcard_decoratedanswer_set'", 'unique': 'True', 'to': "orm['proso_models.Answer']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip_address': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '39', 'null': 'True', 'blank': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'options': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'flashcard_decoratedanswer_set'", 'symmetrical': 'False', 'to': "orm['proso_models.Item']"})
        },
        u'proso_flashcards.flashcard': {
            'Meta': {'unique_together': "(('item', 'language'), ('identifier', 'language'))", 'object_name': 'Flashcard'},
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
        }
    }

    complete_apps = ['proso_flashcards']