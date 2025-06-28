
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [
        ('file_management', '0012_userfile_locked_userfile_locked_password'),
    ]

    operations = [
        migrations.AddField(
            model_name='userfile',
            name='document_side',
            field=models.CharField(
                choices=[('single', 'Single Side'), ('front', 'Front Side'), ('back', 'Back Side')],
                default='single',
                max_length=10
            ),
        ),
        migrations.AddField(
            model_name='userfile',
            name='paired_document',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='paired_with',
                to='file_management.userfile'
            ),
        ),
        migrations.AddField(
            model_name='userfile',
            name='document_type_name',
            field=models.CharField(
                blank=True,
                help_text='e.g., Aadhar Card, PAN Card, License',
                max_length=100
            ),
        ),
    ]