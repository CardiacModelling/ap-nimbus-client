# Generated by Django 3.2.9 on 2021-12-13 17:33

import django.core.validators
from django.db import migrations, models
import files.models


class Migration(migrations.Migration):

    dependencies = [
        ('files', '0006_alter_cellmlmodel_cellml_file'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cellmlmodel',
            name='cellml_file',
            field=models.FileField(help_text='Please upload the cellml file here.', unique=True, upload_to='', validators=[django.core.validators.FileExtensionValidator(allowed_extensions=['cellml']), files.models.validate_is_xml]),
        ),
    ]
