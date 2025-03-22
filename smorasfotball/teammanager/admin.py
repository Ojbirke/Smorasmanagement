from django.contrib import admin
from .models import Team, Player, Match, MatchAppearance


# We don't need PlayerInline anymore since Player doesn't have a ForeignKey to Team


class MatchAppearanceInline(admin.TabularInline):
    model = MatchAppearance
    extra = 1


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'player_count', 'created_at')
    search_fields = ('name',)
    
    def player_count(self, obj):
        # Count players who have appeared for this team in any match
        return Player.objects.filter(match_appearances__team=obj).distinct().count()
    player_count.short_description = 'Number of Players'


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'position', 'active', 'total_matches')
    list_filter = ('active', 'position')
    search_fields = ('first_name', 'last_name')
    
    def total_matches(self, obj):
        return obj.match_appearances.count()
    total_matches.short_description = 'Matches Played'


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'date', 'match_type', 'get_result')
    list_filter = ('match_type', 'date', 'smoras_team', 'location_type')
    search_fields = ('smoras_team__name', 'opponent_name', 'location')
    inlines = [MatchAppearanceInline]


@admin.register(MatchAppearance)
class MatchAppearanceAdmin(admin.ModelAdmin):
    list_display = ('player', 'match', 'team', 'minutes_played', 'goals', 'assists')
    list_filter = ('team', 'goals', 'assists', 'yellow_cards', 'red_card')
    search_fields = ('player__first_name', 'player__last_name', 'match__smoras_team__name', 'match__opponent_name')
