# Generated by Django 2.2.4 on 2019-11-15 12:02

from django.db import migrations


def set_null_values_to_empty_string(apps, schema_editor):
    fields = ['product_role', 'software_product', 'supplier_name', 'software_version']
    ServerRun = apps.get_model('servervalidation', 'ServerRun')
    for server_run in ServerRun.objects.all():
        for field in fields:
            value = getattr(server_run, field)
            if value is None:
                setattr(server_run, field, '')
        server_run.save()


class Migration(migrations.Migration):

    dependencies = [
        ('servervalidation', '0101_auto_20191114_1639'),
    ]

    operations = [
        migrations.RunPython(set_null_values_to_empty_string, migrations.RunPython.noop)
    ]
