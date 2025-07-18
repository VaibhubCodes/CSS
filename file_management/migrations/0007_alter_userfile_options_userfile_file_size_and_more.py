# Generated by Django 5.1.3 on 2024-12-27 09:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('file_management', '0006_expirydetails'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='userfile',
            options={'ordering': ['-upload_date'], 'verbose_name': 'User File', 'verbose_name_plural': 'User Files'},
        ),
        migrations.AddField(
            model_name='userfile',
            name='file_size',
            field=models.BigIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='userfile',
            name='is_public',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='userfile',
            name='original_filename',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='userfile',
            name='s3_key',
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
