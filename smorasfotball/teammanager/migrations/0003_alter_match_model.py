from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('teammanager', '0002_remove_player_team'),
    ]

    operations = [
        # Remove old fields
        migrations.RemoveField(
            model_name='match',
            name='home_team',
        ),
        migrations.RemoveField(
            model_name='match',
            name='away_team',
        ),
        migrations.RemoveField(
            model_name='match',
            name='home_score',
        ),
        migrations.RemoveField(
            model_name='match',
            name='away_score',
        ),
        
        # Add new fields
        migrations.AddField(
            model_name='match',
            name='smoras_team',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='matches', to='teammanager.team'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='match',
            name='opponent_name',
            field=models.CharField(default='Unknown Opponent', max_length=100),
        ),
        migrations.AddField(
            model_name='match',
            name='location_type',
            field=models.CharField(choices=[('Home', 'Home'), ('Away', 'Away'), ('Neutral', 'Neutral')], default='Home', max_length=10),
        ),
        migrations.AddField(
            model_name='match',
            name='smoras_score',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='match',
            name='opponent_score',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]