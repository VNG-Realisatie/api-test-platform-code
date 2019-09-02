# Generated by Django 2.2.4 on 2019-09-02 13:56

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('servervalidation', '0075_auto_20190902_1521'),
    ]

    operations = [
        migrations.AddField(
            model_name='testscenario',
            name='public_logs',
            field=models.BooleanField(blank=True, default=True, help_text='When enabled, the HTML and JSON logs generated by Newman for this TestScenario will be publicly available.'),
        ),
    ]