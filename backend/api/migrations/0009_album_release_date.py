# Generated by Django 5.1.1 on 2025-04-06 08:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0008_song_plays'),
    ]

    operations = [
        migrations.AddField(
            model_name='album',
            name='release_date',
            field=models.DateField(default='2023-01-01'),
        ),
    ]
