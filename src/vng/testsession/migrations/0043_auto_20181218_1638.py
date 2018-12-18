# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2018-12-18 15:38
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('testsession', '0042_auto_20181218_1627'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='testsession',
            name='session',
        ),
        migrations.AddField(
            model_name='testsession',
            name='vng_endpoint',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='testsession.VNGEndpoint'),
            preserve_default=False,
        ),
    ]
