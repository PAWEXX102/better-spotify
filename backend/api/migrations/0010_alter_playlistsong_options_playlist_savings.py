# Generated by Django 5.2 on 2025-04-30 10:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0009_library_libraryitem'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='playlistsong',
            options={'ordering': ['playlist', 'order']},
        ),
        migrations.AddField(
            model_name='playlist',
            name='savings',
            field=models.PositiveIntegerField(default=0),
        ),
    ]
