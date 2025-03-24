from django.urls import path
from . import views

urlpatterns = [
    # Authentication
    path('signup/', views.SignUpView.as_view(), name='signup'),
    path('logout/', views.custom_logout, name='custom-logout'),
    
    # Dashboard
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    
    # Teams
    path('teams/', views.TeamListView.as_view(), name='team-list'),
    path('teams/add/', views.TeamCreateView.as_view(), name='team-add'),
    path('teams/<int:pk>/', views.TeamDetailView.as_view(), name='team-detail'),
    path('teams/<int:pk>/edit/', views.TeamUpdateView.as_view(), name='team-edit'),
    path('teams/<int:pk>/delete/', views.TeamDeleteView.as_view(), name='team-delete'),
    
    # Players
    path('players/', views.PlayerListView.as_view(), name='player-list'),
    path('players/add/', views.PlayerCreateView.as_view(), name='player-add'),
    path('players/import-excel/', views.ImportPlayersFromExcelView.as_view(), name='import-players-excel'),
    path('players/<int:pk>/', views.PlayerDetailView.as_view(), name='player-detail'),
    path('players/<int:pk>/edit/', views.PlayerUpdateView.as_view(), name='player-edit'),
    path('players/<int:pk>/delete/', views.PlayerDeleteView.as_view(), name='player-delete'),
    
    # Matches
    path('matches/', views.MatchListView.as_view(), name='match-list'),
    path('matches/add/', views.MatchCreateView.as_view(), name='match-add'),
    path('matches/<int:pk>/', views.MatchDetailView.as_view(), name='match-detail'),
    path('matches/<int:pk>/edit/', views.MatchUpdateView.as_view(), name='match-edit'),
    path('matches/<int:pk>/delete/', views.MatchDeleteView.as_view(), name='match-delete'),
    path('matches/<int:pk>/score/', views.MatchScoreUpdateView.as_view(), name='match-score'),
    path('matches/<int:match_id>/add-players/<int:team_id>/', views.add_players_to_match, name='add-players-to-match'),
    path('appearance/<int:appearance_id>/edit/', views.edit_appearance_stats, name='edit-appearance-stats'),
    
    # User Management
    path('users/', views.UserListView.as_view(), name='user-list'),
    path('users/<int:pk>/approve/', views.approve_user, name='approve-user'),
    path('users/<int:pk>/reject/', views.reject_user, name='reject-user'),
    path('users/<int:pk>/delete/', views.delete_user, name='delete-user'),
    
    # API for charts
    path('api/player-stats/', views.player_stats, name='player-stats'),
    path('api/match-stats/', views.match_stats, name='match-stats'),
    path('api/player-matrix/', views.player_matrix, name='player-matrix'),
]
