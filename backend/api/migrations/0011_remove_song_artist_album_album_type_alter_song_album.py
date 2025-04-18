# Generated by Django 5.1.1 on 2025-04-06 12:42

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0010_song_artist_alter_song_album'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='song',
            name='artist',
        ),
        migrations.AddField(
            model_name='album',
            name='album_type',
            field=models.CharField(choices=[('single', 'Single'), ('album', 'Album'), ('ep', 'EP')], default='album', max_length=50),
        ),
        migrations.AlterField(
            model_name='song',
            name='album',
            field=models.ForeignKey(default=2, on_delete=django.db.models.deletion.CASCADE, related_name='songs', to='api.album'),
            preserve_default=False,
        ),
    ]
