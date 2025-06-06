from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.views.generic.edit import FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.db.models import Sum, Count, Q
from django.core.exceptions import PermissionDenied
from django.views.decorators.csrf import csrf_exempt
import json
import math
import random
from datetime import timedelta

from .models import (
    Match, Player, Team, MatchAppearance,
    MatchSession, PlayerSubstitution, PlayingTime
)
from .forms import (
    MatchSessionForm, PlayerSelectionSessionForm, SubstitutionForm
)
from .views_lineup import is_coach_or_admin


def is_approved_user(user):
    """Check if user is an approved user (any role)"""
    return user.is_authenticated and hasattr(user, 'profile') and user.profile.is_approved()


@login_required
def match_session_list(request):
    """List all match sessions"""
    if not is_approved_user(request.user):
        messages.error(request, "You need to be an approved user to view match sessions.")
        return redirect('dashboard')
    
    # Get upcoming match sessions (those created in the last 2 weeks or with matches in the future)
    two_weeks_ago = timezone.now() - timedelta(days=14)
    upcoming_sessions = MatchSession.objects.filter(
        Q(match__date__gte=timezone.now()) | Q(created_at__gte=two_weeks_ago)
    ).order_by('-match__date')
    
    # Get past match sessions
    past_sessions = MatchSession.objects.filter(
        match__date__lt=timezone.now(),
        created_at__lt=two_weeks_ago
    ).order_by('-match__date')
    
    context = {
        'upcoming_sessions': upcoming_sessions,
        'past_sessions': past_sessions,
        'can_create': is_coach_or_admin(request.user),
    }
    return render(request, 'teammanager/match_session_list.html', context)


@login_required
def match_session_detail(request, pk):
    """View a match session's details"""
    match_session = get_object_or_404(MatchSession, pk=pk)
    
    # Get all players for this session
    playing_times = PlayingTime.objects.filter(match_session=match_session)
    
    # Get all substitutions for this session
    substitutions = PlayerSubstitution.objects.filter(match_session=match_session).order_by('minute')
    
    # Calculate current game time if session is active
    current_game_time = None
    next_sub_time = None
    
    if match_session.is_active and match_session.start_time:
        elapsed = timezone.now() - match_session.start_time
        current_game_time = math.floor(elapsed.total_seconds() / 60)
        
        # No random substitutions as requested by user
        next_sub_time = None  # Disable substitution timer
    
    context = {
        'match_session': match_session,
        'playing_times': playing_times,
        'substitutions': substitutions,
        'players_on_pitch': playing_times.filter(is_on_pitch=True),
        'players_on_bench': playing_times.filter(is_on_pitch=False),
        'current_game_time': current_game_time,
        'next_sub_time': next_sub_time,
        'can_edit': is_coach_or_admin(request.user),
    }
    return render(request, 'teammanager/match_session_detail.html', context)


class MatchSessionCreateView(LoginRequiredMixin, CreateView):
    """Create a new match session"""
    model = MatchSession
    form_class = MatchSessionForm
    template_name = 'teammanager/match_session_form.html'
    success_url = reverse_lazy('match-session-list')
    
    def dispatch(self, request, *args, **kwargs):
        if not is_coach_or_admin(request.user):
            messages.error(request, "You need to be a coach or admin to create match sessions.")
            return redirect('match-session-list')
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        
        # Check if match has appearances we could auto-import
        match = form.instance.match
        appearances = match.appearances.all()
        
        if appearances.exists():
            # Check for lineup associated with this match
            lineup = match.lineups.filter(is_template=False).order_by('-created_at').first()
            
            if lineup and lineup.player_positions.exists():
                # If a lineup exists for this match, use player positions from it
                starters = []
                bench = []
                
                # Get all players from the lineup with their starter status
                for position in lineup.player_positions.all():
                    if position.is_starter:
                        starters.append(position.player)
                    else:
                        bench.append(position.player)
                
                # Get additional players from match appearances that might not be in lineup
                lineup_player_ids = lineup.player_positions.values_list('player_id', flat=True)
                additional_players = Player.objects.filter(
                    match_appearances__match=match
                ).exclude(id__in=lineup_player_ids).distinct()
                
                # Add additional players to bench
                bench.extend(additional_players)
                
                print(f"Auto-imported players from match lineup: {len(starters)} as starters, {len(bench)} on bench.")
            else:
                # Fallback to getting players from match appearances if no lineup exists
                players_from_match = Player.objects.filter(
                    match_appearances__match=match
                ).distinct()
                
                # Always use 7 players as starters (7-a-side format) as requested
                all_players = list(players_from_match)
                random.shuffle(all_players)  # Randomize the player order for random selection
                
                # If we have more than 7 players, use exactly 7 as starters
                if len(all_players) >= 7:
                    starters = all_players[:7]  # First 7 players after shuffle
                    bench = all_players[7:]     # Remaining players to bench
                else:
                    # If we have fewer than 7 players, use all available as starters
                    starters = all_players
                    bench = []
                    
                print(f"Auto-imported {len(all_players)} players from match appearances: {len(starters)} as starters, {len(bench)} on bench.")
            
            # Create playing time records
            for player in starters:
                PlayingTime.objects.update_or_create(
                    match_session=self.object,
                    player=player,
                    defaults={
                        'is_on_pitch': True,
                        'minutes_played': 0,
                        'last_substitution_time': timezone.now() if self.object.is_active else None
                    }
                )
            
            for player in bench:
                PlayingTime.objects.update_or_create(
                    match_session=self.object,
                    player=player,
                    defaults={
                        'is_on_pitch': False,
                        'minutes_played': 0,
                        'last_substitution_time': None
                    }
                )
            
            total_players = len(starters) + len(bench)
            messages.success(
                self.request, 
                f"Match session created and players auto-imported from match! "
                f"{total_players} players imported with {len(starters)} as starters."
            )
            return redirect('match-session-detail', pk=self.object.pk)
        else:
            # No appearances found, redirect to manual player selection
            messages.success(self.request, "Match session created successfully. Now select players for this session.")
            return redirect('match-session-players', pk=self.object.pk)


class MatchSessionUpdateView(LoginRequiredMixin, UpdateView):
    """Update an existing match session"""
    model = MatchSession
    form_class = MatchSessionForm
    template_name = 'teammanager/match_session_form.html'
    
    def dispatch(self, request, *args, **kwargs):
        if not is_coach_or_admin(request.user):
            messages.error(request, "You need to be a coach or admin to update match sessions.")
            return redirect('match-session-list')
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_success_url(self):
        return reverse('match-session-detail', args=[self.object.pk])


class MatchSessionDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a match session"""
    model = MatchSession
    template_name = 'teammanager/match_session_confirm_delete.html'
    success_url = reverse_lazy('match-session-list')
    
    def dispatch(self, request, *args, **kwargs):
        if not is_coach_or_admin(request.user):
            messages.error(request, "You need to be a coach or admin to delete match sessions.")
            return redirect('match-session-list')
        return super().dispatch(request, *args, **kwargs)


@login_required
def match_session_players(request, pk):
    """Select players for a match session"""
    match_session = get_object_or_404(MatchSession, pk=pk)
    
    if not is_coach_or_admin(request.user):
        messages.error(request, "You need to be a coach or admin to select players for a match session.")
        return redirect('match-session-detail', pk=match_session.pk)
    
    # Check if this match has appearances we could import
    appearances = match_session.match.appearances.all()
    has_appearances = appearances.exists()
    
    # Process form submission
    if request.method == 'POST':
        form = PlayerSelectionSessionForm(match_session, request.POST)
        
        if 'import_from_match' in request.POST and has_appearances:
            # Check for lineup associated with this match
            lineup = match_session.match.lineups.filter(is_template=False).order_by('-created_at').first()
            
            if lineup and lineup.player_positions.exists():
                # If a lineup exists for this match, use player positions from it
                starters = []
                bench = []
                
                # Get all players from the lineup with their starter status
                for position in lineup.player_positions.all():
                    if position.is_starter:
                        starters.append(position.player)
                    else:
                        bench.append(position.player)
                
                # Get additional players from match appearances that might not be in lineup
                lineup_player_ids = lineup.player_positions.values_list('player_id', flat=True)
                additional_players = Player.objects.filter(
                    match_appearances__match=match_session.match
                ).exclude(id__in=lineup_player_ids).distinct()
                
                # Add additional players to bench
                bench.extend(additional_players)
                
                # Combine for the all_players list that's used later
                all_players = starters + bench
                
                print(f"AJAX: Auto-imported players from match lineup: {len(starters)} as starters, {len(bench)} on bench.")
            else:
                # Import players from match appearances
                players_from_match = Player.objects.filter(
                    match_appearances__match=match_session.match
                ).distinct()
                
                # Always use 7 players as starters (7-a-side format) as requested
                # We're already getting the correct players from match appearances
                all_players = list(players_from_match)
                random.shuffle(all_players)  # Randomize the player order for random selection
                
                # If we have more than 7 players, use exactly 7 as starters
                if len(all_players) >= 7:
                    starters = all_players[:7]  # First 7 players after shuffle
                    bench = all_players[7:]     # Remaining players to bench
                else:
                    # If we have fewer than 7 players, use all available as starters
                    starters = all_players
                    bench = []
                    
                print(f"AJAX: Auto-imported {len(all_players)} players from match appearances: {len(starters)} as starters, {len(bench)} on bench.")
            
            # Create playing time records
            for player in starters:
                PlayingTime.objects.update_or_create(
                    match_session=match_session,
                    player=player,
                    defaults={
                        'is_on_pitch': True,
                        'minutes_played': 0,
                        'last_substitution_time': timezone.now() if match_session.is_active else None
                    }
                )
            
            for player in bench:
                PlayingTime.objects.update_or_create(
                    match_session=match_session,
                    player=player,
                    defaults={
                        'is_on_pitch': False,
                        'minutes_played': 0,
                        'last_substitution_time': None
                    }
                )
            
            total_players = len(starters) + len(bench)
            messages.success(request, f"Imported {total_players} players from match. {len(starters)} players are starting.")
            return redirect('match-session-detail', pk=match_session.pk)
            
        elif form.is_valid():
            # Get selected players
            selected_players = form.cleaned_data.get('players', [])
            starting_players = form.cleaned_data.get('starting_players', [])
            
            # Create playing time records
            for player in selected_players:
                is_starter = player in starting_players
                PlayingTime.objects.update_or_create(
                    match_session=match_session,
                    player=player,
                    defaults={
                        'is_on_pitch': is_starter,
                        'minutes_played': 0,
                        'last_substitution_time': timezone.now() if is_starter and match_session.is_active else None
                    }
                )
            
            # Delete any player records that are no longer selected
            PlayingTime.objects.filter(
                match_session=match_session
            ).exclude(
                player__in=selected_players
            ).delete()
            
            messages.success(request, f"Player selection saved. {len(starting_players)} players are starting.")
            return redirect('match-session-detail', pk=match_session.pk)
    else:
        # Check if we already have players for this session
        existing_players = PlayingTime.objects.filter(match_session=match_session)
        
        if existing_players.exists():
            # Pre-select existing players
            initial = {
                'players': [pt.player for pt in existing_players],
                'starting_players': [pt.player for pt in existing_players.filter(is_on_pitch=True)]
            }
            form = PlayerSelectionSessionForm(match_session, initial=initial)
        else:
            form = PlayerSelectionSessionForm(match_session)
    
    context = {
        'form': form,
        'match_session': match_session,
        'has_appearances': has_appearances,
    }
    return render(request, 'teammanager/match_session_players.html', context)


@login_required
def match_session_start(request, pk):
    """Start a match session"""
    match_session = get_object_or_404(MatchSession, pk=pk)
    
    # Check if this request came from the pitch view (mobile view)
    from_pitch_view = request.META.get('HTTP_REFERER', '').endswith(f'/match-sessions/{pk}/pitch/')
    
    if not is_coach_or_admin(request.user):
        messages.error(request, "You need to be a coach or admin to start match sessions.")
        if from_pitch_view:
            return redirect('match-session-pitch', pk=match_session.pk)
        return redirect('match-session-detail', pk=match_session.pk)
    
    # Ensure we have enough players to start
    playing_times = PlayingTime.objects.filter(match_session=match_session)
    players_on_pitch = playing_times.filter(is_on_pitch=True).count()
    players_on_bench = playing_times.filter(is_on_pitch=False).count()
    
    if players_on_pitch < 5:  # Minimum for a viable match (adjust as needed)
        messages.error(request, "You need at least 5 players on the pitch to start a match.")
        if from_pitch_view:
            return redirect('match-session-pitch', pk=match_session.pk)
        return redirect('match-session-detail', pk=match_session.pk)
    
    # Starting a previously stopped match - check if we're starting a new period
    if not match_session.is_active and match_session.elapsed_time > 0:
        # If we've already played some time and are now starting again,
        # see if we should move to the next period
        seconds_per_period = match_session.period_length * 60
        total_seconds_possible = seconds_per_period * match_session.periods
        
        # If we've completed all the time for the current period, move to the next one
        if (match_session.elapsed_time % seconds_per_period == 0 and 
            match_session.elapsed_time < total_seconds_possible and
            match_session.current_period < match_session.periods):
            match_session.current_period += 1
            message = f"Starting period {match_session.current_period} of {match_session.periods}."
            messages.info(request, message)
    
    # Start the match
    now = timezone.now()
    match_session.is_active = True
    
    # Set the new start time, regardless of previous elapsed time
    # The elapsed_time field keeps track of accumulated time, but start_time 
    # should always reflect when the current session started
    match_session.start_time = now
    
    # We don't need to adjust start_time because:
    # 1. elapsed_time tracks the total time across all starts/stops
    # 2. When stopped, we add the current session time to elapsed_time
    # 3. On the client side, the JS clock adds elapsed_time to its calculations
    
    # Always reset the substitution timer when starting a match
    match_session.last_substitution = now
    match_session.save()
    
    # Update all players in this match
    playing_times = PlayingTime.objects.filter(match_session=match_session)
    
    # First, update players on pitch
    for pt in playing_times.filter(is_on_pitch=True):
        # Reset their substitution time to now
        pt.last_substitution_time = now
        # Also update the current_start_time - this is needed for proper timing calculations
        if hasattr(pt, 'current_start_time'):
            pt.current_start_time = now
        pt.save()
    
    # Also ensure players on bench have proper timing data reset
    for pt in playing_times.filter(is_on_pitch=False):
        # Bench players should have no active timing data
        pt.last_substitution_time = None
        if hasattr(pt, 'current_start_time'):
            pt.current_start_time = None
        pt.save()
    
    # Show message about players, but don't enable random substitutions
    if players_on_bench > 0:
        messages.success(request, f"Match session started. {players_on_pitch} players on field, {players_on_bench} on bench.")
    else:
        messages.success(request, "Match session started. Substitution tracking is now active.")
    
    # Redirect back to the pitch view if that's where the request came from
    if from_pitch_view:
        return redirect('match-session-pitch', pk=match_session.pk)
    return redirect('match-session-detail', pk=match_session.pk)


@login_required
def match_session_stop(request, pk):
    """Stop a match session"""
    match_session = get_object_or_404(MatchSession, pk=pk)
    
    # Check if this request came from the pitch view (mobile view)
    from_pitch_view = request.META.get('HTTP_REFERER', '').endswith(f'/match-sessions/{pk}/pitch/')
    
    if not is_coach_or_admin(request.user):
        messages.error(request, "You need to be a coach or admin to stop match sessions.")
        if from_pitch_view:
            return redirect('match-session-pitch', pk=match_session.pk)
        return redirect('match-session-detail', pk=match_session.pk)
    
    if match_session.is_active:
        # Update playing time for all active players
        now = timezone.now()
        
        # First update all players currently on the pitch
        for playing_time in PlayingTime.objects.filter(match_session=match_session, is_on_pitch=True):
            if playing_time.last_substitution_time:
                elapsed = now - playing_time.last_substitution_time
                playing_time.minutes_played += math.floor(elapsed.total_seconds() / 60)
                playing_time.last_substitution_time = None
                # Reset current_start_time to ensure it doesn't carry over
                if hasattr(playing_time, 'current_start_time'):
                    playing_time.current_start_time = None
                playing_time.save()
        
        # Now update the MatchAppearance records with the final playing times
        match = match_session.match
        team = match.smoras_team
        
        # Get all players who participated in this match session
        for playing_time in PlayingTime.objects.filter(match_session=match_session):
            # Get or create a match appearance record
            appearance, created = MatchAppearance.objects.get_or_create(
                player=playing_time.player,
                match=match,
                team=team,
                defaults={
                    'minutes_played': playing_time.minutes_played,
                    'goals': 0,
                    'assists': 0
                }
            )
            
            # If the record already existed, update the minutes
            if not created:
                appearance.minutes_played = playing_time.minutes_played
                appearance.save()
        
        # Update the elapsed time in the match session
        if match_session.start_time:
            elapsed_seconds = int((now - match_session.start_time).total_seconds())
            match_session.elapsed_time += elapsed_seconds
            
            # Check if we've completed a period
            seconds_per_period = match_session.period_length * 60
            periods_completed = match_session.elapsed_time // seconds_per_period
            
            if periods_completed >= match_session.periods:
                # Match has ended completely
                message = "Match complete! All periods have been played."
                messages.success(request, message)
            else:
                # Period completed but match continues
                current_period = min(periods_completed + 1, match_session.periods)
                match_session.current_period = current_period
                
                if periods_completed > 0 and periods_completed < match_session.periods:
                    next_period = periods_completed + 1
                    message = f"Period {periods_completed} complete. Ready to start period {next_period}."
                    messages.info(request, message)
        
        # Stop the match, but keep the start_time 
        # This way we can restart with proper timing if needed
        match_session.is_active = False
        # Keep the start_time, we'll reset it when restarting
        # (old code set it to None which caused problems when restarting)
        match_session.save()
        
        messages.success(request, "Match session stopped. Playing time has been recorded and saved to match statistics.")
    else:
        messages.warning(request, "This match session is not currently active.")
    
    # Redirect back to the pitch view if that's where the request came from
    if from_pitch_view:
        return redirect('match-session-pitch', pk=match_session.pk)
    return redirect('match-session-detail', pk=match_session.pk)


@login_required
def substitution_create(request, pk):
    """Create a substitution in a match session"""
    match_session = get_object_or_404(MatchSession, pk=pk)
    
    if not is_coach_or_admin(request.user):
        messages.error(request, "You need to be a coach or admin to make substitutions.")
        return redirect('match-session-detail', pk=match_session.pk)
    
    if not match_session.is_active:
        messages.error(request, "You can only make substitutions in an active match.")
        return redirect('match-session-detail', pk=match_session.pk)
    
    if request.method == 'POST':
        form = SubstitutionForm(request.POST, match_session=match_session)
        
        if form.is_valid():
            player_in = form.cleaned_data['player_in']
            player_out = form.cleaned_data['player_out']
            minute = form.cleaned_data['minute']
            period = form.cleaned_data['period']
            
            now = timezone.now()
            
            # Create the substitution record
            substitution = form.save(commit=False)
            substitution.match_session = match_session
            substitution.timestamp = now
            substitution.save()
            
            # Update playing time for player coming off
            player_out_record = PlayingTime.objects.get(match_session=match_session, player=player_out)
            if player_out_record.last_substitution_time:
                elapsed = now - player_out_record.last_substitution_time
                player_out_record.minutes_played += math.floor(elapsed.total_seconds() / 60)
            player_out_record.is_on_pitch = False
            player_out_record.last_substitution_time = None
            player_out_record.save()
            
            # Update playing time for player coming on
            player_in_record = PlayingTime.objects.get(match_session=match_session, player=player_in)
            player_in_record.is_on_pitch = True
            player_in_record.last_substitution_time = now
            player_in_record.save()
            
            messages.success(request, f"Substitution recorded: {player_in} replaces {player_out}")
            return redirect('match-session-detail', pk=match_session.pk)
    else:
        # Calculate current game time
        elapsed = timezone.now() - match_session.start_time
        current_minute = math.floor(elapsed.total_seconds() / 60)
        
        # Calculate current period
        period = 1
        if match_session.periods > 1:
            period_minutes = match_session.period_length
            period = (current_minute // period_minutes) + 1
            # Ensure period doesn't exceed the configured number of periods
            period = min(period, match_session.periods)
        
        initial = {
            'minute': current_minute,
            'period': period
        }
        form = SubstitutionForm(initial=initial, match_session=match_session)
    
    context = {
        'form': form,
        'match_session': match_session,
        'title': "Record Substitution"
    }
    return render(request, 'teammanager/substitution_form.html', context)


@csrf_exempt
@login_required
def ajax_quick_sub(request, session_pk):
    """Quick substitution via AJAX"""
    if not request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'error': 'Invalid request'}, status=400)
    
    match_session = get_object_or_404(MatchSession, pk=session_pk)
    
    if not is_coach_or_admin(request.user):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    if not match_session.is_active:
        return JsonResponse({'error': 'Match is not active'}, status=400)
    
    try:
        data = json.loads(request.body)
        player_in_id = data.get('player_in')
        player_out_id = data.get('player_out')
        
        if not player_in_id or not player_out_id:
            return JsonResponse({'error': 'Missing player information'}, status=400)
        
        player_in = get_object_or_404(Player, pk=player_in_id)
        player_out = get_object_or_404(Player, pk=player_out_id)
        
        # Calculate current game time
        now = timezone.now()
        elapsed = now - match_session.start_time
        current_minute = math.floor(elapsed.total_seconds() / 60)
        
        # Calculate current period
        period = 1
        if match_session.periods > 1:
            period_minutes = match_session.period_length
            period = (current_minute // period_minutes) + 1
            period = min(period, match_session.periods)
        
        # Create the substitution record
        substitution = PlayerSubstitution.objects.create(
            match_session=match_session,
            player_in=player_in,
            player_out=player_out,
            minute=current_minute,
            period=period,
            timestamp=now
        )
        
        # Update playing time for player coming off
        player_out_record = PlayingTime.objects.get(match_session=match_session, player=player_out)
        if player_out_record.last_substitution_time:
            elapsed = now - player_out_record.last_substitution_time
            player_out_record.minutes_played += math.floor(elapsed.total_seconds() / 60)
        player_out_record.is_on_pitch = False
        player_out_record.last_substitution_time = None
        player_out_record.save()
        
        # Update playing time for player coming on
        player_in_record = PlayingTime.objects.get(match_session=match_session, player=player_in)
        player_in_record.is_on_pitch = True
        player_in_record.last_substitution_time = now
        player_in_record.save()
        
        return JsonResponse({
            'success': True,
            'minute': current_minute,
            'period': period,
            'player_in': player_in.first_name,
            'player_out': player_out.first_name,
            'player_in_id': player_in.id,  # Added player IDs to response
            'player_out_id': player_out.id,
            'sub_id': substitution.id
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def match_session_pitch_view(request, pk):
    """Mobile-optimized pitch view for match management"""
    match_session = get_object_or_404(MatchSession, pk=pk)
    
    # Get playing time records
    on_pitch = PlayingTime.objects.filter(match_session=match_session, is_on_pitch=True)
    on_bench = PlayingTime.objects.filter(match_session=match_session, is_on_pitch=False)
    
    # Calculate game time and next substitution if match is active
    current_game_time = None
    next_sub_time = None
    time_since_start = None
    next_sub_countdown = None
    
    if match_session.is_active and match_session.start_time:
        elapsed = timezone.now() - match_session.start_time
        time_since_start = elapsed
        current_game_time = math.floor(elapsed.total_seconds() / 60)
        current_seconds = elapsed.total_seconds()
        
        # Calculate next substitution time based on substitution interval
        if match_session.substitution_interval > 0:
            # Calculate how many substitution intervals have passed
            intervals_passed = current_game_time // match_session.substitution_interval
            # Calculate when the next interval will occur
            next_sub_time = (intervals_passed + 1) * match_session.substitution_interval
            # Calculate seconds until next substitution
            seconds_until_sub = (next_sub_time * 60) - current_seconds
            
            # Display seconds countdown when less than 30 seconds remain
            if seconds_until_sub <= 30:
                next_sub_countdown = {'value': int(seconds_until_sub), 'unit': 'sec', 'critical': True}
            else:
                # Otherwise, show minutes
                next_sub_countdown = {'value': math.ceil(seconds_until_sub / 60), 'unit': 'min', 'critical': False}
    
    # Get period from match_session model
    current_period = match_session.current_period
    
    # Calculate minutes remaining in current period
    minutes_remaining = None
    if current_game_time is not None:
        total_minutes_in_period = match_session.period_length
        
        # Calculate minutes elapsed in current period only (not counting previous periods)
        if time_since_start is not None:
            # Get the elapsed time only for this period
            minutes_elapsed_in_period = current_game_time % total_minutes_in_period
            minutes_remaining = total_minutes_in_period - minutes_elapsed_in_period
            
            # Add period info to template context
            elapsed_minutes_previous_periods = 0
            if match_session.elapsed_time > 0:
                elapsed_minutes_previous_periods = match_session.elapsed_time // 60
    
    # Calculate previous periods time - always available regardless of match state
    elapsed_minutes_previous_periods = int(match_session.elapsed_time / 60) if match_session.elapsed_time > 0 else 0
    
    # Set a default for elapsed_seconds_previous_periods for JavaScript clock
    elapsed_seconds_previous_periods = int(match_session.elapsed_time) if match_session.elapsed_time > 0 else 0
    
    # Ensure periods is always defined
    total_periods = match_session.periods if hasattr(match_session, 'periods') and match_session.periods else 2
    
    context = {
        'match_session': match_session,
        'on_pitch': on_pitch,
        'on_bench': on_bench,
        'current_game_time': current_game_time,
        'time_since_start': time_since_start,
        'next_sub_time': next_sub_time,
        'next_sub_countdown': next_sub_countdown,
        'can_edit': is_coach_or_admin(request.user),
        'current_period': current_period,
        'minutes_remaining': minutes_remaining,
        'total_periods': total_periods,
        'period_length': match_session.period_length,
        'substitution_interval': match_session.substitution_interval,
        'elapsed_minutes_previous_periods': elapsed_minutes_previous_periods,
        'elapsed_seconds_previous_periods': elapsed_seconds_previous_periods,
    }
    return render(request, 'teammanager/match_session_pitch.html', context)


@csrf_exempt
@login_required
def get_sub_recommendations(request, session_pk):
    """
    AJAX endpoint to get substitution recommendations
    Analyzes playing times and recommends optimal substitutions
    """
    try:
        match_session = get_object_or_404(MatchSession, pk=session_pk)
        
        if not is_approved_user(request.user):
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        if not match_session.is_active:
            return JsonResponse({'error': 'Match session is not active'}, status=400)
        
        # Calculate current playing times
        now = timezone.now()
        playing_times = PlayingTime.objects.filter(match_session=match_session)
        
        # Players currently on pitch
        players_on_pitch = []
        for pt in playing_times.filter(is_on_pitch=True):
            # Calculate real-time minutes
            real_time_minutes = pt.minutes_played
            if pt.last_substitution_time:
                elapsed = now - pt.last_substitution_time
                real_time_minutes += math.floor(elapsed.total_seconds() / 60)
            
            players_on_pitch.append({
                'id': pt.player.id,
                'name': str(pt.player),
                'minutes': real_time_minutes
            })
        
        # Players on bench
        players_on_bench = []
        match_elapsed_minutes = 0
        if match_session.start_time:
            match_elapsed = (now - match_session.start_time).total_seconds() / 60
            match_elapsed_minutes = math.floor(match_elapsed)
        
        for pt in playing_times.filter(is_on_pitch=False):
            real_time_minutes = pt.minutes_played
            bench_minutes = max(0, match_elapsed_minutes - real_time_minutes)
            
            players_on_bench.append({
                'id': pt.player.id,
                'name': str(pt.player),
                'minutes': real_time_minutes,
                'bench_minutes': bench_minutes
            })
        
        # Calculate playing time disparities and bench time for better recommendations
        if match_elapsed_minutes > 0:
            # Add more context to players on bench
            for player in players_on_bench:
                player['time_on_bench_percent'] = (player['bench_minutes'] / match_elapsed_minutes) * 100
                player['play_bench_ratio'] = player['minutes'] / max(1, player['bench_minutes'])
                
            # Add context for players on pitch
            for player in players_on_pitch:
                player['time_on_pitch_percent'] = (player['minutes'] / match_elapsed_minutes) * 100
        
        # Sort players - we want players with most minutes on pitch to come off
        # and players with most bench time and least playing time to go on
        players_on_pitch.sort(key=lambda p: p['minutes'], reverse=True)
        
        # For bench players, prioritize those who have both played less AND been on bench longer
        if match_elapsed_minutes > 0:
            players_on_bench.sort(key=lambda p: (p['minutes'], -p['bench_minutes']))
        else:
            players_on_bench.sort(key=lambda p: p['minutes'])
        
        # Generate recommendations for all on-pitch players
        recommendations = []
        
        # Only make recommendations if we have both players on pitch and bench
        if players_on_pitch and players_on_bench:
            # Use all players on pitch, already sorted by most minutes played
            candidates_out = players_on_pitch
            
            # For bench players, we'll include all of them in the response
            # and let the frontend handle the dropdown selection
            candidates_in = players_on_bench
            
            # For the initial recommendations, just use the top ones from bench
            top_bench = players_on_bench[:1] if len(players_on_bench) >= 1 else players_on_bench
            
            # Create recommendations with meaningful reasons for each player on pitch
            for player_out in candidates_out:
                for player_in in top_bench:
                    # Calculate play time difference
                    play_time_diff = player_out['minutes'] - player_in['minutes']
                    
                    # Allow recommendations with minimal difference
                    # Removing the 3-minute minimum requirement to provide more immediate recommendations
                    if play_time_diff < 0:  # Still avoid negative differences (bench players with more time)
                        continue
                    
                    # Create reason text based on all factors
                    reason = f"{player_out['name']} has played {player_out['minutes']} minutes"
                    
                    if match_elapsed_minutes > 0 and 'time_on_pitch_percent' in player_out:
                        reason += f" ({player_out['time_on_pitch_percent']:.0f}% of match time)"
                    
                    reason += f", while {player_in['name']} has only played {player_in['minutes']} minutes"
                    
                    if 'bench_minutes' in player_in and player_in['bench_minutes'] > 5:
                        reason += f" and has been waiting on the bench for {player_in['bench_minutes']} minutes"
                    
                    if match_elapsed_minutes > 0 and 'time_on_bench_percent' in player_in and player_in['time_on_bench_percent'] > 30:
                        reason += f" ({player_in['time_on_bench_percent']:.0f}% of match time)"
                    
                    reason += "."
                    
                    recommendations.append({
                        'player_out_id': player_out['id'],
                        'player_out_name': player_out['name'],
                        'player_out_minutes': player_out['minutes'],
                        'player_in_id': player_in['id'],
                        'player_in_name': player_in['name'],
                        'player_in_minutes': player_in['minutes'],
                        'bench_minutes': player_in.get('bench_minutes', 0),
                        'reason': reason
                    })
        
        # Include match information for proper period display
        match_info = {
            'period': match_session.current_period,
            'total_periods': match_session.periods if hasattr(match_session, 'periods') and match_session.periods else 2,
            # Add other match-related data that might be needed
        }
        
        return JsonResponse({
            'success': True,
            'recommendations': recommendations,  # Return all recommendations (7 or however many on-pitch players)
            'players_on_pitch': players_on_pitch,
            'players_on_bench': players_on_bench,
            'match_info': match_info
        })
    except Exception as e:
        import traceback
        print(f"Error in get_sub_recommendations: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
def update_playing_times(request, session_pk):
    """
    AJAX endpoint to update playing times for all active players
    Called periodically to keep the displayed playing times accurate
    """
    try:
        match_session = get_object_or_404(MatchSession, pk=session_pk)
        
        if not is_approved_user(request.user):
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        if not match_session.is_active:
            return JsonResponse({'error': 'Match session is not active'}, status=400)
        
        # Calculate current playing times without saving to database
        now = timezone.now()
        playing_times = PlayingTime.objects.filter(match_session=match_session)
        
        # Match statistics
        next_sub_countdown = None
        if match_session.start_time:
            # Calculate current session elapsed time
            current_seconds = (now - match_session.start_time).total_seconds()
            match_elapsed = current_seconds / 60
            
            # Use the current_period from the match session model
            current_period = match_session.current_period
            
            # Calculate overall match time (including previous periods)
            total_seconds = current_seconds + match_session.elapsed_time
            minute_in_match = int(total_seconds / 60)
            
            # Minutes in current period
            minute_in_period = int(match_elapsed)
            start_time_iso = match_session.start_time.isoformat()
            
            # Calculate next substitution time - based only on current period
            if match_session.substitution_interval > 0:
                intervals_passed = minute_in_period // match_session.substitution_interval
                next_sub_time = (intervals_passed + 1) * match_session.substitution_interval
                seconds_until_sub = (next_sub_time * 60) - current_seconds
                
                # Display seconds countdown when less than 30 seconds remain
                if seconds_until_sub <= 30:
                    next_sub_countdown = {'value': int(seconds_until_sub), 'unit': 'sec', 'critical': True}
                else:
                    # Otherwise, show minutes
                    next_sub_countdown = {'value': math.ceil(seconds_until_sub / 60), 'unit': 'min', 'critical': False}
        else:
            match_elapsed = 0
            current_period = match_session.current_period
            minute_in_match = 0
            minute_in_period = 0
            start_time_iso = None
        
        # Calculate current real-time playing minutes for each player
        playing_time_data = {}
        for pt in playing_times:
            real_time_minutes = pt.minutes_played
            
            # Add current session time for players on the pitch
            if pt.is_on_pitch and pt.last_substitution_time:
                elapsed = now - pt.last_substitution_time
                real_time_minutes += math.floor(elapsed.total_seconds() / 60)
            
            # Get total elapsed time for the match
            match_elapsed_minutes = 0
            if match_session.start_time:
                match_elapsed = (now - match_session.start_time).total_seconds() / 60
                match_elapsed_minutes = math.floor(match_elapsed)
            
            # Calculate bench time (total match time minus playing time)
            bench_minutes = 0
            if not pt.is_on_pitch:  # Currently on bench
                bench_minutes = match_elapsed_minutes - real_time_minutes
            
            playing_time_data[str(pt.player.id)] = {
                'minutes': real_time_minutes,
                'bench_minutes': max(0, bench_minutes),  # Ensure non-negative
                'on_pitch': pt.is_on_pitch,
                'name': str(pt.player)
            }
        
        # Print debug info to server console
        print(f"Update times for session {session_pk}: {len(playing_time_data)} players, match elapsed: {match_elapsed:.1f} min")
        
        return JsonResponse({
            'success': True,
            'playing_times': playing_time_data,
            'match_info': {
                'elapsed': int(match_elapsed),
                'period': current_period,
                'total_periods': match_session.periods if hasattr(match_session, 'periods') and match_session.periods else 2,
                'minute_in_match': minute_in_match,
                'minute_in_period': minute_in_period,
                'start_time': start_time_iso,
                'next_sub_countdown': next_sub_countdown,
                'substitution_interval': match_session.substitution_interval,
                'elapsed_minutes_previous_periods': int(match_session.elapsed_time / 60),
                'elapsed_seconds': int(match_session.elapsed_time), # Add seconds for client-side calculations
                'elapsed_seconds_previous_periods': int(match_session.elapsed_time) # Add this field for compatibility with client-side code
            }
        })
    except Exception as e:
        import traceback
        print(f"Error in update_playing_times: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
def reset_match_time(request, pk):
    """Reset the match time to the beginning of the current period"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=405)
    
    match_session = get_object_or_404(MatchSession, pk=pk)
    
    if not is_coach_or_admin(request.user):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    # Allow resetting even if match is not active
    # This makes it easier to prepare for the next match period
    
    # Reset time by updating start_time to now
    match_session.start_time = timezone.now()
    
    # Reset player times for the current period - we don't want to lose
    # the time from previous periods, so just reset the current period
    appearances = MatchAppearance.objects.filter(match_session=match_session)
    
    # For players currently on the pitch, reset their start time to now
    on_pitch_appearances = appearances.filter(status=MatchAppearance.STATUS_ON_PITCH)
    for appearance in on_pitch_appearances:
        # Calculate and save minutes played up to this point
        minutes_played = appearance.calculate_minutes_played()
        appearance.minutes_played = minutes_played
        # Then reset start time to now
        appearance.current_start_time = timezone.now()
        appearance.save()
    
    match_session.save()
    
    return JsonResponse({
        'success': True,
        'reset_time': timezone.now().isoformat()
    })

@csrf_exempt
def reset_substitution_timer(request, pk):
    """Reset the substitution timer"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=405)
    
    match_session = get_object_or_404(MatchSession, pk=pk)
    
    if not is_coach_or_admin(request.user):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    # Allow resetting even if match is not active
    # This makes it easier to prepare for the next substitution
    
    # Set the last_substitution time to now, which will reset the substitution timer
    # This starts a new rotation interval from this moment
    match_session.last_substitution = timezone.now()
    match_session.save()
    
    # Return the new substitution time so the frontend can use it
    reset_time = timezone.now()
    
    return JsonResponse({
        'success': True, 
        'reset_time': reset_time.isoformat(),
        'substitution_reset': True
    })

@csrf_exempt
def set_match_period(request, pk):
    """Manually set the match period"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=405)
    
    match_session = get_object_or_404(MatchSession, pk=pk)
    
    if not is_coach_or_admin(request.user):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        data = json.loads(request.body)
        period = int(data.get('period', 1))
        
        if period < 1 or period > match_session.periods:
            return JsonResponse({'error': f'Period must be between 1 and {match_session.periods}'}, status=400)
        
        # Store previous period
        previous_period = match_session.current_period
        
        # Calculate elapsed time from previous periods
        elapsed_time = 0
        if period > 1:
            # Each previous period contributes period_length minutes to elapsed time
            elapsed_time = (period - 1) * match_session.period_length * 60
        
        now = timezone.now()
        
        # First, record all player times up to this point
        appearances = MatchAppearance.objects.filter(match_session=match_session)
        for appearance in appearances:
            # Update minutes played for all players
            minutes_played = appearance.calculate_minutes_played()
            appearance.minutes_played = minutes_played
            
            # Reset start time for players on the pitch
            if appearance.status == MatchAppearance.STATUS_ON_PITCH:
                appearance.current_start_time = now
            
            appearance.save()
        
        # Update match session
        match_session.current_period = period
        match_session.elapsed_time = elapsed_time
        # Reset the start time to now
        match_session.start_time = now
        # Reset the substitution timer when starting a new period
        match_session.last_substitution = now
        match_session.save()
        
        return JsonResponse({
            'success': True, 
            'current_period': period, 
            'elapsed_time': elapsed_time,
            'start_time': now.isoformat(),
            'reset_time': now.isoformat()
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)