from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Sum, Q
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.forms import modelformset_factory

from .forms import (
    SignUpForm, TeamForm, PlayerForm, MatchForm, MatchScoreForm,
    MatchAppearanceForm, PlayerSelectionForm
)
from .models import Team, Player, Match, MatchAppearance


class SignUpView(CreateView):
    form_class = SignUpForm
    success_url = reverse_lazy('login')
    template_name = 'registration/signup.html'


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'teammanager/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_teams'] = Team.objects.count()
        context['total_players'] = Player.objects.count()
        context['total_matches'] = Match.objects.count()
        context['recent_matches'] = Match.objects.order_by('-date')[:5]
        return context


class PlayerMatrixView(LoginRequiredMixin, TemplateView):
    template_name = 'teammanager/player_matrix.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['teams'] = Team.objects.all()
        return context


# Team Views
class TeamListView(LoginRequiredMixin, ListView):
    model = Team
    context_object_name = 'teams'


class TeamDetailView(LoginRequiredMixin, DetailView):
    model = Team

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['players'] = self.object.players.all()
        context['home_matches'] = self.object.home_matches.order_by('-date')
        context['away_matches'] = self.object.away_matches.order_by('-date')
        return context


class TeamCreateView(LoginRequiredMixin, CreateView):
    model = Team
    form_class = TeamForm
    success_url = reverse_lazy('team-list')


class TeamUpdateView(LoginRequiredMixin, UpdateView):
    model = Team
    form_class = TeamForm
    success_url = reverse_lazy('team-list')


class TeamDeleteView(LoginRequiredMixin, DeleteView):
    model = Team
    success_url = reverse_lazy('team-list')
    

# Player Views
class PlayerListView(LoginRequiredMixin, ListView):
    model = Player
    context_object_name = 'players'


class PlayerDetailView(LoginRequiredMixin, DetailView):
    model = Player

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['appearances'] = self.object.match_appearances.select_related('match').order_by('-match__date')
        return context


class PlayerCreateView(LoginRequiredMixin, CreateView):
    model = Player
    form_class = PlayerForm
    success_url = reverse_lazy('player-list')


class PlayerUpdateView(LoginRequiredMixin, UpdateView):
    model = Player
    form_class = PlayerForm
    success_url = reverse_lazy('player-list')


class PlayerDeleteView(LoginRequiredMixin, DeleteView):
    model = Player
    success_url = reverse_lazy('player-list')


# Match Views
class MatchListView(LoginRequiredMixin, ListView):
    model = Match
    context_object_name = 'matches'
    ordering = ['-date']


class MatchDetailView(LoginRequiredMixin, DetailView):
    model = Match

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['home_appearances'] = self.object.appearances.filter(team=self.object.home_team)
        context['away_appearances'] = self.object.appearances.filter(team=self.object.away_team)
        return context


class MatchCreateView(LoginRequiredMixin, CreateView):
    model = Match
    form_class = MatchForm
    success_url = reverse_lazy('match-list')


class MatchUpdateView(LoginRequiredMixin, UpdateView):
    model = Match
    form_class = MatchForm
    success_url = reverse_lazy('match-list')


class MatchDeleteView(LoginRequiredMixin, DeleteView):
    model = Match
    success_url = reverse_lazy('match-list')


class MatchScoreUpdateView(LoginRequiredMixin, UpdateView):
    model = Match
    form_class = MatchScoreForm
    template_name = 'teammanager/match_score_form.html'
    
    def get_success_url(self):
        return reverse_lazy('match-detail', kwargs={'pk': self.object.pk})


@login_required
def add_players_to_match(request, match_id, team_id):
    match = get_object_or_404(Match, pk=match_id)
    team = get_object_or_404(Team, pk=team_id)
    
    # Verify that the team is either the home or away team
    if match.home_team.id != team.id and match.away_team.id != team.id:
        return redirect('match-detail', pk=match_id)
    
    if request.method == 'POST':
        form = PlayerSelectionForm(match, team, request.POST)
        if form.is_valid():
            # Remove existing appearances for this team in this match
            MatchAppearance.objects.filter(match=match, team=team).delete()
            
            # Create new appearances
            selected_players = form.cleaned_data['players']
            for player in selected_players:
                MatchAppearance.objects.create(
                    player=player,
                    match=match,
                    team=team
                )
            return redirect('match-detail', pk=match_id)
    else:
        # Pre-select players that already appear in this match
        initial_players = Player.objects.filter(
            match_appearances__match=match,
            match_appearances__team=team
        )
        form = PlayerSelectionForm(match, team, initial={'players': initial_players})
    
    return render(request, 'teammanager/add_players_to_match.html', {
        'form': form,
        'match': match,
        'team': team
    })


# API Views for Chart Data
@login_required
def player_stats(request):
    players = Player.objects.annotate(
        matches_played=Count('match_appearances'),
        total_goals=Sum('match_appearances__goals'),
        total_assists=Sum('match_appearances__assists')
    ).values('id', 'first_name', 'last_name', 'matches_played', 'total_goals', 'total_assists')
    
    return JsonResponse(list(players), safe=False)


@login_required
def match_stats(request):
    teams = Team.objects.all()
    stats = []
    
    for team in teams:
        home_matches = team.home_matches.filter(home_score__isnull=False)
        away_matches = team.away_matches.filter(away_score__isnull=False)
        
        wins = home_matches.filter(home_score__gt=models.F('away_score')).count() + \
               away_matches.filter(away_score__gt=models.F('home_score')).count()
        
        draws = home_matches.filter(home_score=models.F('away_score')).count() + \
                away_matches.filter(away_score=models.F('home_score')).count()
        
        losses = home_matches.filter(home_score__lt=models.F('away_score')).count() + \
                 away_matches.filter(away_score__lt=models.F('home_score')).count()
        
        stats.append({
            'team': team.name,
            'wins': wins,
            'draws': draws,
            'losses': losses
        })
    
    return JsonResponse(stats, safe=False)
