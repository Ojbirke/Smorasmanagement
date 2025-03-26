from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('teammanager', '0006_formationtemplate_player_count'),
    ]

    operations = [
        migrations.AlterField(
            model_name='formationtemplate',
            name='player_count',
            field=models.PositiveSmallIntegerField(choices=[(5, '5er fotball'), (7, '7er fotball'), (9, '9er fotball'), (11, '11er fotball')], default=7, help_text='Select the number of players for this formation'),
        ),
    ]