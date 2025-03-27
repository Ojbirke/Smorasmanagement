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

    def form_invalid(self, form):
        """If the form is invalid, render the invalid form with detailed error messages."""
        for field in form.errors:
            for error in form.errors[field]:
                messages.error(self.request, f"Error in field '{field}': {error}")

        return super().form_invalid(form)

    def form_valid(self, form):
        try:
            # Save the user first - we need to explicitly handle the first_name requirement
            user = form.save(commit=False)
            # Make sure first_name is not empty (now required by Django)
            if not user.first_name:
                user.first_name = user.username
            user.save()

            # Get the role and player from the form
            role = form.cleaned_data.get('role')
            player = form.cleaned_data.get('player')

            # Update the user's profile
            profile = user.profile
            profile.role = role
            profile.player = player
            profile.save()

            # Add a success message
            messages.success(
                self.request, 
                'Your account has been created and is pending approval. You will be notified when your account is approved.'
            )

            # Complete the form actions
            form.save_m2m()  # Save many-to-many relationships
            self.object = user  # Set the object attribute for CreateView

            return redirect(self.get_success_url())
        except Exception as e:
            # Log any error that occurs
            messages.error(self.request, f"An error occurred: {str(e)}")
            return self.form_invalid(form)


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

        # Add user role information for the template
        context['is_admin'] = self.request.user.profile.is_admin()
        context['is_coach'] = self.request.user.profile.is_coach()
        context['is_player'] = self.request.user.profile.is_player()
        context['is_approved'] = self.request.user.profile.is_approved()
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add user role information for the template
        context['is_admin'] = self.request.user.profile.is_admin()
        context['is_coach'] = self.request.user.profile.is_coach()
        context['is_player'] = self.request.user.profile.is_player()
        context['is_approved'] = self.request.user.profile.is_approved()
        context['can_create'] = context['is_approved'] and (context['is_admin'] or context['is_coach'])
        return context


class TeamDetailView(LoginRequiredMixin, DetailView):
    model = Team

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get players who have played for this team in any match
        context['players'] = Player.objects.filter(match_appearances__team=self.object).distinct()
        # Get matches where this team is the Smørås team
        context['matches'] = self.object.matches.order_by('-date')

        # Add user role information for the template
        context['is_admin'] = self.request.user.profile.is_admin()
        context['is_coach'] = self.request.user.profile.is_coach()
        context['is_player'] = self.request.user.profile.is_player()
        context['is_approved'] = self.request.user.profile.is_approved()
        context['can_edit'] = context['is_approved'] and (context['is_admin'] or context['is_coach'])
        context['can_delete'] = context['is_approved'] and context['is_admin']
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
        # Add Excel form for admin users
        context['excel_form'] = ExcelUploadForm()

        # Add user role information for the template
        context['is_admin'] = self.request.user.profile.is_admin()
        context['is_coach'] = self.request.user.profile.is_coach()
        context['is_player'] = self.request.user.profile.is_player()
        context['is_approved'] = self.request.user.profile.is_approved()
        context['can_create'] = context['is_approved'] and (context['is_admin'] or context['is_coach'])
        context['can_import'] = context['is_approved'] and context['is_admin']
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

        # Add user role information for the template
        context['is_admin'] = self.request.user.profile.is_admin()
        context['is_coach'] = self.request.user.profile.is_coach()
        context['is_player'] = self.request.user.profile.is_player()
        context['is_approved'] = self.request.user.profile.is_approved()
        context['can_edit'] = context['is_approved'] and (context['is_admin'] or context['is_coach'])
        context['can_delete'] = context['is_approved'] and context['is_admin']
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add user role information for the template
        context['is_admin'] = self.request.user.profile.is_admin()
        context['is_coach'] = self.request.user.profile.is_coach()
        context['is_player'] = self.request.user.profile.is_player()
        context['is_approved'] = self.request.user.profile.is_approved()
        context['can_create'] = context['is_approved'] and (context['is_admin'] or context['is_coach'])
        return context


class MatchDetailView(LoginRequiredMixin, DetailView):
    model = Match

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get appearances for the Smørås team
        context['home_appearances'] = self.object.appearances.filter(team=self.object.smoras_team)
        # Get appearances for any other teams (external players)
        context['away_appearances'] = self.object.appearances.exclude(team=self.object.smoras_team)
        context['is_home_match'] = self.object.location_type == 'Home'

        # Add user role information for the template
        context['is_admin'] = self.request.user.profile.is_admin()
        context['is_coach'] = self.request.user.profile.is_coach()
        context['is_player'] = self.request.user.profile.is_player()
        context['is_approved'] = self.request.user.profile.is_approved()
        context['can_edit'] = context['is_approved'] and (context['is_admin'] or context['is_coach'])
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


@login_required
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


from django.contrib.auth import logout as auth_logout
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib.auth.models import User

@login_required
def custom_logout(request):
    """
    Custom logout view to properly handle logout process
    and redirect to home page.
    """
    auth_logout(request)
    messages.success(request, "You have been successfully logged out.")
    return HttpResponseRedirect(reverse('home'))


# User Management Views
class UserListView(LoginRequiredMixin, ListView):
    template_name = 'teammanager/user_list.html'
    context_object_name = 'users'

    def get_queryset(self):
        # Only show users if the current user is an admin
        if self.request.user.profile.is_admin():
            return User.objects.all().select_related('profile').order_by('-profile__created_at')
        return User.objects.none()

    def dispatch(self, request, *args, **kwargs):
        # Check if user's profile is approved and has admin role
        if not request.user.profile.is_admin():
            messages.warning(request, "You don't have permission to manage users.")
            return redirect('dashboard')

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['pending_users'] = User.objects.filter(profile__status='pending').select_related('profile')
        context['is_admin'] = self.request.user.profile.is_admin()
        context['is_coach'] = self.request.user.profile.is_coach()
        context['is_player'] = self.request.user.profile.is_player()
        context['is_approved'] = self.request.user.profile.is_approved()
        return context


@login_required
def approve_user(request, pk):
    # Only admin users can approve other users
    if not request.user.profile.is_admin():
        messages.error(request, "You don't have permission to approve users.")
        return redirect('dashboard')

    try:
        user_to_approve = User.objects.get(pk=pk)
        user_to_approve.profile.status = 'approved'
        user_to_approve.profile.save()
        messages.success(request, f"User '{user_to_approve.username}' has been approved.")
    except User.DoesNotExist:
        messages.error(request, "User not found.")

    return redirect('user-list')


@login_required
def reject_user(request, pk):
    # Only admin users can reject other users
    if not request.user.profile.is_admin():
        messages.error(request, "You don't have permission to reject users.")
        return redirect('dashboard')

    try:
        user_to_reject = User.objects.get(pk=pk)
        user_to_reject.profile.status = 'rejected'
        user_to_reject.profile.save()
        messages.success(request, f"User '{user_to_reject.username}' has been rejected.")
    except User.DoesNotExist:
        messages.error(request, "User not found.")

    return redirect('user-list')


@login_required
def delete_user(request, pk):
    # Only admin users can delete other users
    if not request.user.profile.is_admin():
        messages.error(request, "You don't have permission to delete users.")
        return redirect('dashboard')

    # Prevent self-deletion
    if request.user.pk == pk:
        messages.error(request, "You cannot delete your own account.")
        return redirect('user-list')

    try:
        user_to_delete = User.objects.get(pk=pk)
        username = user_to_delete.username

        # Delete user profile and user
        user_to_delete.delete()

        messages.success(request, f"User '{username}' has been permanently deleted.")
    except User.DoesNotExist:
        messages.error(request, "User not found.")

    return redirect('user-list')