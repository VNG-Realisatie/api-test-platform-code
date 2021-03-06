# Generated by Django 2.2.4 on 2019-09-26 10:01

from django.db import migrations


def remove_old_scheduled_server_runs(apps, schema_editor):
    ServerRun = apps.get_model('servervalidation', 'ServerRun')
    ServerRun.objects.filter(scheduled=True).delete()

class Migration(migrations.Migration):

    dependencies = [
        ('servervalidation', '0084_auto_20190923_1143'),
    ]

    operations = [
        migrations.RunPython(remove_old_scheduled_server_runs, migrations.RunPython.noop)
    ]
