# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2018-12-17 14:05
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('testsession', '0035_sessionlog_response_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sessionlog',
            name='response_status',
            field=models.PositiveIntegerField(blank=True, default=None, null=True),
        ),
    ]
