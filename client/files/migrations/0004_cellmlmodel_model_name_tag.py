# Generated by Django 4.0.7 on 2022-11-02 15:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('files', '0003_alter_cellmlmodel_ap_predict_model_call_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='cellmlmodel',
            name='model_name_tag',
            field=models.CharField(blank=True, help_text='Model name tag used for finding lookup tables.\nThis is automatically populated when a cellml file is uploaded.\nThis option is only available to admins.', max_length=255, null=True),
        ),
    ]
