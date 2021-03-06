# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2019-01-22 14:29
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('servervalidation', '0025_auto_20190122_1412'),
    ]

    operations = [
        migrations.AddField(
            model_name='postmantestresult',
            name='status',
            field=models.CharField(choices=[('Success', 'running'), ('Failed', 'stopped')], default=None, max_length=10, null=True),
        ),
        migrations.AlterField(
            model_name='endpoint',
            name='server_run',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='servervalidation.ServerRun'),
        ),
        migrations.AlterField(
            model_name='postmantestresult',
            name='server_run',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='servervalidation.ServerRun'),
        ),
    ]
