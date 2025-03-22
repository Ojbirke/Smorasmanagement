from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Team, Player, Match, MatchAppearance


class SignUpForm(UserCreationForm):
    email = forms.EmailField(max_length=254, help_text='Required. Enter a valid email address.')

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')


class TeamForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = ['name', 'description']


class PlayerForm(forms.ModelForm):
    class Meta:
        model = Player
        fields = ['first_name', 'last_name', 'team', 'position', 'date_of_birth', 'email', 'phone', 'active']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
        }


class MatchForm(forms.ModelForm):
    class Meta:
        model = Match
        fields = ['home_team', 'away_team', 'date', 'location', 'match_type', 'notes']
        widgets = {
            'date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }


class MatchScoreForm(forms.ModelForm):
    class Meta:
        model = Match
        fields = ['home_score', 'away_score']


class MatchAppearanceForm(forms.ModelForm):
    class Meta:
        model = MatchAppearance
        fields = ['player', 'team', 'minutes_played', 'goals', 'assists', 'yellow_cards', 'red_card']


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
        team_players = Player.objects.filter(team=team, active=True)
        self.fields['players'] = forms.ModelMultipleChoiceField(
            queryset=team_players,
            widget=forms.CheckboxSelectMultiple,
            required=False
        )
        self.match = match
        self.team = team
