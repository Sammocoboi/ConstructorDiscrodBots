
import django.db.models.deletion
import django.utils.timezone
import uuid
from django.db import migrations, models

class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Bot',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('owner_id', models.CharField(db_index=True, default='default-user', max_length=64)),
                ('name', models.CharField(default='Новый бот', max_length=100)),
                ('discord_application_id', models.CharField(blank=True, db_index=True, max_length=64, null=True)),
                ('discord_bot_user_id', models.CharField(blank=True, max_length=64, null=True)),
                ('avatar_url', models.URLField(blank=True, max_length=500, null=True)),
                ('discriminator', models.CharField(blank=True, default='0', max_length=10)),
                ('token_encrypted', models.TextField(blank=True, default='')),
                ('status', models.CharField(choices=[('stopped', 'Остановлен'), ('starting', 'Запускается'), ('online', 'В сети'), ('error', 'Ошибка'), ('suspended', 'Приостановлен')], default='stopped', max_length=20)),
                ('desired_state', models.CharField(choices=[('running', 'Работает'), ('stopped', 'Остановлен')], default='stopped', max_length=20)),
                ('last_error', models.TextField(blank=True, null=True)),
                ('last_error_at', models.DateTimeField(blank=True, null=True)),
                ('profile', models.JSONField(default=dict)),
                ('intents', models.JSONField(default=list)),
                ('commands_hash', models.CharField(blank=True, default='', max_length=64)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'db_table': 'bots',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='BotGuild',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('guild_id', models.CharField(db_index=True, max_length=64)),
                ('guild_name', models.CharField(default='Discord Server', max_length=150)),
                ('icon_url', models.URLField(blank=True, max_length=500, null=True)),
                ('joined_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('left_at', models.DateTimeField(blank=True, null=True)),
                ('settings', models.JSONField(default=dict)),
                ('enabled_modules', models.JSONField(default=list)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('bot', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='guilds', to='bots.bot')),
            ],
            options={
                'db_table': 'bot_guilds',
                'ordering': ['guild_name'],
                'unique_together': {('bot', 'guild_id')},
            },
        ),
    ]
