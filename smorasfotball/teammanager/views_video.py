from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.db.models import Count, Q

from .models import Match, MatchSession, Player
from .models_video import VideoClip, HighlightReel, HighlightClipAssociation
from .forms import VideoClipForm, HighlightReelForm

# Permission helpers
def can_edit_videos(user):
    """Check if user can edit videos (admin, coach)"""
    if not user.is_authenticated:
        return False
    
    if user.is_superuser:
        return True
    
    profile = getattr(user, 'profile', None)
    if not profile:
        return False
    
    return profile.is_admin() or profile.is_coach()

def can_view_videos(user):
    """Check if user can view videos (authenticated)"""
    return user.is_authenticated

# Video Clip Views
@login_required
def video_clip_list(request):
    """List all video clips"""
    clips = VideoClip.objects.all().select_related('match_session__match').prefetch_related('players_involved')
    
    # Filter by match session if provided
    match_session_id = request.GET.get('match_session')
    match_id = request.GET.get('match')
    player_id = request.GET.get('player')
    action_tag = request.GET.get('action')
    
    filter_active = False
    
    if match_session_id:
        try:
            match_session = MatchSession.objects.get(pk=match_session_id)
            clips = clips.filter(match_session=match_session)
            filter_active = True
        except (MatchSession.DoesNotExist, ValueError):
            pass
    
    if match_id and not match_session_id:
        try:
            match = Match.objects.get(pk=match_id)
            clips = clips.filter(match_session__match=match)
            filter_active = True
        except (Match.DoesNotExist, ValueError):
            pass
    
    if player_id:
        try:
            player = Player.objects.get(pk=player_id)
            clips = clips.filter(players_involved=player)
            filter_active = True
        except (Player.DoesNotExist, ValueError):
            pass
    
    if action_tag and action_tag != 'all':
        clips = clips.filter(action_tag=action_tag)
        filter_active = True
    
    # Get distinct action tags for filter dropdown
    action_tags = VideoClip.objects.values_list('action_tag', flat=True).distinct()
    
    context = {
        'video_clips': clips,
        'can_edit': can_edit_videos(request.user),
        'can_create': can_edit_videos(request.user),
        'action_tags': action_tags,
        'filter_active': filter_active,
    }
    
    return render(request, 'teammanager/video_clip_list.html', context)

@login_required
def video_clip_detail(request, pk):
    """Detail view for a video clip"""
    clip = get_object_or_404(VideoClip, pk=pk)
    
    # Get related clips (same players, same match, same action type)
    related_clips = VideoClip.objects.filter(
        Q(match_session=clip.match_session) | 
        Q(players_involved__in=clip.players_involved.all()) |
        Q(action_tag=clip.action_tag)
    ).exclude(pk=clip.pk).distinct()[:6]
    
    context = {
        'video_clip': clip,
        'related_clips': related_clips,
        'can_edit': can_edit_videos(request.user),
    }
    
    return render(request, 'teammanager/video_clip_detail.html', context)

@login_required
def video_clip_create(request, match_session_id=None):
    """Create a new video clip, optionally for a specific match session"""
    if not can_edit_videos(request.user):
        messages.error(request, "You don't have permission to create video clips.")
        return redirect('video-clip-list')
    
    match_session = None
    if match_session_id:
        match_session = get_object_or_404(MatchSession, pk=match_session_id)
    
    if request.method == 'POST':
        form = VideoClipForm(request.POST, request.FILES)
        if form.is_valid():
            clip = form.save(commit=False)
            if match_session:
                clip.match_session = match_session
            
            clip.created_by = request.user
            clip.save()
            
            # Handle many-to-many relationship with players
            players_involved = request.POST.getlist('players_involved')
            if players_involved:
                clip.players_involved.set(players_involved)
            
            messages.success(request, "Video clip created successfully.")
            
            # Redirect to appropriate page
            if match_session:
                return redirect('match-session-video-clips', match_session.id)
            return redirect('video-clip-detail', clip.id)
    else:
        initial = {}
        if match_session:
            initial['match_session'] = match_session
            initial['is_highlight'] = True
            
            # If match is active, set game minute and period
            if match_session.is_active:
                initial['period'] = match_session.current_period
                # Calculate current elapsed minutes
                elapsed_seconds = match_session.elapsed_time
                if match_session.start_time:
                    elapsed_seconds += (timezone.now() - match_session.start_time).total_seconds()
                initial['game_minute'] = int(elapsed_seconds / 60)
        
        form = VideoClipForm(initial=initial)
    
    # Get all players for the checkbox list
    players = Player.objects.filter(active=True)
    selected_players = []
    
    context = {
        'form': form,
        'match_session': match_session,
        'players': players,
        'selected_players': selected_players,
    }
    
    return render(request, 'teammanager/video_clip_form.html', context)

@login_required
def video_clip_edit(request, pk):
    """Edit an existing video clip"""
    clip = get_object_or_404(VideoClip, pk=pk)
    
    if not can_edit_videos(request.user):
        messages.error(request, "You don't have permission to edit video clips.")
        return redirect('video-clip-detail', clip.id)
    
    if request.method == 'POST':
        form = VideoClipForm(request.POST, request.FILES, instance=clip)
        if form.is_valid():
            form.save()
            
            # Handle many-to-many relationship with players
            players_involved = request.POST.getlist('players_involved')
            clip.players_involved.set(players_involved)
            
            messages.success(request, "Video clip updated successfully.")
            return redirect('video-clip-detail', clip.id)
    else:
        form = VideoClipForm(instance=clip)
    
    # Get all players for the checkbox list
    players = Player.objects.filter(active=True)
    selected_players = [p.id for p in clip.players_involved.all()]
    
    context = {
        'form': form,
        'players': players,
        'selected_players': selected_players,
    }
    
    return render(request, 'teammanager/video_clip_form.html', context)

@login_required
def video_clip_delete(request, pk):
    """Delete a video clip"""
    clip = get_object_or_404(VideoClip, pk=pk)
    
    if not can_edit_videos(request.user):
        messages.error(request, "You don't have permission to delete video clips.")
        return redirect('video-clip-detail', clip.id)
    
    match_session_id = clip.match_session.id
    
    if request.method == 'POST':
        clip.delete()
        messages.success(request, "Video clip deleted successfully.")
        return redirect('match-session-video-clips', match_session_id)
    
    context = {
        'object': clip,
        'cancel_url': reverse('video-clip-detail', args=[clip.id]),
    }
    
    return render(request, 'teammanager/confirm_delete.html', context)

@login_required
def match_session_video_clips(request, match_session_id):
    """View all video clips for a match session"""
    match_session = get_object_or_404(MatchSession, pk=match_session_id)
    video_clips = VideoClip.objects.filter(match_session=match_session).prefetch_related('players_involved')
    
    context = {
        'match_session': match_session,
        'video_clips': video_clips,
        'can_edit': can_edit_videos(request.user),
        'can_create': can_edit_videos(request.user),
    }
    
    return render(request, 'teammanager/video_clips_session.html', context)

@login_required
def match_session_video_manager(request, match_session_id):
    """Video recording manager for a match session"""
    match_session = get_object_or_404(MatchSession, pk=match_session_id)
    
    # Get recent clips for the right sidebar
    recent_clips = VideoClip.objects.filter(match_session=match_session).order_by('-timestamp')[:5]
    
    context = {
        'match_session': match_session,
        'recent_clips': recent_clips,
        'can_record': can_edit_videos(request.user),
    }
    
    return render(request, 'teammanager/match_session_video.html', context)

@login_required
def match_session_instant_replay(request, match_session_id):
    """API endpoint to save an instant replay video clip"""
    if not can_edit_videos(request.user):
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    match_session = get_object_or_404(MatchSession, pk=match_session_id)
    
    if request.method == 'POST':
        try:
            # Extract data from form
            title = request.POST.get('title', 'Instant Replay')
            action_tag = request.POST.get('action_tag', 'other')
            duration = int(request.POST.get('duration', 30))
            is_highlight = request.POST.get('is_highlight', 'true') == 'true'
            game_minute = int(request.POST.get('game_minute', 0))
            period = int(request.POST.get('period', 1))
            player_ids = request.POST.get('player_ids', '[]')
            
            # Handle video file upload
            video_file = request.FILES.get('video_file')
            if not video_file:
                return JsonResponse({'success': False, 'error': 'No video file uploaded'}, status=400)
            
            # Create the video clip
            clip = VideoClip.objects.create(
                match_session=match_session,
                title=title,
                video_file=video_file,
                duration=duration,
                action_tag=action_tag,
                is_highlight=is_highlight,
                game_minute=game_minute,
                period=period,
                created_by=request.user
            )
            
            # Add player associations
            import json
            try:
                player_id_list = json.loads(player_ids)
                if player_id_list:
                    players = Player.objects.filter(id__in=player_id_list)
                    clip.players_involved.set(players)
            except json.JSONDecodeError:
                pass
            
            return JsonResponse({
                'success': True, 
                'clip_id': clip.id,
                'message': 'Clip saved successfully'
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

@login_required
def player_video_clips(request, player_id):
    """View all video clips featuring a specific player"""
    player = get_object_or_404(Player, pk=player_id)
    video_clips = VideoClip.objects.filter(players_involved=player).select_related('match_session__match')
    
    context = {
        'player': player,
        'video_clips': video_clips,
        'can_edit': can_edit_videos(request.user),
    }
    
    return render(request, 'teammanager/player_video_clips.html', context)

# Highlight Reel Views
@login_required
def highlight_reel_list(request):
    """List all highlight reels"""
    reels = HighlightReel.objects.all().prefetch_related('clip_associations')
    
    context = {
        'highlight_reels': reels,
        'can_create': can_edit_videos(request.user),
        'can_edit': can_edit_videos(request.user),
    }
    
    return render(request, 'teammanager/highlight_reel_list.html', context)

@login_required
def highlight_reel_detail(request, pk):
    """Detail view for a highlight reel"""
    reel = get_object_or_404(HighlightReel, pk=pk)
    
    # Get clips in the correct order
    clips = reel.clip_associations.select_related('video_clip').order_by('order')
    
    # Get player stats (who appears most in these clips)
    player_stats = []
    if clips:
        # This would normally be a more sophisticated query to get player counts
        player_ids = set()
        for clip_assoc in clips:
            for player in clip_assoc.video_clip.players_involved.all():
                player_ids.add(player.id)
        
        if player_ids:
            players = Player.objects.filter(id__in=player_ids)
            # In a real implementation, you'd count appearances and sort
            player_stats = players
    
    context = {
        'highlight_reel': reel,
        'clips': clips,
        'player_stats': player_stats,
        'can_edit': can_edit_videos(request.user),
    }
    
    return render(request, 'teammanager/highlight_reel_detail.html', context)

@login_required
def highlight_reel_create(request):
    """Create a new highlight reel"""
    if not can_edit_videos(request.user):
        messages.error(request, "You don't have permission to create highlight reels.")
        return redirect('highlight-reel-list')
    
    if request.method == 'POST':
        form = HighlightReelForm(request.POST, request.FILES)
        if form.is_valid():
            reel = form.save(commit=False)
            reel.created_by = request.user
            reel.save()
            
            messages.success(request, "Highlight reel created successfully. Now add clips to it.")
            return redirect('highlight-reel-edit-clips', reel.id)
    else:
        form = HighlightReelForm()
    
    context = {
        'form': form,
    }
    
    return render(request, 'teammanager/highlight_reel_form.html', context)

@login_required
def highlight_reel_edit(request, pk):
    """Edit a highlight reel's basic information"""
    reel = get_object_or_404(HighlightReel, pk=pk)
    
    if not can_edit_videos(request.user):
        messages.error(request, "You don't have permission to edit highlight reels.")
        return redirect('highlight-reel-detail', reel.id)
    
    if request.method == 'POST':
        form = HighlightReelForm(request.POST, request.FILES, instance=reel)
        if form.is_valid():
            form.save()
            messages.success(request, "Highlight reel updated successfully.")
            return redirect('highlight-reel-detail', reel.id)
    else:
        form = HighlightReelForm(instance=reel)
    
    # Get stats for the sidebar
    clips_count = reel.clip_associations.count()
    total_duration = sum(clip.video_clip.duration for clip in reel.clip_associations.select_related('video_clip'))
    
    context = {
        'form': form,
        'clips_count': clips_count,
        'total_duration': total_duration,
    }
    
    return render(request, 'teammanager/highlight_reel_form.html', context)

@login_required
def highlight_reel_edit_clips(request, pk):
    """Edit the clips included in a highlight reel and their order"""
    reel = get_object_or_404(HighlightReel, pk=pk)
    
    if not can_edit_videos(request.user):
        messages.error(request, "You don't have permission to edit highlight reel clips.")
        return redirect('highlight-reel-detail', reel.id)
    
    # Get associated clips in order
    associated_clips = reel.clip_associations.select_related('video_clip').order_by('order')
    
    # Get all available clips that aren't already in this reel
    associated_clip_ids = [assoc.video_clip.id for assoc in associated_clips]
    available_clips = VideoClip.objects.filter(is_highlight=True).exclude(id__in=associated_clip_ids)
    
    context = {
        'highlight_reel': reel,
        'associated_clips': associated_clips,
        'available_clips': available_clips,
    }
    
    return render(request, 'teammanager/highlight_reel_edit_clips.html', context)

@login_required
def highlight_reel_update_clips(request, pk):
    """API endpoint to update clip associations and order"""
    reel = get_object_or_404(HighlightReel, pk=pk)
    
    if not can_edit_videos(request.user):
        messages.error(request, "You don't have permission to edit highlight reel clips.")
        return redirect('highlight-reel-detail', reel.id)
    
    if request.method == 'POST':
        # Get the new clip order from the form
        try:
            import json
            clip_order = json.loads(request.POST.get('clip_order', '[]'))
            generate_video = request.POST.get('generate_video', 'false') == 'true'
            is_published = request.POST.get('is_published', 'false') == 'true'
            
            # First, remove all existing associations
            reel.clip_associations.all().delete()
            
            # Create new associations with the correct order
            for i, clip_id in enumerate(clip_order):
                clip = VideoClip.objects.get(pk=clip_id)
                HighlightClipAssociation.objects.create(
                    highlight_reel=reel,
                    video_clip=clip,
                    order=i
                )
            
            # Update publication status if needed
            if reel.is_published != is_published:
                reel.is_published = is_published
                reel.save()
            
            # TODO: If generate_video is True, trigger the video compilation process
            # This would typically be an async task
            
            messages.success(request, "Highlight reel clips updated successfully.")
            return redirect('highlight-reel-detail', reel.id)
        
        except Exception as e:
            messages.error(request, f"Error updating clips: {str(e)}")
    
    return redirect('highlight-reel-edit-clips', reel.id)

@login_required
def highlight_reel_delete(request, pk):
    """Delete a highlight reel"""
    reel = get_object_or_404(HighlightReel, pk=pk)
    
    if not can_edit_videos(request.user):
        messages.error(request, "You don't have permission to delete highlight reels.")
        return redirect('highlight-reel-detail', reel.id)
    
    if request.method == 'POST':
        reel.delete()
        messages.success(request, "Highlight reel deleted successfully.")
        return redirect('highlight-reel-list')
    
    context = {
        'object': reel,
        'cancel_url': reverse('highlight-reel-detail', args=[reel.id]),
    }
    
    return render(request, 'teammanager/confirm_delete.html', context)

@login_required
def highlight_reel_add_clip(request, clip_id):
    """Add a clip to a highlight reel (or create a new one)"""
    clip = get_object_or_404(VideoClip, pk=clip_id)
    
    if not can_edit_videos(request.user):
        messages.error(request, "You don't have permission to add clips to highlight reels.")
        return redirect('video-clip-detail', clip.id)
    
    if request.method == 'POST':
        reel_id = request.POST.get('highlight_reel')
        
        if reel_id == 'new':
            # Create a new highlight reel with this clip
            title = request.POST.get('new_reel_title', 'New Highlight Reel')
            reel = HighlightReel.objects.create(
                title=title,
                created_by=request.user
            )
            HighlightClipAssociation.objects.create(
                highlight_reel=reel,
                video_clip=clip,
                order=0
            )
            messages.success(request, f"New highlight reel '{title}' created with this clip.")
            return redirect('highlight-reel-edit-clips', reel.id)
        
        else:
            # Add to existing reel
            try:
                reel = HighlightReel.objects.get(pk=reel_id)
                
                # Check if clip is already in the reel
                if not HighlightClipAssociation.objects.filter(highlight_reel=reel, video_clip=clip).exists():
                    # Get the next order value
                    next_order = HighlightClipAssociation.objects.filter(highlight_reel=reel).count()
                    
                    HighlightClipAssociation.objects.create(
                        highlight_reel=reel,
                        video_clip=clip,
                        order=next_order
                    )
                    
                    messages.success(request, f"Clip added to '{reel.title}'.")
                else:
                    messages.info(request, f"This clip is already in '{reel.title}'.")
                
                return redirect('highlight-reel-edit-clips', reel.id)
            
            except HighlightReel.DoesNotExist:
                messages.error(request, "Selected highlight reel doesn't exist.")
    
    # Get list of existing highlight reels for the selection
    reels = HighlightReel.objects.all()
    
    context = {
        'video_clip': clip,
        'highlight_reels': reels,
    }
    
    return render(request, 'teammanager/highlight_reel_add_clip.html', context)