from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Sum, Q, F
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView, FormView
from django.forms import modelformset_factory
from django.contrib import messages
import pandas as pd
import datetime

from .forms import (
    SignUpForm, TeamForm, PlayerForm, MatchForm, MatchScoreForm,
    MatchAppearanceForm, PlayerSelectionForm, ExcelUploadForm
)
from .models import Team, Player, Match, MatchAppearance, UserProfile


class SignUpView(CreateView):
    form_class = SignUpForm
    success_url = reverse_lazy('login')
    template_name = 'registration/signup.html'
    
    def form_valid(self, form):
        # Save the user first
        response = super().form_valid(form)
        
        # Get the role and player from the form
        role = form.cleaned_data.get('role')
        player = form.cleaned_data.get('player')
        
        # Update the user's profile
        profile = self.object.profile
        profile.role = role
        profile.player = player
        profile.save()
        
        # Add a success message
        messages.success(
            self.request, 
            'Your account has been created and is pending approval. You will be notified when your account is approved.'
        )
        
        return response


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'teammanager/dashboard.html'

    def dispatch(self, request, *args, **kwargs):
        # Check if user's profile is approved
        if not request.user.profile.is_approved():
            messages.warning(
                request, 
                "Your account is pending approval. Some features may be unavailable until your account is approved."
            )
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Basic data for all roles
        context['total_teams'] = Team.objects.count()
        context['total_players'] = Player.objects.count()
        context['total_matches'] = Match.objects.count()
        context['recent_matches'] = Match.objects.order_by('-date')[:5]
        
        # User role specific data
        context['user_role'] = self.request.user.profile.role
        context['is_pending'] = self.request.user.profile.is_pending()
        
        # For admin users, add pending approval counts
        if self.request.user.profile.is_admin():
            context['pending_approvals'] = UserProfile.objects.filter(status='pending').count()
        
        # For player users, add their own match history
        if self.request.user.profile.is_player() and self.request.user.profile.player:
            context['player_matches'] = MatchAppearance.objects.filter(
                player=self.request.user.profile.player
            ).select_related('match', 'team').order_by('-match__date')[:5]
        
        return context


# Removed LoginRequiredMixin for testing
class PlayerMatrixView(TemplateView):
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
        # Get players who have played for this team in any match
        context['players'] = Player.objects.filter(match_appearances__team=self.object).distinct()
        # Get matches where this team is the Smørås team
        context['matches'] = self.object.matches.order_by('-date')
        return context


class TeamCreateView(LoginRequiredMixin, CreateView):
    model = Team
    form_class = TeamForm
    success_url = reverse_lazy('team-list')
    
    def dispatch(self, request, *args, **kwargs):
        # Check if user's profile is approved and has correct role
        if not request.user.profile.is_approved():
            messages.warning(request, "Your account needs to be approved before you can create teams.")
            return redirect('team-list')
        
        # Only admin and coach can create teams
        if not (request.user.profile.is_admin() or request.user.profile.is_coach()):
            messages.warning(request, "You don't have permission to create teams.")
            return redirect('team-list')
            
        return super().dispatch(request, *args, **kwargs)


class TeamUpdateView(LoginRequiredMixin, UpdateView):
    model = Team
    form_class = TeamForm
    success_url = reverse_lazy('team-list')
    
    def dispatch(self, request, *args, **kwargs):
        # Check if user's profile is approved and has correct role
        if not request.user.profile.is_approved():
            messages.warning(request, "Your account needs to be approved before you can update teams.")
            return redirect('team-list')
        
        # Only admin and coach can update teams
        if not (request.user.profile.is_admin() or request.user.profile.is_coach()):
            messages.warning(request, "You don't have permission to update teams.")
            return redirect('team-list')
            
        return super().dispatch(request, *args, **kwargs)


class TeamDeleteView(LoginRequiredMixin, DeleteView):
    model = Team
    success_url = reverse_lazy('team-list')
    
    def dispatch(self, request, *args, **kwargs):
        # Check if user's profile is approved and has admin role
        if not request.user.profile.is_approved():
            messages.warning(request, "Your account needs to be approved before you can delete teams.")
            return redirect('team-list')
        
        # Only admin can delete teams (more restrictive than create/update)
        if not request.user.profile.is_admin():
            messages.warning(request, "You don't have permission to delete teams.")
            return redirect('team-list')
            
        return super().dispatch(request, *args, **kwargs)
    

# Player Views
class PlayerListView(LoginRequiredMixin, ListView):
    model = Player
    context_object_name = 'players'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['excel_form'] = ExcelUploadForm()
        return context


class ImportPlayersFromExcelView(LoginRequiredMixin, FormView):
    template_name = 'teammanager/import_players_excel.html'
    form_class = ExcelUploadForm
    success_url = reverse_lazy('player-list')
    
    def dispatch(self, request, *args, **kwargs):
        # Check if user's profile is approved and has admin role
        if not request.user.profile.is_approved():
            messages.warning(request, "Your account needs to be approved before you can import players.")
            return redirect('player-list')
        
        # Only admin can import players from Excel
        if not request.user.profile.is_admin():
            messages.warning(request, "You don't have permission to import players from Excel.")
            return redirect('player-list')
            
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        excel_file = self.request.FILES['excel_file']
        
        # Check if file is an Excel file
        if not excel_file.name.endswith('.xlsx'):
            messages.error(self.request, 'Please upload a valid Excel file (.xlsx)')
            return super().form_invalid(form)
        
        try:
            # Read Excel file
            df = pd.read_excel(excel_file)
            
            # Expected columns
            required_columns = ['first_name']
            optional_columns = ['last_name', 'position', 'date_of_birth', 'email', 'phone', 'active']
            
            # Validate required columns
            for col in required_columns:
                if col not in df.columns:
                    messages.error(self.request, f"Required column '{col}' not found in the Excel file.")
                    return super().form_invalid(form)
            
            # Process data and create players
            players_created = 0
            players_updated = 0
            errors = 0
            
            for _, row in df.iterrows():
                if pd.isna(row['first_name']):
                    continue  # Skip rows without a first name
                
                player_data = {
                    'first_name': row['first_name']
                }
                
                # Add optional fields if they exist in the file
                for field in optional_columns:
                    if field in df.columns and not pd.isna(row[field]):
                        # Special handling for dates
                        if field == 'date_of_birth' and not pd.isna(row[field]):
                            if isinstance(row[field], datetime.datetime) or isinstance(row[field], datetime.date):
                                player_data[field] = row[field]
                            else:
                                try:
                                    # Try to parse as a date
                                    player_data[field] = pd.to_datetime(row[field]).date()
                                except:
                                    # If parsing fails, skip this field
                                    continue
                        # Special handling for boolean values
                        elif field == 'active':
                            if isinstance(row[field], bool):
                                player_data[field] = row[field]
                            elif isinstance(row[field], str):
                                player_data[field] = row[field].lower() in ['yes', 'true', 'y', '1']
                            elif isinstance(row[field], (int, float)):
                                player_data[field] = bool(row[field])
                        else:
                            player_data[field] = row[field]
                
                try:
                    # Check if player already exists (by first and last name)
                    if 'last_name' in player_data:
                        existing_player = Player.objects.filter(
                            first_name__iexact=player_data['first_name'],
                            last_name__iexact=player_data['last_name']
                        ).first()
                    else:
                        existing_player = None
                    
                    if existing_player:
                        # Update existing player
                        for key, value in player_data.items():
                            setattr(existing_player, key, value)
                        existing_player.save()
                        players_updated += 1
                    else:
                        # Create new player
                        Player.objects.create(**player_data)
                        players_created += 1
                except Exception as e:
                    errors += 1
                    continue
            
            # Display results
            if players_created > 0:
                messages.success(self.request, f"Successfully created {players_created} new players.")
            if players_updated > 0:
                messages.success(self.request, f"Successfully updated {players_updated} existing players.")
            if errors > 0:
                messages.warning(self.request, f"Encountered {errors} errors while processing the data.")
            
            if players_created == 0 and players_updated == 0:
                messages.warning(self.request, "No players were imported. Please check your Excel file format.")
                return super().form_invalid(form)
                
        except Exception as e:
            messages.error(self.request, f"Error processing Excel file: {str(e)}")
            return super().form_invalid(form)
        
        return super().form_valid(form)


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
    
    def dispatch(self, request, *args, **kwargs):
        # Check if user's profile is approved and has correct role
        if not request.user.profile.is_approved():
            messages.warning(request, "Your account needs to be approved before you can create players.")
            return redirect('player-list')
        
        # Only admin and coach can create players
        if not (request.user.profile.is_admin() or request.user.profile.is_coach()):
            messages.warning(request, "You don't have permission to create players.")
            return redirect('player-list')
            
        return super().dispatch(request, *args, **kwargs)


class PlayerUpdateView(LoginRequiredMixin, UpdateView):
    model = Player
    form_class = PlayerForm
    success_url = reverse_lazy('player-list')
    
    def dispatch(self, request, *args, **kwargs):
        # Check if user's profile is approved and has correct role
        if not request.user.profile.is_approved():
            messages.warning(request, "Your account needs to be approved before you can update players.")
            return redirect('player-list')
        
        # Only admin and coach can update players
        if not (request.user.profile.is_admin() or request.user.profile.is_coach()):
            messages.warning(request, "You don't have permission to update players.")
            return redirect('player-list')
            
        return super().dispatch(request, *args, **kwargs)


class PlayerDeleteView(LoginRequiredMixin, DeleteView):
    model = Player
    success_url = reverse_lazy('player-list')
    
    def dispatch(self, request, *args, **kwargs):
        # Check if user's profile is approved and has admin role
        if not request.user.profile.is_approved():
            messages.warning(request, "Your account needs to be approved before you can delete players.")
            return redirect('player-list')
        
        # Only admin can delete players
        if not request.user.profile.is_admin():
            messages.warning(request, "You don't have permission to delete players.")
            return redirect('player-list')
            
        return super().dispatch(request, *args, **kwargs)


# Match Views
class MatchListView(LoginRequiredMixin, ListView):
    model = Match
    context_object_name = 'matches'
    ordering = ['-date']


class MatchDetailView(LoginRequiredMixin, DetailView):
    model = Match

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get appearances for the Smørås team
        context['home_appearances'] = self.object.appearances.filter(team=self.object.smoras_team)
        # Get appearances for any other teams (external players)
        context['away_appearances'] = self.object.appearances.exclude(team=self.object.smoras_team)
        context['is_home_match'] = self.object.location_type == 'Home'
        return context


class MatchCreateView(LoginRequiredMixin, CreateView):
    model = Match
    form_class = MatchForm
    success_url = reverse_lazy('match-list')
    
    def dispatch(self, request, *args, **kwargs):
        # Check if user's profile is approved and has correct role
        if not request.user.profile.is_approved():
            messages.warning(request, "Your account needs to be approved before you can create matches.")
            return redirect('match-list')
        
        # Only admin and coach can create matches
        if not (request.user.profile.is_admin() or request.user.profile.is_coach()):
            messages.warning(request, "You don't have permission to create matches.")
            return redirect('match-list')
            
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        """Process the form data when valid."""
        # No need to process template data here since the JavaScript 
        # in the template handles it on the client side
        if form.cleaned_data.get('use_template') and form.cleaned_data.get('template_match'):
            # Log that a template was used
            template_match = form.cleaned_data['template_match']
            messages.info(self.request, 
                f"Created new match using template: {template_match.smoras_team.name} vs {template_match.opponent_name}")
        return super().form_valid(form)


class MatchUpdateView(LoginRequiredMixin, UpdateView):
    model = Match
    form_class = MatchForm
    success_url = reverse_lazy('match-list')
    
    def dispatch(self, request, *args, **kwargs):
        # Check if user's profile is approved and has correct role
        if not request.user.profile.is_approved():
            messages.warning(request, "Your account needs to be approved before you can update matches.")
            return redirect('match-list')
        
        # Only admin and coach can update matches
        if not (request.user.profile.is_admin() or request.user.profile.is_coach()):
            messages.warning(request, "You don't have permission to update matches.")
            return redirect('match-list')
            
        return super().dispatch(request, *args, **kwargs)


class MatchDeleteView(LoginRequiredMixin, DeleteView):
    model = Match
    success_url = reverse_lazy('match-list')
    
    def dispatch(self, request, *args, **kwargs):
        # Check if user's profile is approved and has admin role
        if not request.user.profile.is_approved():
            messages.warning(request, "Your account needs to be approved before you can delete matches.")
            return redirect('match-list')
        
        # Only admin can delete matches
        if not request.user.profile.is_admin():
            messages.warning(request, "You don't have permission to delete matches.")
            return redirect('match-list')
            
        return super().dispatch(request, *args, **kwargs)


class MatchScoreUpdateView(LoginRequiredMixin, UpdateView):
    model = Match
    form_class = MatchScoreForm
    template_name = 'teammanager/match_score_form.html'
    
    def dispatch(self, request, *args, **kwargs):
        # Check if user's profile is approved and has correct role
        if not request.user.profile.is_approved():
            messages.warning(request, "Your account needs to be approved before you can update match scores.")
            return redirect('match-list')
        
        # Both coach and admin can update match scores
        if not (request.user.profile.is_admin() or request.user.profile.is_coach()):
            messages.warning(request, "You don't have permission to update match scores.")
            return redirect('match-list')
            
        return super().dispatch(request, *args, **kwargs)
    
    def get_success_url(self):
        return reverse_lazy('match-detail', kwargs={'pk': self.object.pk})


@login_required
def add_players_to_match(request, match_id, team_id):
    # Check if user's profile is approved and has correct role
    if not request.user.profile.is_approved():
        messages.warning(request, "Your account needs to be approved before you can add players to matches.")
        return redirect('match-list')
    
    # Only admin and coach can add players to matches
    if not (request.user.profile.is_admin() or request.user.profile.is_coach()):
        messages.warning(request, "You don't have permission to add players to matches.")
        return redirect('match-list')
    
    match = get_object_or_404(Match, pk=match_id)
    team = get_object_or_404(Team, pk=team_id)
    
    # Verify that the team is the Smørås team
    if match.smoras_team.id != team.id:
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
    
    context = {
        'form': form,
        'match': match,
        'team': team,
        'opponent_name': match.opponent_name
    }
    
    return render(request, 'teammanager/add_players_to_match.html', context)


@login_required
def edit_appearance_stats(request, appearance_id):
    # Check if user's profile is approved and has correct role
    if not request.user.profile.is_approved():
        messages.warning(request, "Your account needs to be approved before you can update player statistics.")
        return redirect('match-list')
    
    # Only admin and coach can edit player statistics
    if not (request.user.profile.is_admin() or request.user.profile.is_coach()):
        messages.warning(request, "You don't have permission to update player statistics.")
        return redirect('match-list')
        
    appearance = get_object_or_404(MatchAppearance, pk=appearance_id)
    match = appearance.match
    
    if request.method == 'POST':
        form = MatchAppearanceForm(request.POST, instance=appearance)
        if form.is_valid():
            form.save()
            messages.success(request, f"Statistics updated for {appearance.player.first_name}")
            return redirect('match-detail', pk=match.id)
    else:
        form = MatchAppearanceForm(instance=appearance)
    
    context = {
        'form': form,
        'appearance': appearance,
        'match': match,
        'player': appearance.player
    }
    
    return render(request, 'teammanager/edit_appearance_stats.html', context)


# API Views for Chart Data
@login_required
def player_stats(request):
    # Get all players with their match counts
    players = Player.objects.annotate(
        matches_played=Count('match_appearances'),
        total_goals=Sum('match_appearances__goals'),
        total_assists=Sum('match_appearances__assists')
    ).values('id', 'first_name', 'last_name', 'matches_played', 'total_goals', 'total_assists')
    
    # Create a list to store the enriched player data with team information
    enriched_players = []
    
    for player in players:
        # For each player, get the teams they've played for and the number of matches with each team
        player_teams = MatchAppearance.objects.filter(player_id=player['id']) \
            .values('team__name') \
            .annotate(team_matches=Count('match')) \
            .order_by('-team_matches')
        
        # Add team data to the player record
        player_with_teams = player.copy()
        player_with_teams['teams'] = list(player_teams)
        enriched_players.append(player_with_teams)
    
    return JsonResponse(enriched_players, safe=False)


@login_required
def match_stats(request):
    teams = Team.objects.all()
    stats = []
    
    for team in teams:
        # Get all matches where this team is the Smørås team
        team_matches = team.matches.filter(smoras_score__isnull=False, opponent_score__isnull=False)
        
        # Calculate wins, draws, and losses based on scores
        wins = team_matches.filter(smoras_score__gt=F('opponent_score')).count()
        draws = team_matches.filter(smoras_score=F('opponent_score')).count()
        losses = team_matches.filter(smoras_score__lt=F('opponent_score')).count()
        
        stats.append({
            'team': team.name,
            'wins': wins,
            'draws': draws,
            'losses': losses
        })
    
    return JsonResponse(stats, safe=False)


# Removed login_required for testing purposes
def player_matrix(request):
    """
    API endpoint that returns player matrix data for all players
    showing how often players have played together in matches.
    """
    try:
        # Get all active players
        players = Player.objects.filter(active=True)
        players_data = list(players.values('id', 'first_name', 'last_name'))
        
        # If no players, return empty response
        if not players_data:
            return JsonResponse({
                'players': [],
                'matrix': [],
                'max_value': 0,
                'error': 'No active players found'
            })
        
        # Initialize matrix with zeros
        player_count = len(players)
        matrix = [[0 for _ in range(player_count)] for _ in range(player_count)]
        
        # Map player IDs to matrix indices
        player_indices = {player['id']: idx for idx, player in enumerate(players_data)}
        
        # Populate matrix: For each match, find all pairs of players who played together
        matches = Match.objects.all()
        max_value = 0
        
        for match in matches:
            # Get players who played in this match
            match_player_ids = list(match.players.values_list('id', flat=True))
            
            # For each pair of players in this match, increment their count
            for i, player_id1 in enumerate(match_player_ids):
                if player_id1 in player_indices:
                    idx1 = player_indices[player_id1]
                    
                    # Diagonal counts (player with themselves) - total matches for this player
                    matrix[idx1][idx1] += 1
                    if matrix[idx1][idx1] > max_value:
                        max_value = matrix[idx1][idx1]
                    
                    # Count pairs of players who played together
                    for player_id2 in match_player_ids[i+1:]:
                        if player_id2 in player_indices:
                            idx2 = player_indices[player_id2]
                            
                            # Increment both positions (the matrix is symmetric)
                            matrix[idx1][idx2] += 1
                            matrix[idx2][idx1] += 1
                            
                            # Update max value for color scaling
                            if matrix[idx1][idx2] > max_value:
                                max_value = matrix[idx1][idx2]
        
        # Prepare response
        response_data = {
            'players': players_data,
            'matrix': matrix,
            'max_value': max_value
        }
        
        return JsonResponse(response_data)
    
    except Exception as e:
        # Return error information for debugging
        import traceback
        return JsonResponse({
            'error': str(e),
            'traceback': traceback.format_exc(),
            'players': [],
            'matrix': [],
            'max_value': 0
        })
