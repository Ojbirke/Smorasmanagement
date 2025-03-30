from django.urls import path
from . import views
from . import views_db_admin
from . import views_lineup
from . import views_match_management
from . import views_video
from . import views_db_diagnostics

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
    
    # Database Management
    path('database/', views_db_admin.database_overview, name='database-overview'),
    path('database/diagnostic/', views_db_diagnostics.database_diagnostic_view, name='database-diagnostic'),
    
    # API for charts
    path('api/player-stats/', views.player_stats, name='player-stats'),
    path('api/match-stats/', views.match_stats, name='match-stats'),
    path('api/player-matrix/', views.player_matrix, name='player-matrix'),
    
    # Lineup Builder
    path('lineups/', views_lineup.LineupListView.as_view(), name='lineup-list'),
    path('lineups/add/', views_lineup.LineupCreateView.as_view(), name='lineup-add'),
    path('lineups/<int:pk>/', views_lineup.LineupDetailView.as_view(), name='lineup-detail'),
    path('lineups/<int:pk>/builder/', views_lineup.LineupBuilderView.as_view(), name='lineup-builder'),
    path('lineups/<int:pk>/edit/', views_lineup.LineupUpdateView.as_view(), name='lineup-edit'),
    path('lineups/<int:pk>/duplicate/', views_lineup.duplicate_lineup, name='lineup-duplicate'),
    path('lineups/<int:pk>/delete/', views_lineup.LineupDeleteView.as_view(), name='lineup-delete'),
    path('lineups/<int:pk>/export-pdf/', views_lineup.export_lineup_pdf, name='lineup-export-pdf'),
    
    # Lineup Player Position AJAX endpoints
    path('lineups/<int:pk>/save-positions/', views_lineup.save_lineup_positions, name='save-lineup-positions'),
    path('lineups/<int:lineup_id>/remove-player/<int:player_id>/', views_lineup.remove_player_from_lineup, name='remove-player-from-lineup'),
    
    # Formation Templates
    path('formations/', views_lineup.FormationTemplateListView.as_view(), name='formation-list'),
    path('formations/add/', views_lineup.FormationTemplateCreateView.as_view(), name='formation-add'),
    path('formations/<int:pk>/edit/', views_lineup.FormationTemplateUpdateView.as_view(), name='formation-edit'),
    path('formations/<int:pk>/delete/', views_lineup.FormationTemplateDeleteView.as_view(), name='formation-delete'),
    
    # Lineup Positions
    path('positions/', views_lineup.LineupPositionListView.as_view(), name='position-list'),
    path('positions/add/', views_lineup.LineupPositionCreateView.as_view(), name='position-add'), 
    path('positions/<int:pk>/edit/', views_lineup.LineupPositionUpdateView.as_view(), name='position-edit'),
    path('positions/<int:pk>/delete/', views_lineup.LineupPositionDeleteView.as_view(), name='position-delete'),
    path('positions/create-defaults/', views_lineup.create_default_positions, name='position-create-defaults'),
    
    # Match Sessions
    path('match-sessions/', views_match_management.match_session_list, name='match-session-list'),
    path('match-sessions/add/', views_match_management.MatchSessionCreateView.as_view(), name='match-session-create'),
    path('match-sessions/<int:pk>/', views_match_management.match_session_detail, name='match-session-detail'),
    path('match-sessions/<int:pk>/edit/', views_match_management.MatchSessionUpdateView.as_view(), name='match-session-update'),
    path('match-sessions/<int:pk>/delete/', views_match_management.MatchSessionDeleteView.as_view(), name='match-session-delete'),
    path('match-sessions/<int:pk>/players/', views_match_management.match_session_players, name='match-session-players'),
    path('match-sessions/<int:pk>/start/', views_match_management.match_session_start, name='match-session-start'),
    path('match-sessions/<int:pk>/stop/', views_match_management.match_session_stop, name='match-session-stop'),
    path('match-sessions/<int:pk>/substitute/', views_match_management.substitution_create, name='substitution-create'),
    path('match-sessions/<int:pk>/pitch/', views_match_management.match_session_pitch_view, name='match-session-pitch'),
    path('match-sessions/<int:session_pk>/quick-sub/', views_match_management.ajax_quick_sub, name='match-session-quick-sub'),
    path('match-sessions/<int:session_pk>/update-times/', views_match_management.update_playing_times, name='match-session-update-times'),
    path('match-sessions/<int:session_pk>/recommendations/', views_match_management.get_sub_recommendations, name='match-session-recommendations'),
    
    # Video Clips
    path('videos/', views_video.video_clip_list, name='video-clip-list'),
    path('videos/<int:pk>/', views_video.video_clip_detail, name='video-clip-detail'),
    path('videos/add/', views_video.video_clip_create, name='video-clip-create'),
    path('videos/<int:pk>/edit/', views_video.video_clip_edit, name='video-clip-edit'),
    path('videos/<int:pk>/delete/', views_video.video_clip_delete, name='video-clip-delete'),
    
    # Match Session Videos
    path('match-sessions/<int:match_session_id>/videos/', views_video.match_session_video_clips, name='match-session-video-clips'),
    path('match-sessions/<int:match_session_id>/videos/add/', views_video.video_clip_create, name='match-session-video-clip-create'),
    path('match-sessions/<int:match_session_id>/video-manager/', views_video.match_session_video_manager, name='match-session-video-manager'),
    path('match-sessions/<int:match_session_id>/instant-replay/', views_video.match_session_instant_replay, name='match-session-instant-replay'),
    
    # Highlight Reels
    path('highlights/', views_video.highlight_reel_list, name='highlight-reel-list'),
    path('highlights/<int:pk>/', views_video.highlight_reel_detail, name='highlight-reel-detail'),
    path('highlights/add/', views_video.highlight_reel_create, name='highlight-reel-create'),
    path('highlights/<int:pk>/edit/', views_video.highlight_reel_edit, name='highlight-reel-edit'),
    path('highlights/<int:pk>/edit-clips/', views_video.highlight_reel_edit_clips, name='highlight-reel-edit-clips'),
    path('highlights/<int:pk>/delete/', views_video.highlight_reel_delete, name='highlight-reel-delete'),
    
    # Player Videos
    path('players/<int:player_pk>/videos/', views_video.player_video_clips, name='player-video-clips'),
    

]
