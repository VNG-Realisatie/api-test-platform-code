# Generated by Django 2.2.13 on 2021-01-22 13:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('design_rules', '0024_designruletestsuite_specification_url'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='designruletestsuite',
            name='specification_url',
        ),
        migrations.AddField(
            model_name='designrulesession',
            name='specification_url',
            field=models.URLField(blank=True),
        ),
    ]
