# Generated by Django 2.2a1 on 2019-02-25 09:01

from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('testsession', '0058_auto_20190219_1131'),
    ]

    operations = [
        migrations.AlterField(
            model_name='scenariocase',
            name='url',
            field=models.CharField(help_text='\n                                                        General URL patter that will be compared\n                                                        with the request and eventually matched.\n                                                        Matching flag can be added, e.g. /test/{uuid}/stop\n                                                        will match every url with text instead of {uuid}.\n                                                        ', max_length=200),
        ),
        migrations.AddField(
            model_name='vngendpoint',
            name='name',
            field=models.CharField(max_length=200, validators=[django.core.validators.RegexValidator(code='Invalid_name', message='The name cannot contain spaces', regex='^[^ ]*$')]),
        ),
    ]
