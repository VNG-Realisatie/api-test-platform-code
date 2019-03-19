# Generated by Django 2.2a1 on 2019-03-04 08:42

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('servervalidation', '0049_auto_20190304_0930'),
    ]

    operations = [
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
        migrations.AlterField(
            model_name='serverheader',
            name='server_run',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='servervalidation.ServerRun'),
        ),
        migrations.AlterField(
            model_name='serverrun',
            name='status',
            field=models.CharField(choices=[('starting', 'starting'), ('running', 'running'), ('shutting down', 'shutting down'), ('stopped', 'stopped'), ('Error deployment', 'error deploy')], default='starting', max_length=20),
        ),
    ]