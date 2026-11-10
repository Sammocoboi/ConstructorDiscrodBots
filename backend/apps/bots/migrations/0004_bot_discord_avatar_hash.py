from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("bots", "0003_merge_20261029_1106")]

    operations = [
        migrations.AddField(
            model_name="bot",
            name="discord_avatar_hash",
            field=models.CharField(blank=True, default="", max_length=34),
        ),
    ]
