# Generated by Django 3.2.9 on 2021-12-13 13:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('files', '0004_auto_20211213_1346'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cellmlmodel',
            name='visibility',
            field=models.CharField(choices=[('public', 'Public'), ('moderated', 'Moderated'), ('private', 'Private')], default=('public', 'Public'), help_text='Moderated = public and checked by a moderator<br/>Public = anyone can view<br/>Private = only you can view', max_length=16),
        ),
    ]
