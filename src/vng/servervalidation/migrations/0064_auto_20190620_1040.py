# Generated by Django 2.2.1 on 2019-06-20 08:40

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('servervalidation', '0063_auto_20190619_1247'),
    ]

    operations = [
        migrations.AlterField(
            model_name='endpoint',
            name='jwt',
            field=models.TextField(blank=True, default=None, null=True),
        ),
    ]
