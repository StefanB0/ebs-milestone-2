# Generated by Django 5.1.2 on 2024-11-08 13:33

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tasks", "0005_taskattachment_file_upload_url"),
    ]

    operations = [
        migrations.AlterField(
            model_name="taskattachment",
            name="file_upload_url",
            field=models.CharField(max_length=255),
        ),
    ]
