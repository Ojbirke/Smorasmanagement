from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Team, Player, Match, MatchAppearance, UserProfile


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


# Define an inline admin descriptor for UserProfile model
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'User Profiles'


# Define a new User admin
class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'get_role', 'get_status', 'is_active')
    list_filter = ('profile__role', 'profile__status', 'is_active', 'is_staff')
    
    def get_role(self, obj):
        return obj.profile.get_role_display() if hasattr(obj, 'profile') else '-'
    get_role.short_description = 'Role'
    
    def get_status(self, obj):
        return obj.profile.get_status_display() if hasattr(obj, 'profile') else '-'
    get_status.short_description = 'Status'


# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'status', 'player', 'created_at')
    list_filter = ('role', 'status')
    search_fields = ('user__username', 'user__email', 'player__first_name', 'player__last_name')
    list_editable = ('role', 'status')
    actions = ['approve_users', 'reject_users']
    
    def approve_users(self, request, queryset):
        queryset.update(status='approved')
        self.message_user(request, f"{queryset.count()} users have been approved.")
    approve_users.short_description = "Approve selected users"
    
    def reject_users(self, request, queryset):
        queryset.update(status='rejected')
        self.message_user(request, f"{queryset.count()} users have been rejected.")
    reject_users.short_description = "Reject selected users"
