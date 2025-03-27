from django.db import models
from django.urls import reverse
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('player', 'Player'),
        ('coach', 'Coach'),
        ('admin', 'Admin'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='player')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    player = models.ForeignKey('Player', on_delete=models.SET_NULL, null=True, blank=True, related_name='user_profile')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"
    
    def is_approved(self):
        return self.status == 'approved'
    
    def is_pending(self):
        return self.status == 'pending'
    
    def is_admin(self):
        return self.role == 'admin' and self.is_approved()
    
    def is_coach(self):
        return self.role == 'coach' and self.is_approved()
    
    def is_player(self):
        return self.role == 'player' and self.is_approved()


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create a UserProfile whenever a new User is created"""
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save the UserProfile whenever the User is saved"""
    if hasattr(instance, 'profile'):
        instance.profile.save()
    else:
        # If somehow a profile wasn't created, create one now
        UserProfile.objects.create(user=instance)


class Team(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('team-detail', args=[str(self.id)])


class Player(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    position = models.CharField(max_length=50, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}" if self.last_name else self.first_name

    def get_absolute_url(self):
        return reverse('player-detail', args=[str(self.id)])

    def total_matches(self):
        return self.match_appearances.count()


class Match(models.Model):
    MATCH_TYPE_CHOICES = [
        ('Friendly', 'Friendly'),
        ('League', 'League'),
        ('Cup', 'Cup'),
        ('Tournament', 'Tournament'),
    ]
    
    LOCATION_CHOICES = [
        ('Home', 'Home'),
        ('Away', 'Away'),
        ('Neutral', 'Neutral'),
    ]
    
    # Smørås team (our team)
    smoras_team = models.ForeignKey(Team, related_name='matches', on_delete=models.CASCADE)
    
    # Opponent team name (text field)
    opponent_name = models.CharField(max_length=100, default='Unknown Opponent')
    
    # Match location type (home/away/neutral)
    location_type = models.CharField(max_length=10, choices=LOCATION_CHOICES, default='Home')
    
    # Scores
    smoras_score = models.PositiveIntegerField(blank=True, null=True)
    opponent_score = models.PositiveIntegerField(blank=True, null=True)
    
    date = models.DateTimeField()
    location = models.CharField(max_length=100, blank=True, null=True)
    match_type = models.CharField(max_length=20, choices=MATCH_TYPE_CHOICES, default='Friendly')
    notes = models.TextField(blank=True, null=True)
    players = models.ManyToManyField(Player, through='MatchAppearance', related_name='matches')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.location_type == 'Home':
            return f"{self.smoras_team} vs {self.opponent_name} ({self.date.strftime('%Y-%m-%d')})"
        elif self.location_type == 'Away':
            return f"{self.opponent_name} vs {self.smoras_team} ({self.date.strftime('%Y-%m-%d')})"
        else:
            return f"{self.smoras_team} vs {self.opponent_name} ({self.date.strftime('%Y-%m-%d')}) at {self.location}"

    def get_absolute_url(self):
        return reverse('match-detail', args=[str(self.id)])

    def get_result(self):
        if self.smoras_score is None or self.opponent_score is None:
            return "Match not played yet"
        
        if self.smoras_score > self.opponent_score:
            return f"{self.smoras_team} won"
        elif self.smoras_score < self.opponent_score:
            return f"{self.opponent_name} won"
        else:
            return "Draw"
            
    @property
    def home_team(self):
        """Backward compatibility for templates"""
        if self.location_type == 'Away':
            return self.opponent_name
        return self.smoras_team
            
    @property
    def away_team(self):
        """Backward compatibility for templates"""
        if self.location_type == 'Away':
            return self.smoras_team
        return self.opponent_name
        
    @property
    def home_score(self):
        """Backward compatibility for templates"""
        if self.location_type == 'Away':
            return self.opponent_score
        return self.smoras_score
        
    @property
    def away_score(self):
        """Backward compatibility for templates"""
        if self.location_type == 'Away':
            return self.smoras_score
        return self.opponent_score


class MatchAppearance(models.Model):
    player = models.ForeignKey(Player, related_name='match_appearances', on_delete=models.CASCADE)
    match = models.ForeignKey(Match, related_name='appearances', on_delete=models.CASCADE)
    # Now only Smørås players can be in match appearances
    team = models.ForeignKey(Team, related_name='match_appearances', on_delete=models.CASCADE)
    minutes_played = models.PositiveIntegerField(blank=True, null=True)
    goals = models.PositiveIntegerField(default=0)
    assists = models.PositiveIntegerField(default=0)
    yellow_cards = models.PositiveIntegerField(default=0)
    red_card = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ('player', 'match')

    def __str__(self):
        return f"{self.player} in {self.match}"


class FormationTemplate(models.Model):
    """
    Pre-defined formation templates (e.g., 4-4-2, 4-3-3, etc.)
    """
    PLAYER_COUNT_CHOICES = [
        (5, '5er fotball'),
        (7, '7er fotball'),
        (9, '9er fotball'),
        (11, '11er fotball'),
    ]
    
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True, null=True)
    formation_structure = models.CharField(max_length=20, help_text="Format: e.g. '4-4-2', '4-3-3', etc.")
    player_count = models.PositiveSmallIntegerField(choices=PLAYER_COUNT_CHOICES, default=7, 
                                                   help_text="Select the number of players for this formation")
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} ({self.get_player_count_display()})"
        
    def validate_formation_structure(self):
        """Validate that the formation structure matches the player count (including goalkeeper)"""
        try:
            layers = self.formation_structure.split('-')
            total_outfield_players = sum(int(layer) for layer in layers)
            return total_outfield_players + 1 == self.player_count  # +1 for goalkeeper
        except (ValueError, AttributeError):
            return False


class LineupPosition(models.Model):
    """
    Defines positions on a football pitch
    """
    POSITION_TYPES = [
        ('GK', 'Goalkeeper'),
        ('DEF', 'Defender'),
        ('MID', 'Midfielder'),
        ('FWD', 'Forward'),
    ]
    
    name = models.CharField(max_length=50)
    short_name = models.CharField(max_length=10)
    position_type = models.CharField(max_length=3, choices=POSITION_TYPES)
    
    def __str__(self):
        return self.name


class Lineup(models.Model):
    """
    Stores lineups for matches
    """
    DIRECTION_CHOICES = [
        ('LR', 'Playing from Left (GK Left)'),
        ('RL', 'Playing from Right (GK Right)'),
    ]
    
    name = models.CharField(max_length=100)
    match = models.ForeignKey(Match, related_name='lineups', on_delete=models.CASCADE, null=True, blank=True)
    team = models.ForeignKey(Team, related_name='lineups', on_delete=models.CASCADE)
    formation = models.ForeignKey(FormationTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    is_template = models.BooleanField(default=False, help_text="Is this a reusable template lineup?")
    notes = models.TextField(blank=True, null=True)
    direction = models.CharField(max_length=2, choices=DIRECTION_CHOICES, default='LR',
                                help_text="Direction of play (LR=GK on left, RL=GK on right)")
    created_by = models.ForeignKey(User, related_name='created_lineups', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        match_str = f" - {self.match}" if self.match else ""
        return f"{self.name}{match_str}"
    
    def get_absolute_url(self):
        return reverse('lineup-detail', kwargs={'pk': self.pk})
    
    def duplicate(self):
        """Create a copy of this lineup"""
        new_lineup = Lineup.objects.create(
            name=f"Copy of {self.name}",
            team=self.team,
            formation=self.formation,
            is_template=False,
            notes=self.notes,
            created_by=self.created_by
        )
        
        # Copy player positions
        for position in self.player_positions.all():
            LineupPlayerPosition.objects.create(
                lineup=new_lineup,
                player=position.player,
                position=position.position,
                x_coordinate=position.x_coordinate,
                y_coordinate=position.y_coordinate,
                jersey_number=position.jersey_number,
                is_starter=position.is_starter,
                notes=position.notes
            )
        
        return new_lineup


class LineupPlayerPosition(models.Model):
    """
    Positions of players in a lineup
    """
    lineup = models.ForeignKey(Lineup, related_name='player_positions', on_delete=models.CASCADE)
    player = models.ForeignKey(Player, related_name='lineup_positions', on_delete=models.CASCADE)
    position = models.ForeignKey(LineupPosition, on_delete=models.SET_NULL, null=True, blank=True)
    x_coordinate = models.DecimalField(max_digits=5, decimal_places=2, help_text="X coordinate on pitch (0-100)")
    y_coordinate = models.DecimalField(max_digits=5, decimal_places=2, help_text="Y coordinate on pitch (0-100)")
    jersey_number = models.PositiveSmallIntegerField(blank=True, null=True)
    is_starter = models.BooleanField(default=True, help_text="Is this player in the starting lineup?")
    notes = models.CharField(max_length=100, blank=True, null=True)
    
    class Meta:
        unique_together = ('lineup', 'player')
    
    def __str__(self):
        position_str = f" ({self.position})" if self.position else ""
        return f"{self.player}{position_str} in {self.lineup}"


class MatchSession(models.Model):
    """
    Manages a match session with substitution tracking and configuration
    """
    match = models.ForeignKey(Match, related_name='sessions', on_delete=models.CASCADE)
    name = models.CharField(max_length=100, help_text="Name for this match session (e.g., 'Game Day 1')")
    created_by = models.ForeignKey(User, related_name='match_sessions', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Match configuration
    periods = models.PositiveSmallIntegerField(default=2, help_text="Number of periods in the match")
    period_length = models.PositiveSmallIntegerField(default=25, help_text="Length of each period in minutes")
    substitution_interval = models.PositiveSmallIntegerField(default=5, help_text="Time between substitutions in minutes")
    
    # Match status
    is_active = models.BooleanField(default=False, help_text="Whether this session is currently active")
    start_time = models.DateTimeField(null=True, blank=True, help_text="When the match actually started")
    current_period = models.PositiveSmallIntegerField(default=1, help_text="Current period of the match")
    elapsed_time = models.PositiveIntegerField(default=0, help_text="Elapsed time in seconds from previous periods")
    
    def __str__(self):
        return f"{self.name} - {self.match}"
    
    def get_absolute_url(self):
        return reverse('match-session-detail', args=[str(self.id)])
    
    def total_match_time(self):
        """Return the total match time in minutes"""
        return self.periods * self.period_length
    
    def expected_substitutions(self):
        """Return the expected number of substitutions"""
        if self.substitution_interval <= 0:
            return 0
        return (self.total_match_time() // self.substitution_interval) - 1


class PlayerSubstitution(models.Model):
    """
    Records player substitutions during a match session
    """
    match_session = models.ForeignKey(MatchSession, related_name='substitutions', on_delete=models.CASCADE)
    player_in = models.ForeignKey(Player, related_name='substitutions_in', on_delete=models.CASCADE)
    player_out = models.ForeignKey(Player, related_name='substitutions_out', on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True, help_text="When the substitution was made")
    minute = models.PositiveSmallIntegerField(help_text="Match minute when substitution occurred")
    period = models.PositiveSmallIntegerField(default=1, help_text="Match period when substitution occurred")
    notes = models.CharField(max_length=200, blank=True, null=True)
    
    def __str__(self):
        return f"{self.minute}' {self.player_in} for {self.player_out}"


class PlayingTime(models.Model):
    """
    Tracks actual playing time for each player in a match session
    """
    match_session = models.ForeignKey(MatchSession, related_name='playing_times', on_delete=models.CASCADE)
    player = models.ForeignKey(Player, related_name='match_playing_times', on_delete=models.CASCADE)
    minutes_played = models.PositiveSmallIntegerField(default=0, help_text="Total minutes played in this match")
    last_substitution_time = models.DateTimeField(null=True, blank=True, 
                                                help_text="Last time this player was involved in a substitution")
    is_on_pitch = models.BooleanField(default=False, help_text="Whether the player is currently on the pitch")
    
    class Meta:
        unique_together = ('match_session', 'player')
    
    def __str__(self):
        status = "playing" if self.is_on_pitch else "on bench"
        return f"{self.player} - {self.minutes_played} mins ({status})"
