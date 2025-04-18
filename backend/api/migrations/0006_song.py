# Generated by Django 5.1.1 on 2025-04-05 17:17

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0005_artist_image'),
    ]

    operations = [
        migrations.CreateModel(
            name='Song',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('duration', models.DurationField()),
                ('file', models.FileField(upload_to='songs/')),
                ('lyrics', models.TextField(blank=True, null=True)),
                ('album', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='songs', to='api.album')),
            ],
        ),
    ]
