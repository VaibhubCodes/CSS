# Generated by Django 5.1.3 on 2025-04-21 18:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("file_management", "0009_userfile_is_favorite"),
    ]

    operations = [
        migrations.AddField(
            model_name="userfile",
            name="coins_awarded",
            field=models.BooleanField(default=False),
        ),
    ]
