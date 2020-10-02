# Generated by Django 2.2.13 on 2020-09-30 11:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('design_rules', '0006_remove_designrulesession_documentation_endpoint'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='designruleresult',
            options={'ordering': ('design_rule',)},
        ),
        migrations.RemoveField(
            model_name='designrulesession',
            name='test_result',
        ),
        migrations.AddField(
            model_name='designrulesession',
            name='percentage_score',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5),
        ),
    ]
