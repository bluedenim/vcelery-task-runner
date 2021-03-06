# Generated by Django 3.2.13 on 2022-06-04 06:11

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='TaskRunRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('task_name', models.CharField(db_index=True, max_length=200)),
                ('task_id', models.CharField(db_index=True, max_length=100)),
                ('run_with', models.TextField(help_text='The params the task was run with')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('run_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
