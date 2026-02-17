from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("directory", "0007_saunasubmission"),
    ]

    operations = [
        migrations.AddField(
            model_name="listing",
            name="latitude",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="listing",
            name="longitude",
            field=models.FloatField(blank=True, null=True),
        ),
    ]
