# Generated by Django 4.1.5 on 2024-01-31 00:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('qna', '0008_polls'),
    ]

    operations = [
        migrations.AddField(
            model_name='answer',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to='posts/'),
        ),
    ]
