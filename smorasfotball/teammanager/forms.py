from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Team, Player, Match, MatchAppearance


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
