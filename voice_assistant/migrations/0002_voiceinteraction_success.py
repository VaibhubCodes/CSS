# Generated by Django 5.1.3 on 2025-04-03 19:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("voice_assistant", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="voiceinteraction",
            name="success",
            field=models.BooleanField(default=True),
        ),
    ]
