# Generated by Django 2.2.13 on 2020-11-18 14:28

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('design_rules', '0019_remove_designruleresult_errors'),
    ]

    operations = [
        migrations.RenameField(
            model_name='designruleresult',
            old_name='new_errors',
            new_name='errors',
        ),
    ]
