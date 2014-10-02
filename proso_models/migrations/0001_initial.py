# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Item'
        db.create_table(u'proso_models_item', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('proso_models', ['Item'])

        # Adding model 'Answer'
        db.create_table(u'proso_models_answer', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('item', self.gf('django.db.models.fields.related.ForeignKey')(related_name='item_answers', to=orm['proso_models.Item'])),
            ('item_asked', self.gf('django.db.models.fields.related.ForeignKey')(related_name='item_asked_answers', to=orm['proso_models.Item'])),
            ('item_answered', self.gf('django.db.models.fields.related.ForeignKey')(default=None, related_name='item_answered_answers', null=True, blank=True, to=orm['proso_models.Item'])),
            ('time', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('response_time', self.gf('django.db.models.fields.IntegerField')(default=0)),
        ))
        db.send_create_signal('proso_models', ['Answer'])

        # Adding model 'Variable'
        db.create_table(u'proso_models_variable', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(default=None, to=orm['auth.User'], null=True, blank=True)),
            ('item_primary', self.gf('django.db.models.fields.related.ForeignKey')(default=None, related_name='item_primary_variables', null=True, blank=True, to=orm['proso_models.Item'])),
            ('item_secondary', self.gf('django.db.models.fields.related.ForeignKey')(default=None, related_name='item_secondary_variables', null=True, blank=True, to=orm['proso_models.Item'])),
            ('key', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('value', self.gf('django.db.models.fields.FloatField')()),
            ('audit', self.gf('django.db.models.fields.BooleanField')()),
            ('updated', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
        ))
        db.send_create_signal('proso_models', ['Variable'])

        # Adding unique constraint on 'Variable', fields ['key', 'user', 'item_primary', 'item_secondary']
        db.create_unique(u'proso_models_variable', ['key', 'user_id', 'item_primary_id', 'item_secondary_id'])

        # Adding index on 'Variable', fields ['key', 'user']
        db.create_index(u'proso_models_variable', ['key', 'user_id'])

        # Adding index on 'Variable', fields ['key', 'item_primary']
        db.create_index(u'proso_models_variable', ['key', 'item_primary_id'])

        # Adding index on 'Variable', fields ['key', 'user', 'item_primary']
        db.create_index(u'proso_models_variable', ['key', 'user_id', 'item_primary_id'])

        # Adding index on 'Variable', fields ['key', 'user', 'item_primary', 'item_secondary']
        db.create_index(u'proso_models_variable', ['key', 'user_id', 'item_primary_id', 'item_secondary_id'])

        # Adding model 'Audit'
        db.create_table(u'proso_models_audit', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(default=None, to=orm['auth.User'], null=True, blank=True)),
            ('item_primary', self.gf('django.db.models.fields.related.ForeignKey')(default=None, related_name='item_primary_audits', null=True, blank=True, to=orm['proso_models.Item'])),
            ('item_secondary', self.gf('django.db.models.fields.related.ForeignKey')(default=None, related_name='item_secondary_audits', null=True, blank=True, to=orm['proso_models.Item'])),
            ('key', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('value', self.gf('django.db.models.fields.FloatField')()),
            ('time', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
        ))
        db.send_create_signal('proso_models', ['Audit'])

        # Adding unique constraint on 'Audit', fields ['key', 'user', 'item_primary', 'item_secondary']
        db.create_unique(u'proso_models_audit', ['key', 'user_id', 'item_primary_id', 'item_secondary_id'])

        # Adding index on 'Audit', fields ['key', 'user']
        db.create_index(u'proso_models_audit', ['key', 'user_id'])

        # Adding index on 'Audit', fields ['key', 'item_primary']
        db.create_index(u'proso_models_audit', ['key', 'item_primary_id'])

        # Adding index on 'Audit', fields ['key', 'user', 'item_primary']
        db.create_index(u'proso_models_audit', ['key', 'user_id', 'item_primary_id'])

        # Adding index on 'Audit', fields ['key', 'user', 'item_primary', 'item_secondary']
        db.create_index(u'proso_models_audit', ['key', 'user_id', 'item_primary_id', 'item_secondary_id'])

    def backwards(self, orm):
        # Removing index on 'Audit', fields ['key', 'user', 'item_primary', 'item_secondary']
        db.delete_index(u'proso_models_audit', ['key', 'user_id', 'item_primary_id', 'item_secondary_id'])

        # Removing index on 'Audit', fields ['key', 'user', 'item_primary']
        db.delete_index(u'proso_models_audit', ['key', 'user_id', 'item_primary_id'])

        # Removing index on 'Audit', fields ['key', 'item_primary']
        db.delete_index(u'proso_models_audit', ['key', 'item_primary_id'])

        # Removing index on 'Audit', fields ['key', 'user']
        db.delete_index(u'proso_models_audit', ['key', 'user_id'])

        # Removing unique constraint on 'Audit', fields ['key', 'user', 'item_primary', 'item_secondary']
        db.delete_unique(u'proso_models_audit', ['key', 'user_id', 'item_primary_id', 'item_secondary_id'])

        # Removing index on 'Variable', fields ['key', 'user', 'item_primary', 'item_secondary']
        db.delete_index(u'proso_models_variable', ['key', 'user_id', 'item_primary_id', 'item_secondary_id'])

        # Removing index on 'Variable', fields ['key', 'user', 'item_primary']
        db.delete_index(u'proso_models_variable', ['key', 'user_id', 'item_primary_id'])

        # Removing index on 'Variable', fields ['key', 'item_primary']
        db.delete_index(u'proso_models_variable', ['key', 'item_primary_id'])

        # Removing index on 'Variable', fields ['key', 'user']
        db.delete_index(u'proso_models_variable', ['key', 'user_id'])

        # Removing unique constraint on 'Variable', fields ['key', 'user', 'item_primary', 'item_secondary']
        db.delete_unique(u'proso_models_variable', ['key', 'user_id', 'item_primary_id', 'item_secondary_id'])

        # Deleting model 'Item'
        db.delete_table(u'proso_models_item')

        # Deleting model 'Answer'
        db.delete_table(u'proso_models_answer')

        # Deleting model 'Variable'
        db.delete_table(u'proso_models_variable')

        # Deleting model 'Audit'
        db.delete_table(u'proso_models_audit')

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
        'proso_models.answer': {
            'Meta': {'object_name': 'Answer'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'item': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'item_answers'", 'to': "orm['proso_models.Item']"}),
            'item_answered': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'related_name': "'item_answered_answers'", 'null': 'True', 'blank': 'True', 'to': "orm['proso_models.Item']"}),
            'item_asked': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'item_asked_answers'", 'to': "orm['proso_models.Item']"}),
            'response_time': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        'proso_models.audit': {
            'Meta': {'unique_together': "(('key', 'user', 'item_primary', 'item_secondary'),)", 'object_name': 'Audit', 'index_together': "[['key', 'user'], ['key', 'item_primary'], ['key', 'user', 'item_primary'], ['key', 'user', 'item_primary', 'item_secondary']]"},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'item_primary': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'related_name': "'item_primary_audits'", 'null': 'True', 'blank': 'True', 'to': "orm['proso_models.Item']"}),
            'item_secondary': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'related_name': "'item_secondary_audits'", 'null': 'True', 'blank': 'True', 'to': "orm['proso_models.Item']"}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'value': ('django.db.models.fields.FloatField', [], {})
        },
        'proso_models.item': {
            'Meta': {'object_name': 'Item'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'proso_models.variable': {
            'Meta': {'unique_together': "(('key', 'user', 'item_primary', 'item_secondary'),)", 'object_name': 'Variable', 'index_together': "[['key', 'user'], ['key', 'item_primary'], ['key', 'user', 'item_primary'], ['key', 'user', 'item_primary', 'item_secondary']]"},
            'audit': ('django.db.models.fields.BooleanField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'item_primary': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'related_name': "'item_primary_variables'", 'null': 'True', 'blank': 'True', 'to': "orm['proso_models.Item']"}),
            'item_secondary': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'related_name': "'item_secondary_variables'", 'null': 'True', 'blank': 'True', 'to': "orm['proso_models.Item']"}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'value': ('django.db.models.fields.FloatField', [], {})
        }
    }

    complete_apps = ['proso_models']
