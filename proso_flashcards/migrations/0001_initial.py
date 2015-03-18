# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Term'
        db.create_table(u'proso_flashcards_term', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('identifier', self.gf('django.db.models.fields.SlugField')(default=None, max_length=50, unique=True, null=True, blank=True)),
            ('item', self.gf('django.db.models.fields.related.ForeignKey')(related_name='flashcard_terms', null=True, default=None, to=orm['proso_models.Item'], blank=True, unique=True)),
            ('lang', self.gf('django.db.models.fields.CharField')(max_length=2)),
            ('text', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal(u'proso_flashcards', ['Term'])

        # Adding model 'Context'
        db.create_table(u'proso_flashcards_context', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('identifier', self.gf('django.db.models.fields.SlugField')(default=None, max_length=50, unique=True, null=True, blank=True)),
            ('item', self.gf('django.db.models.fields.related.ForeignKey')(related_name='flashcard_contexts', null=True, default=None, to=orm['proso_models.Item'], blank=True, unique=True)),
            ('lang', self.gf('django.db.models.fields.CharField')(max_length=2, null=True)),
            ('text', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal(u'proso_flashcards', ['Context'])

        # Adding model 'Flashcard'
        db.create_table(u'proso_flashcards_flashcard', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('identifier', self.gf('django.db.models.fields.SlugField')(default=None, max_length=50, unique=True, null=True, blank=True)),
            ('item', self.gf('django.db.models.fields.related.ForeignKey')(related_name='flashcards', null=True, default=None, to=orm['proso_models.Item'], blank=True, unique=True)),
            ('term', self.gf('django.db.models.fields.related.ForeignKey')(related_name='flashcards', to=orm['proso_flashcards.Term'])),
            ('context', self.gf('django.db.models.fields.related.ForeignKey')(related_name='flashcards', to=orm['proso_flashcards.Context'])),
        ))
        db.send_create_signal(u'proso_flashcards', ['Flashcard'])

        # Adding model 'Category'
        db.create_table(u'proso_flashcards_category', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('identifier', self.gf('django.db.models.fields.SlugField')(default=None, max_length=50, unique=True, null=True, blank=True)),
            ('item', self.gf('django.db.models.fields.related.ForeignKey')(related_name='flashcard_categories', null=True, default=None, to=orm['proso_models.Item'], blank=True, unique=True)),
            ('lang', self.gf('django.db.models.fields.CharField')(max_length=2)),
            ('text', self.gf('django.db.models.fields.TextField')()),
            ('type', self.gf('django.db.models.fields.CharField')(max_length=50)),
        ))
        db.send_create_signal(u'proso_flashcards', ['Category'])

        # Adding M2M table for field subcategories on 'Category'
        m2m_table_name = db.shorten_name(u'proso_flashcards_category_subcategories')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('from_category', models.ForeignKey(orm[u'proso_flashcards.category'], null=False)),
            ('to_category', models.ForeignKey(orm[u'proso_flashcards.category'], null=False))
        ))
        db.create_unique(m2m_table_name, ['from_category_id', 'to_category_id'])

        # Adding M2M table for field terms on 'Category'
        m2m_table_name = db.shorten_name(u'proso_flashcards_category_terms')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('category', models.ForeignKey(orm[u'proso_flashcards.category'], null=False)),
            ('term', models.ForeignKey(orm[u'proso_flashcards.term'], null=False))
        ))
        db.create_unique(m2m_table_name, ['category_id', 'term_id'])

        # Adding model 'FlashcardAnswer'
        db.create_table(u'proso_flashcards_flashcardanswer', (
            (u'answer_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['proso_models.Answer'], unique=True, primary_key=True)),
            ('from_term_direction', self.gf('django.db.models.fields.BooleanField')()),
            ('options', self.gf('django.db.models.fields.TextField')(null=True)),
        ))
        db.send_create_signal(u'proso_flashcards', ['FlashcardAnswer'])


    def backwards(self, orm):
        # Deleting model 'Term'
        db.delete_table(u'proso_flashcards_term')

        # Deleting model 'Context'
        db.delete_table(u'proso_flashcards_context')

        # Deleting model 'Flashcard'
        db.delete_table(u'proso_flashcards_flashcard')

        # Deleting model 'Category'
        db.delete_table(u'proso_flashcards_category')

        # Removing M2M table for field subcategories on 'Category'
        db.delete_table(db.shorten_name(u'proso_flashcards_category_subcategories'))

        # Removing M2M table for field terms on 'Category'
        db.delete_table(db.shorten_name(u'proso_flashcards_category_terms'))

        # Deleting model 'FlashcardAnswer'
        db.delete_table(u'proso_flashcards_flashcardanswer')


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
            'Meta': {'object_name': 'Category'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'identifier': ('django.db.models.fields.SlugField', [], {'default': 'None', 'max_length': '50', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'item': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'flashcard_categories'", 'null': 'True', 'default': 'None', 'to': "orm['proso_models.Item']", 'blank': 'True', 'unique': 'True'}),
            'lang': ('django.db.models.fields.CharField', [], {'max_length': '2'}),
            'subcategories': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'subcategories_rel_+'", 'to': u"orm['proso_flashcards.Category']"}),
            'terms': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'parents'", 'symmetrical': 'False', 'to': u"orm['proso_flashcards.Term']"}),
            'text': ('django.db.models.fields.TextField', [], {}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'proso_flashcards.context': {
            'Meta': {'object_name': 'Context'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'identifier': ('django.db.models.fields.SlugField', [], {'default': 'None', 'max_length': '50', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'item': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'flashcard_contexts'", 'null': 'True', 'default': 'None', 'to': "orm['proso_models.Item']", 'blank': 'True', 'unique': 'True'}),
            'lang': ('django.db.models.fields.CharField', [], {'max_length': '2', 'null': 'True'}),
            'text': ('django.db.models.fields.TextField', [], {})
        },
        u'proso_flashcards.flashcard': {
            'Meta': {'object_name': 'Flashcard'},
            'context': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'flashcards'", 'to': u"orm['proso_flashcards.Context']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'identifier': ('django.db.models.fields.SlugField', [], {'default': 'None', 'max_length': '50', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'item': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'flashcards'", 'null': 'True', 'default': 'None', 'to': "orm['proso_models.Item']", 'blank': 'True', 'unique': 'True'}),
            'term': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'flashcards'", 'to': u"orm['proso_flashcards.Term']"})
        },
        u'proso_flashcards.flashcardanswer': {
            'Meta': {'object_name': 'FlashcardAnswer', '_ormbases': ['proso_models.Answer']},
            u'answer_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['proso_models.Answer']", 'unique': 'True', 'primary_key': 'True'}),
            'from_term_direction': ('django.db.models.fields.BooleanField', [], {}),
            'options': ('django.db.models.fields.TextField', [], {'null': 'True'})
        },
        u'proso_flashcards.term': {
            'Meta': {'object_name': 'Term'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'identifier': ('django.db.models.fields.SlugField', [], {'default': 'None', 'max_length': '50', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'item': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'flashcard_terms'", 'null': 'True', 'default': 'None', 'to': "orm['proso_models.Item']", 'blank': 'True', 'unique': 'True'}),
            'lang': ('django.db.models.fields.CharField', [], {'max_length': '2'}),
            'text': ('django.db.models.fields.TextField', [], {})
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