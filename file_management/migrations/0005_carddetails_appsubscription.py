# Generated by Django 5.1.3 on 2024-12-23 09:33

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('file_management', '0004_userfile_user_filecategory_userfile_category'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CardDetails',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('card_type', models.CharField(choices=[('credit', 'Credit Card'), ('debit', 'Debit Card')], max_length=10)),
                ('bank_name', models.CharField(max_length=100)),
                ('card_number', models.CharField(max_length=16)),
                ('card_holder', models.CharField(max_length=100)),
                ('expiry_month', models.CharField(max_length=2)),
                ('expiry_year', models.CharField(max_length=4)),
                ('cvv', models.CharField(max_length=4)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('extracted_from_doc', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='file_management.userfile')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='AppSubscription',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('app_name', models.CharField(max_length=100)),
                ('subscription_type', models.CharField(max_length=50)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                ('auto_renewal', models.BooleanField(default=True)),
                ('status', models.CharField(choices=[('active', 'Active'), ('expired', 'Expired'), ('canceled', 'Canceled')], default='active', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('extracted_from_doc', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='file_management.userfile')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('payment_method', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='file_management.carddetails')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
