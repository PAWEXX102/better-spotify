# Generated by Django 5.1.1 on 2025-04-04 15:28
 


 

from django.db import migrations
 


 


 

class Migration(migrations.Migration):
 


 

    dependencies = [
 

        ('api', '0003_album_image'),
 

    ]
 


 

    operations = [
 

        migrations.RemoveField(
 

            model_name='album',
 

            name='img_url',
 

        ),
 

    ]