import os
from django.db import models
from django.utils import timezone
from django.urls import reverse
from django.conf import settings
from .models import Player, Match, MatchSession

def video_upload_path(instance, filename):
    """Generate a path for uploaded videos"""
    # Create a timestamp-based filename to avoid collisions
    base, ext = os.path.splitext(filename)
    timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
    
    if isinstance(instance, VideoClip):
        return f'videos/clips/{instance.match_session.id}/{timestamp}{ext}'
    elif isinstance(instance, HighlightReel):
        return f'videos/highlights/{instance.id}/{timestamp}{ext}'
    
    return f'videos/other/{timestamp}{ext}'

class VideoClip(models.Model):
    """
    A video clip from a match session, typically a short clip of a notable moment
    like a goal, save, or other highlight.
    """
    ACTION_TAGS = [
        ('goal', 'Goal'),
        ('assist', 'Assist'),
        ('save', 'Save'),
        ('tackle', 'Tackle'),
        ('skill', 'Skill Move'),
        ('pass', 'Great Pass'),
        ('shot', 'Shot'),
        ('other', 'Other'),
    ]
    
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    video_file = models.FileField(upload_to=video_upload_path)
    thumbnail = models.ImageField(upload_to='videos/thumbnails/', blank=True, null=True)
    duration = models.PositiveIntegerField(help_text="Duration in seconds")
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Match context
    match_session = models.ForeignKey(MatchSession, on_delete=models.CASCADE, related_name='video_clips')
    game_minute = models.PositiveIntegerField(default=0, help_text="Minute in the game when this happened")
    period = models.PositiveIntegerField(default=1, help_text="Period number when this happened")
    
    # Classification
    action_tag = models.CharField(max_length=20, choices=ACTION_TAGS, default='other')
    is_highlight = models.BooleanField(default=True, help_text="Include in highlight reels")
    
    # Players involved
    players_involved = models.ManyToManyField(Player, related_name='video_appearances')
    
    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        return reverse('video-clip-detail', args=[self.id])
    
    @property
    def formatted_game_time(self):
        """Return formatted game time (e.g., "1st half 23'")"""
        period_names = {
            1: "1st half",
            2: "2nd half",
            3: "3rd period",
            4: "4th period",
            5: "Extra time 1",
            6: "Extra time 2",
            7: "Penalties"
        }
        period_name = period_names.get(self.period, f"Period {self.period}")
        return f"{period_name} {self.game_minute}'"
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['match_session']),
            models.Index(fields=['action_tag']),
            models.Index(fields=['is_highlight']),
        ]

class HighlightReel(models.Model):
    """
    A compilation of multiple video clips assembled into a single highlight reel
    """
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    video_file = models.FileField(upload_to=video_upload_path, blank=True, null=True)
    thumbnail = models.ImageField(upload_to='videos/thumbnails/', blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    is_published = models.BooleanField(default=False)
    
    # Optional associations
    match = models.ForeignKey(Match, on_delete=models.SET_NULL, null=True, blank=True, related_name='highlight_reels')
    
    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        return reverse('highlight-reel-detail', args=[self.id])
    
    @property
    def total_duration(self):
        """Calculate total duration of all clips in seconds"""
        clip_durations = [assoc.video_clip.duration for assoc in self.clip_associations.all()]
        return sum(clip_durations) if clip_durations else 0
    
    class Meta:
        ordering = ['-created_at']

class HighlightClipAssociation(models.Model):
    """
    Associates video clips with highlight reels, keeping track of the order
    """
    highlight_reel = models.ForeignKey(HighlightReel, on_delete=models.CASCADE, related_name='clip_associations')
    video_clip = models.ForeignKey(VideoClip, on_delete=models.CASCADE, related_name='highlight_appearances')
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['highlight_reel', 'order']
        unique_together = [['highlight_reel', 'order'], ['highlight_reel', 'video_clip']]