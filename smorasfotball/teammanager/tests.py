from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Team, Player, Match, MatchAppearance


class TeamModelTest(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name='Test Team', description='Test Description')
    
    def test_team_creation(self):
        self.assertEqual(self.team.name, 'Test Team')
        self.assertEqual(self.team.description, 'Test Description')


class PlayerModelTest(TestCase):
    def setUp(self):
        self.team = Team.objects.create(name='Test Team')
        self.player = Player.objects.create(
            first_name='John',
            last_name='Doe',
            team=self.team,
            position='Forward'
        )
    
    def test_player_creation(self):
        self.assertEqual(self.player.first_name, 'John')
        self.assertEqual(self.player.last_name, 'Doe')
        self.assertEqual(self.player.team, self.team)
        self.assertEqual(self.player.position, 'Forward')
        self.assertEqual(str(self.player), 'John Doe')


class MatchModelTest(TestCase):
    def setUp(self):
        self.home_team = Team.objects.create(name='Home Team')
        self.away_team = Team.objects.create(name='Away Team')
        self.match = Match.objects.create(
            home_team=self.home_team,
            away_team=self.away_team,
            date='2023-01-01T12:00:00Z',
            home_score=2,
            away_score=1
        )
    
    def test_match_creation(self):
        self.assertEqual(self.match.home_team, self.home_team)
        self.assertEqual(self.match.away_team, self.away_team)
        self.assertEqual(self.match.home_score, 2)
        self.assertEqual(self.match.away_score, 1)
        self.assertEqual(self.match.get_result(), 'Home Team won')


class ViewsTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.team = Team.objects.create(name='Test Team')
        self.player = Player.objects.create(first_name='John', team=self.team)
        
    def test_dashboard_view(self):
        self.client.login(username='testuser', password='testpassword')
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'teammanager/dashboard.html')
        
    def test_team_list_view(self):
        self.client.login(username='testuser', password='testpassword')
        response = self.client.get(reverse('team-list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'teammanager/team_list.html')
        self.assertContains(response, 'Test Team')
        
    def test_player_list_view(self):
        self.client.login(username='testuser', password='testpassword')
        response = self.client.get(reverse('player-list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'teammanager/player_list.html')
        self.assertContains(response, 'John')
