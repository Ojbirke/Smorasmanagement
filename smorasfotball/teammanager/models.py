from django.db import models
from django.urls import reverse


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
    opponent_name = models.CharField(max_length=100)
    
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
