from __future__ import unicode_literals
from django.db import migrations
from proso.list import group_by


def compute_setup_probability(apps, schema_editor):
    ExperimentSetup = apps.get_model("proso_configab", "ExperimentSetup")
    for setups in group_by(ExperimentSetup.objects.prefetch_related('values').all(), by=lambda s: s.experiment_id).values():
        probs = {s.id: sum([v.probability for v in s.values.all()]) for s in setups}
        total = sum(probs.values())
        for s in setups:
            s.probability = probs[s.id] / (total if total > 0 else 1)
            s.save()


class Migration(migrations.Migration):

    dependencies = [
        ('proso_configab', '0002_experimentsetup_probability'),
    ]

    operations = [
        migrations.RunPython(compute_setup_probability),
    ]
