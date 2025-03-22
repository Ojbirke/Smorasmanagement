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
    team = models.ForeignKey(Team, related_name='players', on_delete=models.SET_NULL, null=True, blank=True)
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
    
    home_team = models.ForeignKey(Team, related_name='home_matches', on_delete=models.CASCADE)
    away_team = models.ForeignKey(Team, related_name='away_matches', on_delete=models.CASCADE)
    home_score = models.PositiveIntegerField(blank=True, null=True)
    away_score = models.PositiveIntegerField(blank=True, null=True)
    date = models.DateTimeField()
    location = models.CharField(max_length=100, blank=True, null=True)
    match_type = models.CharField(max_length=20, choices=MATCH_TYPE_CHOICES, default='Friendly')
    notes = models.TextField(blank=True, null=True)
    players = models.ManyToManyField(Player, through='MatchAppearance', related_name='matches')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.home_team} vs {self.away_team} ({self.date.strftime('%Y-%m-%d')})"

    def get_absolute_url(self):
        return reverse('match-detail', args=[str(self.id)])

    def get_result(self):
        if self.home_score is None or self.away_score is None:
            return "Match not played yet"
        if self.home_score > self.away_score:
            return f"{self.home_team} won"
        elif self.home_score < self.away_score:
            return f"{self.away_team} won"
        else:
            return "Draw"


class MatchAppearance(models.Model):
    player = models.ForeignKey(Player, related_name='match_appearances', on_delete=models.CASCADE)
    match = models.ForeignKey(Match, related_name='appearances', on_delete=models.CASCADE)
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
