from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import (
    Team, Player, Match, MatchAppearance,
    FormationTemplate, LineupPosition, Lineup, LineupPlayerPosition,
    MatchSession, PlayerSubstitution, PlayingTime
)
from .models_video import VideoClip, HighlightReel, HighlightClipAssociation


class SignUpForm(UserCreationForm):
    email = forms.EmailField(max_length=254, help_text='Required. Enter a valid email address.')
    first_name = forms.CharField(max_length=30, required=True, help_text='Required.')
    last_name = forms.CharField(max_length=30, required=False, help_text='Optional.')
    
    ROLE_CHOICES = [
        ('player', 'Player'),
        ('coach', 'Coach'),
        ('admin', 'Admin'),
    ]
    
    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        required=True,
        help_text='Select your role in the team.',
        widget=forms.RadioSelect
    )
    
    player = forms.ModelChoiceField(
        queryset=Player.objects.filter(active=True).order_by('first_name'),
        required=False,
        help_text='If you are a player, select your player profile.',
        empty_label='-- Select your player profile --'
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2', 'role', 'player')
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['player'].queryset = Player.objects.filter(active=True).order_by('first_name')
        
        # Make player field visible only for player role (via JavaScript)


class TeamForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = ['name', 'description']


class PlayerForm(forms.ModelForm):
    class Meta:
        model = Player
        fields = ['first_name', 'last_name', 'position', 'date_of_birth', 'email', 'phone', 'active']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
        }


class MatchForm(forms.ModelForm):
    use_template = forms.BooleanField(
        required=False, 
        label='Use Previous Match as Template',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'use-template'})
    )
    
    template_match = forms.ModelChoiceField(
        queryset=Match.objects.all().order_by('-date'),
        required=False,
        label='Select Template Match',
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'template-match'})
    )
    
    class Meta:
        model = Match
        fields = ['smoras_team', 'opponent_name', 'location_type', 'date', 'location', 'match_type', 'notes']
        widgets = {
            'date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }
        labels = {
            'smoras_team': 'Smørås Team',
            'opponent_name': 'Opponent Name',
            'location_type': 'Match Location',
        }
        help_texts = {
            'location_type': 'Select whether the match is at home, away, or a neutral venue',
            'opponent_name': 'Name of the opponent team (no need to create them as a team)',
        }


class MatchScoreForm(forms.ModelForm):
    class Meta:
        model = Match
        fields = ['smoras_score', 'opponent_score']
        labels = {
            'smoras_score': 'Smørås Score',
            'opponent_score': 'Opponent Score',
        }


class MatchAppearanceForm(forms.ModelForm):
    class Meta:
        model = MatchAppearance
        fields = ['player', 'team', 'minutes_played', 'goals', 'assists', 'yellow_cards', 'red_card']
        widgets = {
            'minutes_played': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '120'}),
            'goals': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'assists': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'yellow_cards': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '2'}),
            'red_card': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class MatchAppearanceFormSet(forms.BaseModelFormSet):
    def __init__(self, *args, **kwargs):
        self.match = kwargs.pop('match', None)
        super().__init__(*args, **kwargs)
        
    def _construct_form(self, i, **kwargs):
        kwargs['match'] = self.match
        return super()._construct_form(i, **kwargs)


class PlayerSelectionForm(forms.Form):
    def __init__(self, match, team, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Get all active players
        all_active_players = Player.objects.filter(active=True)
        
        # Get players already assigned to this match
        existing_player_ids = MatchAppearance.objects.filter(match=match).values_list('player_id', flat=True)
        
        # Either show all players not yet in this match, or pre-selected if viewing existing players
        if kwargs.get('initial') and kwargs['initial'].get('players'):
            # Form is being used to edit existing selections
            available_players = all_active_players
        else:
            # Form is being used to add new players
            available_players = all_active_players.exclude(id__in=existing_player_ids)
        
        self.fields['players'] = forms.ModelMultipleChoiceField(
            queryset=available_players,
            widget=forms.CheckboxSelectMultiple,
            required=False,
            label=f"Select players for this match"
        )
        self.match = match
        self.team = team


class ExcelUploadForm(forms.Form):
    excel_file = forms.FileField(
        label='Select Excel File',
        help_text='Upload an Excel file (.xlsx) containing player data.'
    )


class FormationTemplateForm(forms.ModelForm):
    class Meta:
        model = FormationTemplate
        fields = ['name', 'description', 'player_count', 'formation_structure']
        help_texts = {
            'formation_structure': 'Enter in the format "4-4-2", "4-3-3", etc.',
            'player_count': 'Select the number of players for this formation (including goalkeeper)'
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'player_count': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        formation_structure = cleaned_data.get('formation_structure')
        player_count = cleaned_data.get('player_count')
        
        if formation_structure and player_count:
            try:
                layers = formation_structure.split('-')
                total_outfield_players = sum(int(layer) for layer in layers)
                total_players = total_outfield_players + 1  # Add goalkeeper
                
                if total_players != player_count:
                    self.add_error('formation_structure', 
                                  f'Formation should have {player_count-1} outfield players for {player_count}-a-side format. '
                                  f'Current structure has {total_outfield_players} outfield players.')
            except (ValueError, AttributeError):
                self.add_error('formation_structure', 'Invalid formation structure format. Use numbers and hyphens only (e.g. 4-4-2).')
        
        return cleaned_data


class LineupPositionForm(forms.ModelForm):
    class Meta:
        model = LineupPosition
        fields = ['name', 'short_name', 'position_type']


class LineupForm(forms.ModelForm):
    class Meta:
        model = Lineup
        fields = ['name', 'match', 'team', 'formation', 'is_template', 'direction', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
            'is_template': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'direction': forms.RadioSelect(attrs={'class': 'form-check-input'}),
        }
        help_texts = {
            'is_template': 'Check if you want to save this as a reusable template.',
            'direction': 'Choose the direction of play: first period (goalkeeper on left) or second period (goalkeeper on right).'
        }
        
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Only show upcoming or recent matches
        if 'match' in self.fields:
            from django.utils import timezone
            from datetime import timedelta
            
            # Get matches within 2 weeks before or 1 month after today
            two_weeks_ago = timezone.now() - timedelta(days=14)
            one_month_ahead = timezone.now() + timedelta(days=30)
            
            self.fields['match'].queryset = Match.objects.filter(
                date__gte=two_weeks_ago,
                date__lte=one_month_ahead
            ).order_by('date')
            
            # Improve the help text to explain player import feature
            self.fields['match'].help_text = 'Optional. If selected, players from this match will be automatically added to the lineup.'
            
            # Customize the display of match options
            self.fields['match'].label_from_instance = lambda obj: f"{obj.date.strftime('%Y-%m-%d')}: {obj.smoras_team} vs {obj.opponent_name}"
            
            # Make the match field optional
            self.fields['match'].required = False


class LineupPlayerPositionForm(forms.ModelForm):
    class Meta:
        model = LineupPlayerPosition
        fields = ['player', 'position', 'x_coordinate', 'y_coordinate', 'jersey_number', 'is_starter', 'notes']
        widgets = {
            'x_coordinate': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'max': '100'}),
            'y_coordinate': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'max': '100'}),
            'is_starter': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        
    def __init__(self, *args, **kwargs):
        lineup = kwargs.pop('lineup', None)
        super().__init__(*args, **kwargs)
        
        # Only show active players
        if 'player' in self.fields:
            self.fields['player'].queryset = Player.objects.filter(active=True).order_by('first_name', 'last_name')
            
        # If we already have a lineup, only show players on the team
        if lineup and 'player' in self.fields:
            # Get all players that have already been added to this lineup
            existing_players = LineupPlayerPosition.objects.filter(lineup=lineup).values_list('player_id', flat=True)
            
            # Exclude them from the available options if this is a new position
            if not self.instance.pk:
                self.fields['player'].queryset = self.fields['player'].queryset.exclude(id__in=existing_players)


class MatchSessionForm(forms.ModelForm):
    """
    Form for creating and updating match sessions
    """
    class Meta:
        model = MatchSession
        fields = [
            'name', 'match', 'periods', 'period_length', 'substitution_interval'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'match': forms.Select(attrs={'class': 'form-select'}),
            'periods': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '4'}),
            'period_length': forms.NumberInput(attrs={'class': 'form-control', 'min': '5', 'max': '45'}),
            'substitution_interval': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '15'}),
        }
        help_texts = {
            'name': 'Give this match session a name for easy reference',
            'periods': 'Number of periods in the match (typically 1 or 2)',
            'period_length': 'Length of each period in minutes',
            'substitution_interval': 'How often to make substitutions (in minutes)',
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Only show recent/upcoming matches
        from django.utils import timezone
        from datetime import timedelta
        
        two_weeks_ago = timezone.now() - timedelta(days=14)
        one_month_ahead = timezone.now() + timedelta(days=30)
        
        self.fields['match'].queryset = Match.objects.filter(
            date__gte=two_weeks_ago,
            date__lte=one_month_ahead
        ).order_by('date')
        
        # Customize match display
        self.fields['match'].label_from_instance = lambda obj: f"{obj.date.strftime('%Y-%m-%d')}: {obj.smoras_team} vs {obj.opponent_name}"


class PlayerSelectionSessionForm(forms.Form):
    """
    Form for selecting players for a match session
    """
    
    def __init__(self, match_session, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.match_session = match_session
        
        # Get the match for this session
        match = match_session.match
        
        # Get all active players
        available_players = Player.objects.filter(active=True).order_by('first_name', 'last_name')
        
        # Create a multiple selection field for players
        self.fields['players'] = forms.ModelMultipleChoiceField(
            queryset=available_players,
            widget=forms.CheckboxSelectMultiple(attrs={'class': 'player-checkbox'}),
            required=False,
            label="Select players for this match"
        )
        
        # Create fields for specifying which players start the match
        self.fields['starting_players'] = forms.ModelMultipleChoiceField(
            queryset=available_players,
            widget=forms.CheckboxSelectMultiple(attrs={'class': 'starter-checkbox'}),
            required=False,
            label="Select players to start on the pitch"
        )
        
        # Set initial values if we're editing an existing session
        if kwargs.get('initial'):
            # Add code here to pre-select players in an existing session
            pass


class SubstitutionForm(forms.ModelForm):
    """
    Form for recording player substitutions during a match
    """
    class Meta:
        model = PlayerSubstitution
        fields = ['player_in', 'player_out', 'minute', 'period', 'notes']
        widgets = {
            'player_in': forms.Select(attrs={'class': 'form-select'}),
            'player_out': forms.Select(attrs={'class': 'form-select'}),
            'minute': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '90'}),
            'period': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '4'}),
            'notes': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        match_session = kwargs.pop('match_session', None)
        super().__init__(*args, **kwargs)
        
        if match_session:
            # Filter the player lists to only include players for this match session
            players_on_pitch = PlayingTime.objects.filter(
                match_session=match_session, 
                is_on_pitch=True
            ).values_list('player_id', flat=True)
            
            players_on_bench = PlayingTime.objects.filter(
                match_session=match_session, 
                is_on_pitch=False
            ).values_list('player_id', flat=True)
            
            # Players who can come off are those on the pitch
            self.fields['player_out'].queryset = Player.objects.filter(
                id__in=players_on_pitch
            ).order_by('first_name', 'last_name')
            
            # Players who can come on are those on the bench
            self.fields['player_in'].queryset = Player.objects.filter(
                id__in=players_on_bench
            ).order_by('first_name', 'last_name')


class VideoClipForm(forms.ModelForm):
    """
    Form for creating and editing video clips
    """
    class Meta:
        model = VideoClip
        fields = [
            'title', 'description', 'game_minute', 'period', 
            'duration', 'video_file', 'is_highlight', 'action_tag', 'players_involved'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'game_minute': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '120'}),
            'period': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '4'}),
            'duration': forms.NumberInput(attrs={'class': 'form-control', 'min': '5', 'max': '120'}),
            'is_highlight': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'action_tag': forms.Select(attrs={'class': 'form-select'}),
            'players_involved': forms.CheckboxSelectMultiple(attrs={'class': 'list-unstyled'}),
        }
        
    def __init__(self, *args, **kwargs):
        match_session = kwargs.pop('match_session', None)
        super().__init__(*args, **kwargs)
        
        if match_session:
            # Filter players to only those in this match session
            session_player_ids = PlayingTime.objects.filter(
                match_session=match_session
            ).values_list('player_id', flat=True)
            
            self.fields['players_involved'].queryset = Player.objects.filter(
                id__in=session_player_ids
            ).order_by('first_name', 'last_name')
            
            # Set initial values for game minute and period based on current match status
            if match_session.is_active:
                # Game is in progress, use current values
                from django.utils import timezone
                import math
                
                if match_session.start_time:
                    current_time = timezone.now()
                    elapsed_seconds = (current_time - match_session.start_time).total_seconds()
                    elapsed_seconds += match_session.elapsed_time  # Add time from previous periods
                    
                    # Convert to minutes for the form fields
                    total_elapsed_minutes = math.floor(elapsed_seconds / 60)
                    
                    # Calculate period
                    period_length_seconds = match_session.period_length * 60
                    current_period = math.ceil(elapsed_seconds / period_length_seconds)
                    
                    # Calculate minutes within the current period
                    period_minutes = total_elapsed_minutes % match_session.period_length
                    
                    self.fields['game_minute'].initial = period_minutes
                    self.fields['period'].initial = current_period
            
            # Set a more descriptive label for the players field
            self.fields['players_involved'].label = f"Players featured in this clip"


class HighlightReelForm(forms.ModelForm):
    """
    Form for creating and editing highlight reels
    """
    class Meta:
        model = HighlightReel
        fields = ['title', 'description', 'is_published']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_published': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class HighlightClipOrderForm(forms.ModelForm):
    """
    Form for ordering clips in a highlight reel
    """
    class Meta:
        model = HighlightClipAssociation
        fields = ['video_clip', 'order']
        widgets = {
            'video_clip': forms.Select(attrs={'class': 'form-select'}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '100'}),
        }
