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
import json
import math
from datetime import timedelta

from .models import (
    Match, Player, Team, 
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
        
        # Calculate next substitution time
        if match_session.substitution_interval > 0:
            next_sub_minute = (math.floor(current_game_time / match_session.substitution_interval) + 1) * match_session.substitution_interval
            next_sub_time = next_sub_minute - current_game_time
    
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
        
        # Redirect to player selection page
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
            # Import players from match appearances
            players_from_match = Player.objects.filter(
                match_appearances__match=match_session.match
            ).distinct()
            
            # Default formation for 7-a-side is usually 2-3-1
            formation_count = 7
            if players_from_match.count() >= 11:
                formation_count = 11  # 11-a-side
            elif players_from_match.count() >= 9:
                formation_count = 9  # 9-a-side
            elif players_from_match.count() >= 7:
                formation_count = 7  # 7-a-side
            elif players_from_match.count() >= 5:
                formation_count = 5  # 5-a-side
            
            # Determine starters and bench
            all_players = list(players_from_match)
            starters = all_players[:formation_count]
            bench = all_players[formation_count:]
            
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
            
            messages.success(request, f"Imported {len(all_players)} players from match. {len(starters)} players are starting.")
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
    
    if not is_coach_or_admin(request.user):
        messages.error(request, "You need to be a coach or admin to start match sessions.")
        return redirect('match-session-detail', pk=match_session.pk)
    
    # Ensure we have enough players to start
    playing_times = PlayingTime.objects.filter(match_session=match_session)
    players_on_pitch = playing_times.filter(is_on_pitch=True).count()
    
    if players_on_pitch < 5:  # Minimum for a viable match (adjust as needed)
        messages.error(request, "You need at least 5 players on the pitch to start a match.")
        return redirect('match-session-detail', pk=match_session.pk)
    
    # Start the match
    match_session.is_active = True
    match_session.start_time = timezone.now()
    match_session.save()
    
    # Update starting time for all players on the pitch
    PlayingTime.objects.filter(match_session=match_session, is_on_pitch=True).update(
        last_substitution_time=timezone.now()
    )
    
    messages.success(request, "Match session started. Substitution tracking is now active.")
    return redirect('match-session-detail', pk=match_session.pk)


@login_required
def match_session_stop(request, pk):
    """Stop a match session"""
    match_session = get_object_or_404(MatchSession, pk=pk)
    
    if not is_coach_or_admin(request.user):
        messages.error(request, "You need to be a coach or admin to stop match sessions.")
        return redirect('match-session-detail', pk=match_session.pk)
    
    if match_session.is_active:
        # Update playing time for all active players
        now = timezone.now()
        
        for playing_time in PlayingTime.objects.filter(match_session=match_session, is_on_pitch=True):
            if playing_time.last_substitution_time:
                elapsed = now - playing_time.last_substitution_time
                playing_time.minutes_played += math.floor(elapsed.total_seconds() / 60)
                playing_time.last_substitution_time = None
                playing_time.save()
        
        # Stop the match
        match_session.is_active = False
        match_session.save()
        
        messages.success(request, "Match session stopped. Playing time has been recorded.")
    else:
        messages.warning(request, "This match session is not currently active.")
    
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
    
    if match_session.is_active and match_session.start_time:
        elapsed = timezone.now() - match_session.start_time
        time_since_start = elapsed
        current_game_time = math.floor(elapsed.total_seconds() / 60)
        
        # Calculate next substitution time
        if match_session.substitution_interval > 0:
            next_sub_minute = (math.floor(current_game_time / match_session.substitution_interval) + 1) * match_session.substitution_interval
            next_sub_time = next_sub_minute - current_game_time
    
    # Calculate period
    current_period = 1
    if current_game_time is not None and match_session.periods > 1:
        current_period = min((current_game_time // match_session.period_length) + 1, match_session.periods)
    
    # Calculate minutes remaining in current period
    minutes_remaining = None
    if current_game_time is not None:
        total_minutes_in_period = match_session.period_length
        minutes_elapsed_in_period = current_game_time % total_minutes_in_period
        minutes_remaining = total_minutes_in_period - minutes_elapsed_in_period
    
    context = {
        'match_session': match_session,
        'on_pitch': on_pitch,
        'on_bench': on_bench,
        'current_game_time': current_game_time,
        'time_since_start': time_since_start,
        'next_sub_time': next_sub_time,
        'can_edit': is_coach_or_admin(request.user),
        'current_period': current_period,
        'minutes_remaining': minutes_remaining,
        'total_periods': match_session.periods,
        'period_length': match_session.period_length,
        'substitution_interval': match_session.substitution_interval,
    }
    return render(request, 'teammanager/match_session_pitch.html', context)


@login_required
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
        if match_session.start_time:
            match_elapsed = (now - match_session.start_time).total_seconds() / 60
            current_period = min((int(match_elapsed) // match_session.period_length) + 1, match_session.periods)
            minute_in_match = int(match_elapsed)
            minute_in_period = int(match_elapsed) % match_session.period_length
            start_time_iso = match_session.start_time.isoformat()
        else:
            match_elapsed = 0
            current_period = 1
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
            
            playing_time_data[str(pt.player.id)] = {
                'minutes': real_time_minutes,
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
                'minute_in_match': minute_in_match,
                'minute_in_period': minute_in_period,
                'start_time': start_time_iso
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