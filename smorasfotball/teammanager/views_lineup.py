from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.views.generic.edit import FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.db.models import Count, Q
from django.core.exceptions import PermissionDenied
import json
import io
import base64
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors

from .models import (
    FormationTemplate, LineupPosition, Lineup, LineupPlayerPosition,
    Team, Player, Match, MatchAppearance
)
from .forms import (
    FormationTemplateForm, LineupPositionForm, LineupForm, LineupPlayerPositionForm
)


def is_coach_or_admin(user):
    """Check if user is an approved coach or admin"""
    if not user.is_authenticated:
        return False
    try:
        profile = user.profile
        return (profile.is_approved() and 
                (profile.is_coach() or profile.is_admin()))
    except:
        return False


class LineupListView(LoginRequiredMixin, ListView):
    model = Lineup
    template_name = 'teammanager/lineup_list.html'
    context_object_name = 'lineups'
    ordering = ['-created_at']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter for templates or match-specific lineups
        show_templates = self.request.GET.get('templates', 'false')
        if show_templates.lower() == 'true':
            queryset = queryset.filter(is_template=True)
        else:
            queryset = queryset.filter(is_template=False)
        
        # Filter by team if specified
        team_id = self.request.GET.get('team')
        if team_id:
            queryset = queryset.filter(team_id=team_id)
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Pass common user role flags to template
        if self.request.user.is_authenticated:
            try:
                profile = self.request.user.profile
                context['is_admin'] = profile.is_admin() and profile.is_approved()
                context['is_coach'] = profile.is_coach() and profile.is_approved() 
                context['is_player'] = profile.is_player() and profile.is_approved()
                context['is_approved'] = profile.is_approved()
            except:
                pass
        
        # Add teams for filtering
        context['teams'] = Team.objects.all()
        
        # Check active filters for the UI
        context['show_templates'] = self.request.GET.get('templates', 'false').lower() == 'true'
        context['selected_team'] = self.request.GET.get('team', '')
        
        return context


class LineupDetailView(LoginRequiredMixin, DetailView):
    model = Lineup
    template_name = 'teammanager/lineup_detail.html'
    context_object_name = 'lineup'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Pass common user role flags to template
        if self.request.user.is_authenticated:
            try:
                profile = self.request.user.profile
                context['is_admin'] = profile.is_admin() and profile.is_approved()
                context['is_coach'] = profile.is_coach() and profile.is_approved() 
                context['is_player'] = profile.is_player() and profile.is_approved()
                context['is_approved'] = profile.is_approved()
            except:
                pass
                
        # Get player positions for this lineup
        context['player_positions'] = self.object.player_positions.all().select_related('player', 'position')
        
        # Get available players for this team
        context['available_players'] = Player.objects.filter(active=True)
        
        # Get available positions
        context['available_positions'] = LineupPosition.objects.all()
        
        return context


class LineupCreateView(LoginRequiredMixin, CreateView):
    model = Lineup
    form_class = LineupForm
    template_name = 'teammanager/lineup_form.html'
    
    def dispatch(self, request, *args, **kwargs):
        if not is_coach_or_admin(request.user):
            messages.error(request, "You don't have permission to create lineups.")
            return redirect('lineup-list')
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Pass common user role flags to template
        if self.request.user.is_authenticated:
            try:
                profile = self.request.user.profile
                context['is_admin'] = profile.is_admin() and profile.is_approved()
                context['is_coach'] = profile.is_coach() and profile.is_approved() 
                context['is_player'] = profile.is_player() and profile.is_approved()
                context['is_approved'] = profile.is_approved()
            except:
                pass
                
        # Check if we're copying from a template
        template_id = self.request.GET.get('from_template')
        if template_id:
            try:
                template = Lineup.objects.get(id=template_id, is_template=True)
                context['template'] = template
                context['from_template'] = True
            except Lineup.DoesNotExist:
                pass
        
        context['formations'] = FormationTemplate.objects.all()
        
        return context
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        
        # Save the new lineup
        response = super().form_valid(form)
        
        # Check if we're copying from a template
        template_id = self.request.GET.get('from_template')
        if template_id:
            try:
                template = Lineup.objects.get(id=template_id, is_template=True)
                
                # Copy player positions from template
                for position in template.player_positions.all():
                    LineupPlayerPosition.objects.create(
                        lineup=self.object,
                        player=position.player if position.player.active else None,
                        position=position.position,
                        x_coordinate=position.x_coordinate,
                        y_coordinate=position.y_coordinate,
                        jersey_number=position.jersey_number,
                        is_starter=position.is_starter,
                        notes=position.notes
                    )
                
                messages.success(self.request, f"Lineup created from template '{template.name}'.")
            except Lineup.DoesNotExist:
                messages.error(self.request, "Template lineup not found.")
        # If no template but we have a match, add the match players to the lineup
        elif form.instance.match:
            match = form.instance.match
            team = form.instance.team
            
            # Get all players who appeared in this match for this team
            match_appearances = match.appearances.filter(team=team)
            
            # Get or create default positions based on formation
            positions = self._get_positions_from_formation(form.instance.formation)
            
            # Add each player who appeared in the match to the lineup
            # First, determine how many players should be in the starting lineup
            formation = form.instance.formation
            starting_count = 11  # Default for standard football
            
            # If we have a formation, use its player count to determine starters
            if formation:
                starting_count = formation.player_count
            
            # Process each player
            for idx, appearance in enumerate(match_appearances):
                # Skip if player is not active
                if not appearance.player.active:
                    continue
                    
                # Calculate default positions (evenly distributed)
                position_type = None
                if idx == 0:  # First player is goalkeeper
                    position_type = LineupPosition.objects.filter(position_type='GK').first()
                else:
                    # Rotate through remaining position types for other players
                    position_options = ['DEF', 'MID', 'FWD']
                    position_type = LineupPosition.objects.filter(
                        position_type=position_options[(idx - 1) % 3]
                    ).first()
                
                # Calculate sensible default coordinates based on position type
                x, y = self._get_default_coordinates(position_type, idx, len(match_appearances))
                
                # Determine if this player is a starter based on position and index
                # First 'starting_count' players are starters, rest are substitutes
                is_starter = idx < starting_count
                
                # If it's a substitute, place them on the sideline
                if not is_starter:
                    # Place substitutes on the left edge of the pitch
                    x = 1
                    # Distribute them vertically with equal spacing
                    sub_idx = idx - starting_count
                    sub_spacing = 80 / max(1, match_appearances.count() - starting_count)
                    y = 10 + (sub_idx * sub_spacing)
                
                # Create the player position in the lineup
                LineupPlayerPosition.objects.create(
                    lineup=self.object,
                    player=appearance.player,
                    position=position_type,
                    x_coordinate=x,
                    y_coordinate=y,
                    jersey_number=idx + 1,  # Default jersey number
                    is_starter=is_starter,
                    notes=f"Added from match: {match.smoras_team} vs {match.opponent_name}"
                )
            
            messages.success(self.request, f"Lineup created with {match_appearances.count()} players from match: {match.smoras_team} vs {match.opponent_name}.")
        else:
            messages.success(self.request, "Lineup created successfully.")
        
        return response
        
    def _get_positions_from_formation(self, formation):
        """Get appropriate positions based on the formation"""
        position_types = {
            'GK': 1,  # Always 1 goalkeeper
            'DEF': 4, # Default 4 defenders
            'MID': 4, # Default 4 midfielders
            'FWD': 2  # Default 2 forwards
        }
        
        # If we have a formation, parse its structure
        if formation:
            try:
                parts = formation.formation_structure.split('-')
                if len(parts) >= 3:  # Typical format: 4-4-2, 4-3-3, etc.
                    position_types['DEF'] = int(parts[0])
                    position_types['MID'] = int(parts[1])
                    position_types['FWD'] = int(parts[2])
            except (ValueError, IndexError):
                # If parsing fails, use defaults
                pass
                
        return position_types
        
    def _get_default_coordinates(self, position_type, idx, total_players):
        """Calculate sensible default coordinates based on position and index"""
        if not position_type:
            # Default to middle if no position
            return 50, 50
            
        # X coordinate - based on position type
        if position_type.position_type == 'GK':
            x = 10  # Goalkeeper near the goal
        elif position_type.position_type == 'DEF':
            x = 30  # Defenders
        elif position_type.position_type == 'MID':
            x = 60  # Midfielders
        elif position_type.position_type == 'FWD':
            x = 80  # Forwards
        else:
            x = 50  # Default to middle
            
        # Y coordinate - evenly distribute players of same position type
        base_y = 50  # Start in the middle
        spread = min(70, total_players * 5)  # Limit the spread based on player count
        
        # Distribute Y based on position and index to avoid overlap
        if position_type.position_type == 'GK':
            y = 50  # Goalkeeper in the middle
        else:
            # For each position type, calculate how many we have
            position_count = {
                'DEF': min(4, max(3, total_players // 4)),
                'MID': min(4, max(3, total_players // 3)),
                'FWD': min(3, max(2, total_players // 5))
            }[position_type.position_type]
            
            # Distribute Y based on position count
            offset = spread / (position_count + 1)
            # Position index within its category
            pos_idx = idx % position_count
            y = 50 - (spread / 2) + (offset * (pos_idx + 1))
            
        return x, y
    
    def get_success_url(self):
        return reverse('lineup-builder', kwargs={'pk': self.object.pk})


class LineupUpdateView(LoginRequiredMixin, UpdateView):
    model = Lineup
    form_class = LineupForm
    template_name = 'teammanager/lineup_form.html'
    
    def dispatch(self, request, *args, **kwargs):
        if not is_coach_or_admin(request.user):
            messages.error(request, "You don't have permission to update lineups.")
            return redirect('lineup-list')
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Pass common user role flags to template
        if self.request.user.is_authenticated:
            try:
                profile = self.request.user.profile
                context['is_admin'] = profile.is_admin() and profile.is_approved()
                context['is_coach'] = profile.is_coach() and profile.is_approved() 
                context['is_player'] = profile.is_player() and profile.is_approved()
                context['is_approved'] = profile.is_approved()
            except:
                pass
                
        context['formations'] = FormationTemplate.objects.all()
        context['editing'] = True
        
        return context
    
    def form_valid(self, form):
        messages.success(self.request, "Lineup updated successfully.")
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('lineup-builder', kwargs={'pk': self.object.pk})


class LineupDeleteView(LoginRequiredMixin, DeleteView):
    model = Lineup
    template_name = 'teammanager/lineup_confirm_delete.html'
    success_url = reverse_lazy('lineup-list')
    
    def dispatch(self, request, *args, **kwargs):
        if not is_coach_or_admin(request.user):
            messages.error(request, "You don't have permission to delete lineups.")
            return redirect('lineup-list')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Pass common user role flags to template
        if self.request.user.is_authenticated:
            try:
                profile = self.request.user.profile
                context['is_admin'] = profile.is_admin() and profile.is_approved()
                context['is_coach'] = profile.is_coach() and profile.is_approved() 
                context['is_player'] = profile.is_player() and profile.is_approved()
                context['is_approved'] = profile.is_approved()
            except:
                pass
                
        return context
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, "Lineup deleted successfully.")
        return super().delete(request, *args, **kwargs)


class LineupBuilderView(LoginRequiredMixin, DetailView):
    model = Lineup
    template_name = 'teammanager/lineup_builder.html'
    context_object_name = 'lineup'
    
    def dispatch(self, request, *args, **kwargs):
        if not is_coach_or_admin(request.user):
            messages.error(request, "You don't have permission to use the lineup builder.")
            return redirect('lineup-list')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Pass common user role flags to template
        if self.request.user.is_authenticated:
            try:
                profile = self.request.user.profile
                context['is_admin'] = profile.is_admin() and profile.is_approved()
                context['is_coach'] = profile.is_coach() and profile.is_approved() 
                context['is_player'] = profile.is_player() and profile.is_approved()
                context['is_approved'] = profile.is_approved()
            except:
                pass
                
        # Get player positions for this lineup
        context['player_positions'] = self.object.player_positions.all().select_related('player', 'position')
        
        # Get available players for this team who aren't already in the lineup
        used_player_ids = self.object.player_positions.values_list('player_id', flat=True)
        context['available_players'] = Player.objects.filter(active=True).exclude(id__in=used_player_ids)
        
        # Get available positions
        context['available_positions'] = LineupPosition.objects.all()
        
        # Get formation templates for quick application
        context['formations'] = FormationTemplate.objects.all()
        
        return context


@login_required
def save_lineup_positions(request, pk):
    """AJAX endpoint to save player positions in a lineup"""
    if not is_coach_or_admin(request.user):
        return JsonResponse({'status': 'error', 'message': 'Permission denied'}, status=403)
    
    lineup = get_object_or_404(Lineup, pk=pk)
    
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            # Log request info for debugging
            print(f"[Save] Saving positions for lineup {pk}, user: {request.user.username}")
            
            data = json.loads(request.body)
            positions = data.get('positions', []) or data.get('playerPositions', [])
            direction = data.get('direction')
            
            # Update direction if specified
            if direction:
                print(f"[Save] Updating direction to {direction}")
                lineup.direction = direction
                lineup.save(update_fields=['direction'])
            
            print(f"[Save] Received {len(positions)} player positions to save")
            
            # Log the position data being received
            for pos in positions:
                print(f"[Save] Player {pos.get('player_id')}: x={pos.get('x')}, y={pos.get('y')}, "
                      f"position_id={pos.get('position_id')}, jersey={pos.get('jersey_number')}")
            
            # Track which players have been processed to handle deletions
            processed_player_ids = []
            
            # Process each position
            for pos in positions:
                try:
                    player_id = pos.get('player_id')
                    if not player_id:
                        print(f"Warning: Missing player_id in position data: {pos}")
                        continue
                        
                    position_id = pos.get('position_id')
                    x = pos.get('x')
                    y = pos.get('y')
                    is_starter = pos.get('is_starter', True)
                    jersey_number = pos.get('jersey_number')
                    notes = pos.get('notes', '')
                    
                    # Ensure we have valid coordinates
                    if x is None or y is None:
                        print(f"Warning: Missing coordinates for player {player_id}: x={x}, y={y}")
                        continue
                        
                    # Validate coordinate values
                    x = max(0, min(100, float(x)))
                    y = max(0, min(100, float(y)))
                    
                    processed_player_ids.append(int(player_id))
                    
                    # Check if this position already exists
                    try:
                        player_position = LineupPlayerPosition.objects.get(
                            lineup=lineup,
                            player_id=player_id
                        )
                        # Update existing position
                        player_position.position_id = position_id
                        player_position.x_coordinate = x
                        player_position.y_coordinate = y
                        player_position.is_starter = is_starter
                        player_position.jersey_number = jersey_number
                        player_position.notes = notes
                        player_position.save()
                        print(f"Updated position for player {player_id} at coordinates ({x}, {y})")
                    except LineupPlayerPosition.DoesNotExist:
                        # Create new position
                        LineupPlayerPosition.objects.create(
                            lineup=lineup,
                            player_id=player_id,
                            position_id=position_id,
                            x_coordinate=x,
                            y_coordinate=y,
                            is_starter=is_starter,
                            jersey_number=jersey_number,
                            notes=notes
                        )
                        print(f"Created new position for player {player_id} at coordinates ({x}, {y})")
                except Exception as e:
                    print(f"Error processing position for player {pos.get('player_id')}: {str(e)}")
            
            # Clear any positions for players who were removed from the lineup
            if processed_player_ids:
                removed = LineupPlayerPosition.objects.filter(lineup=lineup).exclude(player_id__in=processed_player_ids).delete()[0]
                if removed > 0:
                    print(f"Removed {removed} positions for players no longer in the lineup")
            
            # Verify that positions were saved
            position_count = LineupPlayerPosition.objects.filter(lineup=lineup).count()
            print(f"Lineup {pk} now has {position_count} player positions")
            
            return JsonResponse({
                'status': 'success', 
                'message': 'Lineup saved successfully',
                'position_count': position_count
            })
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)


@login_required
def remove_player_from_lineup(request, lineup_id, player_id):
    """Remove a player from a lineup"""
    if not is_coach_or_admin(request.user):
        return JsonResponse({'status': 'error', 'message': 'Permission denied'}, status=403)
    
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            lineup = get_object_or_404(Lineup, pk=lineup_id)
            position = get_object_or_404(LineupPlayerPosition, lineup=lineup, player_id=player_id)
            position.delete()
            
            return JsonResponse({'status': 'success', 'message': 'Player removed from lineup'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)


@login_required
def duplicate_lineup(request, pk):
    """Create a copy of an existing lineup"""
    if not is_coach_or_admin(request.user):
        messages.error(request, "You don't have permission to duplicate lineups.")
        return redirect('lineup-list')
    
    lineup = get_object_or_404(Lineup, pk=pk)
    new_lineup = lineup.duplicate()
    new_lineup.created_by = request.user
    new_lineup.save()
    
    messages.success(request, f"Lineup '{lineup.name}' duplicated successfully.")
    return redirect('lineup-builder', pk=new_lineup.pk)


@login_required
def export_lineup_pdf(request, pk):
    """Export a lineup as PDF with both directions (first and second period)"""
    if not request.user.is_authenticated:
        return redirect('login')
    
    lineup = get_object_or_404(Lineup, pk=pk)
    
    # Create a file-like buffer to receive PDF data
    buffer = io.BytesIO()
    
    # Create the PDF object, using the buffer as its "file"
    p = canvas.Canvas(buffer, pagesize=landscape(A4))
    width, height = landscape(A4)
    
    # Set up the document
    p.setTitle(f"Football Lineup - {lineup.name}")
    
    # Store the original direction
    original_direction = lineup.direction
    
    # Draw the header
    p.setFont("Helvetica-Bold", 18)
    p.drawString(30, height - 30, f"Lineup: {lineup.name}")
    
    # Draw sub-header with more match details if available
    p.setFont("Helvetica", 12)
    if lineup.match:
        match_date = lineup.match.date.strftime("%Y-%m-%d %H:%M")
        location = lineup.match.location or "Unknown location"
        match_type = lineup.match.match_type
        p.drawString(30, height - 50, f"Match: {lineup.team.name} vs {lineup.match.opponent_name}")
        p.drawString(30, height - 70, f"Date: {match_date} | Location: {location} | Type: {match_type}")
    else:
        p.drawString(30, height - 50, "Practice/Template Lineup")
        p.drawString(30, height - 70, f"Team: {lineup.team.name}")
    
    # Draw formation if specified
    if lineup.formation:
        p.drawString(30, height - 90, f"Formation: {lineup.formation.formation_structure}")
    
    # Draw the pitch with clear dimensions and coordinates
    # IMPORTANT: Pitch orientation: Left = Goalkeeper side (x=0), Right = Striker side (x=100%)
    # This matches the orientation in the lineup builder: GK on left, Strikers on right
    # Leave more space at the bottom for text
    pitch_width = width - 150  # Slightly narrower pitch
    pitch_height = height - 180  # More space at bottom
    pitch_x = 50  # Left side of pitch
    pitch_y = 70  # Bottom of pitch - increased to leave more space
    
    # Draw realistic grass pattern
    p.setStrokeColor(colors.darkgreen)
    p.setFillColor(colors.green)
    p.rect(pitch_x, pitch_y, pitch_width, pitch_height, fill=True)
    
    # Add striped pattern for grass effect
    p.setStrokeColor(colors.Color(0, 0.5, 0, 0.1))  # Very light green
    stripe_width = 20
    for i in range(0, int(pitch_height), stripe_width * 2):
        p.rect(pitch_x, pitch_y + i, pitch_width, stripe_width, fill=True, stroke=False)
    
    # Draw pitch markings
    p.setStrokeColor(colors.white)
    p.setFillColor(colors.white)
    
    # Pitch outline
    p.rect(pitch_x, pitch_y, pitch_width, pitch_height, fill=0)
    
    # Center line
    p.line(pitch_x + pitch_width/2, pitch_y, pitch_x + pitch_width/2, pitch_y + pitch_height)
    
    # Center circle
    p.circle(pitch_x + pitch_width/2, pitch_y + pitch_height/2, 50, stroke=1, fill=0)
    p.circle(pitch_x + pitch_width/2, pitch_y + pitch_height/2, 5, fill=1)
    
    # Penalty spots
    p.circle(pitch_x + 60, pitch_y + pitch_height/2, 3, fill=1)
    p.circle(pitch_x + pitch_width - 60, pitch_y + pitch_height/2, 3, fill=1)
    
    # Goal areas (6-yard boxes)
    goal_width = 40
    goal_height = 120
    # Goalkeeper side (left) goal area
    p.rect(pitch_x, pitch_y + (pitch_height - goal_height)/2, goal_width, goal_height, fill=0)
    # Striker side (right) goal area
    p.rect(pitch_x + pitch_width - goal_width, pitch_y + (pitch_height - goal_height)/2, goal_width, goal_height, fill=0)
    
    # Penalty areas (18-yard boxes)
    penalty_width = 80
    penalty_height = 220
    # Goalkeeper side (left) penalty area
    p.rect(pitch_x, pitch_y + (pitch_height - penalty_height)/2, penalty_width, penalty_height, fill=0)
    # Striker side (right) penalty area
    p.rect(pitch_x + pitch_width - penalty_width, pitch_y + (pitch_height - penalty_height)/2, penalty_width, penalty_height, fill=0)
    
    # Draw goals
    p.setFillColor(colors.white)
    goal_post_width = 5
    goal_post_depth = 8
    # Goalkeeper side (left) goal
    p.rect(pitch_x - goal_post_depth, pitch_y + (pitch_height - 80)/2, goal_post_depth, 80, fill=1, stroke=0)
    # Striker side (right) goal
    p.rect(pitch_x + pitch_width, pitch_y + (pitch_height - 80)/2, goal_post_depth, 80, fill=1, stroke=0)
    
    # Get player positions from database, including related data
    player_positions = lineup.player_positions.all().select_related('player', 'position')
    
    # Enhanced debug info to console
    position_count = player_positions.count()
    print(f"[PDF Export] Lineup {lineup.id} has {position_count} player positions")
    
    # Create a list to store player information for both display and debugging
    players_info = []
    for pos in player_positions:
        print(f"[PDF Export] Position ID: {pos.id}, Player: {pos.player.first_name} {pos.player.last_name}, " 
              f"Coords: ({pos.x_coordinate}, {pos.y_coordinate}), "
              f"Position: {pos.position.short_name if pos.position else 'None'}")
        
        # Store player data in standardized format for easier rendering
        players_info.append({
            'id': pos.id,
            'player_id': pos.player.id,
            'name': pos.player.first_name,
            'x': float(pos.x_coordinate),
            'y': float(pos.y_coordinate),
            'is_starter': pos.is_starter,
            'jersey_number': pos.jersey_number,
            'position': pos.position.short_name if pos.position else ''
        })
    
    # Draw message if no players are positioned
    if position_count == 0:
        if lineup.formation:
            print(f"No player positions found, showing formation template: {lineup.formation.formation_structure}")
            # Draw a template formation with placeholder positions
            p.setFont("Helvetica-Bold", 14)
            p.setFillColor(colors.black)
            p.drawCentredString(pitch_x + pitch_width/2, pitch_y + pitch_height/2, 
                               f"Formation: {lineup.formation.formation_structure}")
            p.setFont("Helvetica", 10)
            p.drawCentredString(pitch_x + pitch_width/2, pitch_y + pitch_height/2 - 20, 
                               "No players positioned yet")
            p.drawCentredString(pitch_x + pitch_width/2, pitch_y + pitch_height/2 - 40, 
                               "Open in the Lineup Builder to position players")
        else:
            p.setFont("Helvetica-Bold", 14)
            p.setFillColor(colors.black)
            p.drawCentredString(pitch_x + pitch_width/2, pitch_y + pitch_height/2, 
                               "No formation or player positions defined")
            p.setFont("Helvetica", 10)
            p.drawCentredString(pitch_x + pitch_width/2, pitch_y + pitch_height/2 - 20, 
                               "Open in the Lineup Builder to create a formation")
    
    # Draw each positioned player
    for player in players_info:
        # Convert percentage coordinates to absolute PDF coordinates
        # IMPORTANT: Keep original orientation (GK at left (x=0), strikers at right (x=100))
        # NOTE: We need to flip the y-axis because PDF coordinate system has (0,0) at bottom-left,
        # while the web coordinate system has (0,0) at top-left
        player_x = pitch_x + (player['x'] / 100) * pitch_width
        player_y = pitch_y + pitch_height - ((player['y'] / 100) * pitch_height)  # Flip y-axis
        
        print(f"[PDF Export] Drawing player at coordinates: ({player_x}, {player_y}), Original x: {player['x']}, y: {player['y']}")
        
        # Draw shadow for 3D effect
        p.setFillColor(colors.Color(0, 0, 0, 0.2))
        p.circle(player_x + 2, player_y - 2, 16, fill=1)
        
        # Draw player circle with different colors for starters vs substitutes
        if player['is_starter']:
            p.setFillColor(colors.blue)
        else:
            p.setFillColor(colors.lightblue)
            
        p.circle(player_x, player_y, 15, fill=1)
        
        # Draw jersey number if available
        p.setFillColor(colors.white)
        p.setFont("Helvetica-Bold", 10)
        number = str(player['jersey_number']) if player['jersey_number'] else ""
        p.drawCentredString(player_x, player_y - 4, number)
        
        # Draw player name with white background for better readability
        name_width = p.stringWidth(player['name'], "Helvetica", 8) + 4
        p.setFillColor(colors.white)
        p.rect(player_x - name_width/2, player_y - 30, name_width, 12, fill=1, stroke=0)
        
        p.setFillColor(colors.black)
        p.setFont("Helvetica", 8)
        p.drawCentredString(player_x, player_y - 25, player['name'])
        
        # Draw position if available
        if player['position']:
            p.setFillColor(colors.white)
            position_width = p.stringWidth(player['position'], "Helvetica", 6) + 4
            p.rect(player_x - position_width/2, player_y - 40, position_width, 10, fill=1, stroke=0)
            
            p.setFillColor(colors.darkblue)
            p.setFont("Helvetica", 6)
            p.drawCentredString(player_x, player_y - 35, player['position'])
    
    # Add player list with roles on the side
    # Only show if there are players
    right_col_x = pitch_x + pitch_width + 20
    if players_info:
        # List starters
        starters = [p for p in players_info if p['is_starter']]
        substitutes = [p for p in players_info if not p['is_starter']]
        
        top_y = pitch_y + pitch_height
        current_y = top_y
        
        if starters:
            p.setFont("Helvetica-Bold", 12)
            p.setFillColor(colors.black)
            p.drawString(right_col_x, current_y, "Starting XI")
            current_y -= 20
            
            p.setFont("Helvetica", 9)
            for player in starters:
                jersey = f"#{player['jersey_number']}" if player['jersey_number'] else ""
                pos = f" ({player['position']})" if player['position'] else ""
                p.drawString(right_col_x, current_y, f"{jersey} {player['name']}{pos}")
                current_y -= 15
        
        # Add spacing
        current_y -= 10
        
        if substitutes:
            p.setFont("Helvetica-Bold", 12)
            p.setFillColor(colors.black)
            p.drawString(right_col_x, current_y, "Substitutes")
            current_y -= 20
            
            p.setFont("Helvetica", 9)
            for player in substitutes:
                jersey = f"#{player['jersey_number']}" if player['jersey_number'] else ""
                pos = f" ({player['position']})" if player['position'] else ""
                p.drawString(right_col_x, current_y, f"{jersey} {player['name']}{pos}")
                current_y -= 15
    
    # Add a legend - moved up to avoid text overlap
    p.setFont("Helvetica-Bold", 10)
    p.setFillColor(colors.black)
    p.drawString(pitch_x, 50, "Starting XI")
    p.setFillColor(colors.blue)
    p.circle(pitch_x + 60, 50, 5, fill=1)
    
    p.setFillColor(colors.black)
    p.drawString(pitch_x + 80, 50, "Substitutes")
    p.setFillColor(colors.lightblue)
    p.circle(pitch_x + 150, 50, 5, fill=1)
    
    # Add footer with date and notes - moved up to avoid overlap
    p.setFont("Helvetica", 8)
    p.setFillColor(colors.black)
    p.drawString(pitch_x, 30, f"Generated on {timezone.now().strftime('%Y-%m-%d %H:%M')}")
    p.drawRightString(width - 50, 30, f"Smørås Fotball - G2015")
    
    if lineup.notes:
        p.setFont("Helvetica", 9)
        notes = lineup.notes[:100] + ('...' if len(lineup.notes) > 100 else '')
        p.drawString(pitch_x + 250, 30, f"Notes: {notes}")
    
    # Add text to indicate this is the playing from left direction - placed below pitch
    p.setFont("Helvetica-Bold", 14)
    p.setFillColor(colors.black)
    # Draw with a background box for better visibility
    direction_text = "Playing from Left - Goalkeeper on Left"
    text_width = p.stringWidth(direction_text, "Helvetica-Bold", 14)
    text_height = 16
    margin = 5
    # Draw white background box
    p.setFillColor(colors.white)
    p.rect(pitch_x + (pitch_width/2) - (text_width/2) - margin, 
           pitch_y - 20 - text_height, 
           text_width + (margin*2), 
           text_height + (margin*2), 
           fill=1, stroke=0)
    # Draw text centered below pitch
    p.setFillColor(colors.black)
    p.drawCentredString(pitch_x + (pitch_width/2), pitch_y - 20, direction_text)
    
    # End first page
    p.showPage()
    
    # Start second page with opposite direction
    # Temporarily change lineup direction to the opposite
    lineup.direction = 'RL' if original_direction == 'LR' else 'LR'
    
    # Set up the document - second page
    p.setFont("Helvetica-Bold", 18)
    p.drawString(30, height - 30, f"Lineup: {lineup.name}")
    
    # Draw sub-header with more match details if available
    p.setFont("Helvetica", 12)
    if lineup.match:
        match_date = lineup.match.date.strftime("%Y-%m-%d %H:%M")
        location = lineup.match.location or "Unknown location"
        match_type = lineup.match.match_type
        p.drawString(30, height - 50, f"Match: {lineup.team.name} vs {lineup.match.opponent_name}")
        p.drawString(30, height - 70, f"Date: {match_date} | Location: {location} | Type: {match_type}")
    else:
        p.drawString(30, height - 50, "Practice/Template Lineup")
        p.drawString(30, height - 70, f"Team: {lineup.team.name}")
    
    # Draw formation if specified
    if lineup.formation:
        p.drawString(30, height - 90, f"Formation: {lineup.formation.formation_structure}")
    
    # Add text to indicate this is the playing from right direction - placed below pitch
    p.setFont("Helvetica-Bold", 14)
    p.setFillColor(colors.black)
    # Draw with a background box for better visibility
    direction_text = "Playing from Right - Goalkeeper on Right"
    text_width = p.stringWidth(direction_text, "Helvetica-Bold", 14)
    text_height = 16
    margin = 5
    # Draw white background box
    p.setFillColor(colors.white)
    p.rect(pitch_x + (pitch_width/2) - (text_width/2) - margin, 
           pitch_y - 20 - text_height, 
           text_width + (margin*2), 
           text_height + (margin*2), 
           fill=1, stroke=0)
    # Draw text centered below pitch
    p.setFillColor(colors.black)
    p.drawCentredString(pitch_x + (pitch_width/2), pitch_y - 20, direction_text)
    
    # Draw the pitch with clear dimensions and coordinates
    # Pitch orientation for second period: Left = Striker side, Right = Goalkeeper side
    p.setStrokeColor(colors.darkgreen)
    p.setFillColor(colors.green)
    p.rect(pitch_x, pitch_y, pitch_width, pitch_height, fill=True)
    
    # Add striped pattern for grass effect
    p.setStrokeColor(colors.Color(0, 0.5, 0, 0.1))  # Very light green
    for i in range(0, int(pitch_height), stripe_width * 2):
        p.rect(pitch_x, pitch_y + i, pitch_width, stripe_width, fill=True, stroke=False)
    
    # Draw pitch markings
    p.setStrokeColor(colors.white)
    p.setFillColor(colors.white)
    
    # Pitch outline
    p.rect(pitch_x, pitch_y, pitch_width, pitch_height, fill=0)
    
    # Center line
    p.line(pitch_x + pitch_width/2, pitch_y, pitch_x + pitch_width/2, pitch_y + pitch_height)
    
    # Center circle
    p.circle(pitch_x + pitch_width/2, pitch_y + pitch_height/2, 50, stroke=1, fill=0)
    p.circle(pitch_x + pitch_width/2, pitch_y + pitch_height/2, 5, fill=1)
    
    # Penalty spots
    p.circle(pitch_x + 60, pitch_y + pitch_height/2, 3, fill=1)
    p.circle(pitch_x + pitch_width - 60, pitch_y + pitch_height/2, 3, fill=1)
    
    # Goal areas (6-yard boxes)
    # For second period: right side is goalkeeper side, left side is striker side
    p.rect(pitch_x, pitch_y + (pitch_height - goal_height)/2, goal_width, goal_height, fill=0)
    p.rect(pitch_x + pitch_width - goal_width, pitch_y + (pitch_height - goal_height)/2, goal_width, goal_height, fill=0)
    
    # Penalty areas (18-yard boxes)
    p.rect(pitch_x, pitch_y + (pitch_height - penalty_height)/2, penalty_width, penalty_height, fill=0)
    p.rect(pitch_x + pitch_width - penalty_width, pitch_y + (pitch_height - penalty_height)/2, penalty_width, penalty_height, fill=0)
    
    # Draw goals
    p.setFillColor(colors.white)
    # For second period: left side goal for strikers, right side goal for goalkeeper
    p.rect(pitch_x - goal_post_depth, pitch_y + (pitch_height - 80)/2, goal_post_depth, 80, fill=1, stroke=0)
    p.rect(pitch_x + pitch_width, pitch_y + (pitch_height - 80)/2, goal_post_depth, 80, fill=1, stroke=0)
    
    # Draw each positioned player with flipped x-coordinates for second period
    for player in players_info:
        # Convert percentage coordinates to absolute PDF coordinates
        # For second period: Flip the x-coordinate (100-x)
        # Still flip the y-axis for PDF coordinate system
        player_x = pitch_x + ((100 - player['x']) / 100) * pitch_width  # Flip x-axis for second period
        player_y = pitch_y + pitch_height - ((player['y'] / 100) * pitch_height)  # Flip y-axis
        
        print(f"[PDF Export] Second period: Drawing player at coordinates: ({player_x}, {player_y}), Original x: {player['x']}, y: {player['y']}")
        
        # Draw shadow for 3D effect
        p.setFillColor(colors.Color(0, 0, 0, 0.2))
        p.circle(player_x + 2, player_y - 2, 16, fill=1)
        
        # Draw player circle with different colors for starters vs substitutes
        if player['is_starter']:
            p.setFillColor(colors.blue)
        else:
            p.setFillColor(colors.lightblue)
            
        p.circle(player_x, player_y, 15, fill=1)
        
        # Draw jersey number if available
        p.setFillColor(colors.white)
        p.setFont("Helvetica-Bold", 10)
        number = str(player['jersey_number']) if player['jersey_number'] else ""
        p.drawCentredString(player_x, player_y - 4, number)
        
        # Draw player name with white background for better readability
        name_width = p.stringWidth(player['name'], "Helvetica", 8) + 4
        p.setFillColor(colors.white)
        p.rect(player_x - name_width/2, player_y - 30, name_width, 12, fill=1, stroke=0)
        
        p.setFillColor(colors.black)
        p.setFont("Helvetica", 8)
        p.drawCentredString(player_x, player_y - 25, player['name'])
        
        # Draw position if available
        if player['position']:
            p.setFillColor(colors.white)
            position_width = p.stringWidth(player['position'], "Helvetica", 6) + 4
            p.rect(player_x - position_width/2, player_y - 40, position_width, 10, fill=1, stroke=0)
            
            p.setFillColor(colors.darkblue)
            p.setFont("Helvetica", 6)
            p.drawCentredString(player_x, player_y - 35, player['position'])
    
    # Add player list with roles on the side (same as first page)
    right_col_x = pitch_x + pitch_width + 20
    if players_info:
        # List starters
        starters = [p for p in players_info if p['is_starter']]
        substitutes = [p for p in players_info if not p['is_starter']]
        
        top_y = pitch_y + pitch_height
        current_y = top_y
        
        if starters:
            p.setFont("Helvetica-Bold", 12)
            p.setFillColor(colors.black)
            p.drawString(right_col_x, current_y, "Starting XI")
            current_y -= 20
            
            p.setFont("Helvetica", 9)
            for player in starters:
                jersey = f"#{player['jersey_number']}" if player['jersey_number'] else ""
                pos = f" ({player['position']})" if player['position'] else ""
                p.drawString(right_col_x, current_y, f"{jersey} {player['name']}{pos}")
                current_y -= 15
        
        # Add spacing
        current_y -= 10
        
        if substitutes:
            p.setFont("Helvetica-Bold", 12)
            p.setFillColor(colors.black)
            p.drawString(right_col_x, current_y, "Substitutes")
            current_y -= 20
            
            p.setFont("Helvetica", 9)
            for player in substitutes:
                jersey = f"#{player['jersey_number']}" if player['jersey_number'] else ""
                pos = f" ({player['position']})" if player['position'] else ""
                p.drawString(right_col_x, current_y, f"{jersey} {player['name']}{pos}")
                current_y -= 15
                
    # Add a legend and footer (same as first page)
    p.setFont("Helvetica-Bold", 10)
    p.setFillColor(colors.black)
    p.drawString(pitch_x, 50, "Starting XI")
    p.setFillColor(colors.blue)
    p.circle(pitch_x + 60, 50, 5, fill=1)
    
    p.setFillColor(colors.black)
    p.drawString(pitch_x + 80, 50, "Substitutes")
    p.setFillColor(colors.lightblue)
    p.circle(pitch_x + 150, 50, 5, fill=1)
    
    p.setFont("Helvetica", 8)
    p.setFillColor(colors.black)
    p.drawString(pitch_x, 30, f"Generated on {timezone.now().strftime('%Y-%m-%d %H:%M')}")
    p.drawRightString(width - 50, 30, f"Smørås Fotball - G2015")
    
    # Restore the original direction for the lineup object
    lineup.direction = original_direction
    
    # Close the PDF object cleanly
    p.showPage()
    p.save()
    
    # FileResponse sets the Content-Disposition header so that browsers
    # present the option to save the file
    buffer.seek(0)
    
    # Create the HTTP response
    filename = f"lineup_{lineup.name.replace(' ', '_')}_{timezone.now().strftime('%Y%m%d')}.pdf"
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response


class FormationTemplateListView(LoginRequiredMixin, ListView):
    model = FormationTemplate
    template_name = 'teammanager/formation_list.html'
    context_object_name = 'formations'
    
    def dispatch(self, request, *args, **kwargs):
        if not is_coach_or_admin(request.user):
            messages.error(request, "You don't have permission to manage formations.")
            return redirect('lineup-list')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Pass common user role flags to template
        if self.request.user.is_authenticated:
            try:
                profile = self.request.user.profile
                context['is_admin'] = profile.is_admin() and profile.is_approved()
                context['is_coach'] = profile.is_coach() and profile.is_approved() 
                context['is_player'] = profile.is_player() and profile.is_approved()
                context['is_approved'] = profile.is_approved()
            except:
                pass
                
        return context


class FormationTemplateCreateView(LoginRequiredMixin, CreateView):
    model = FormationTemplate
    form_class = FormationTemplateForm
    template_name = 'teammanager/formation_form.html'
    success_url = reverse_lazy('formation-list')
    
    def dispatch(self, request, *args, **kwargs):
        if not is_coach_or_admin(request.user):
            messages.error(request, "You don't have permission to create formations.")
            return redirect('formation-list')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Pass common user role flags to template
        if self.request.user.is_authenticated:
            try:
                profile = self.request.user.profile
                context['is_admin'] = profile.is_admin() and profile.is_approved()
                context['is_coach'] = profile.is_coach() and profile.is_approved() 
                context['is_player'] = profile.is_player() and profile.is_approved()
                context['is_approved'] = profile.is_approved()
            except:
                pass
                
        return context
    
    def form_valid(self, form):
        messages.success(self.request, "Formation template created successfully.")
        return super().form_valid(form)


class FormationTemplateUpdateView(LoginRequiredMixin, UpdateView):
    model = FormationTemplate
    form_class = FormationTemplateForm
    template_name = 'teammanager/formation_form.html'
    success_url = reverse_lazy('formation-list')
    
    def dispatch(self, request, *args, **kwargs):
        if not is_coach_or_admin(request.user):
            messages.error(request, "You don't have permission to update formations.")
            return redirect('formation-list')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Pass common user role flags to template
        if self.request.user.is_authenticated:
            try:
                profile = self.request.user.profile
                context['is_admin'] = profile.is_admin() and profile.is_approved()
                context['is_coach'] = profile.is_coach() and profile.is_approved() 
                context['is_player'] = profile.is_player() and profile.is_approved()
                context['is_approved'] = profile.is_approved()
            except:
                pass
                
        context['editing'] = True
        
        return context
    
    def form_valid(self, form):
        messages.success(self.request, "Formation template updated successfully.")
        return super().form_valid(form)


class FormationTemplateDeleteView(LoginRequiredMixin, DeleteView):
    model = FormationTemplate
    template_name = 'teammanager/formation_confirm_delete.html'
    success_url = reverse_lazy('formation-list')
    
    def dispatch(self, request, *args, **kwargs):
        if not is_coach_or_admin(request.user):
            messages.error(request, "You don't have permission to delete formations.")
            return redirect('formation-list')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Pass common user role flags to template
        if self.request.user.is_authenticated:
            try:
                profile = self.request.user.profile
                context['is_admin'] = profile.is_admin() and profile.is_approved()
                context['is_coach'] = profile.is_coach() and profile.is_approved() 
                context['is_player'] = profile.is_player() and profile.is_approved()
                context['is_approved'] = profile.is_approved()
            except:
                pass
                
        return context
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, "Formation template deleted successfully.")
        return super().delete(request, *args, **kwargs)


class LineupPositionListView(LoginRequiredMixin, ListView):
    model = LineupPosition
    template_name = 'teammanager/position_list.html'
    context_object_name = 'positions'
    
    def dispatch(self, request, *args, **kwargs):
        if not is_coach_or_admin(request.user):
            messages.error(request, "You don't have permission to manage positions.")
            return redirect('lineup-list')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Pass common user role flags to template
        if self.request.user.is_authenticated:
            try:
                profile = self.request.user.profile
                context['is_admin'] = profile.is_admin() and profile.is_approved()
                context['is_coach'] = profile.is_coach() and profile.is_approved() 
                context['is_player'] = profile.is_player() and profile.is_approved()
                context['is_approved'] = profile.is_approved()
            except:
                pass
                
        return context


class LineupPositionCreateView(LoginRequiredMixin, CreateView):
    model = LineupPosition
    form_class = LineupPositionForm
    template_name = 'teammanager/position_form.html'
    success_url = reverse_lazy('position-list')
    
    def dispatch(self, request, *args, **kwargs):
        if not is_coach_or_admin(request.user):
            messages.error(request, "You don't have permission to create positions.")
            return redirect('position-list')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Pass common user role flags to template
        if self.request.user.is_authenticated:
            try:
                profile = self.request.user.profile
                context['is_admin'] = profile.is_admin() and profile.is_approved()
                context['is_coach'] = profile.is_coach() and profile.is_approved() 
                context['is_player'] = profile.is_player() and profile.is_approved()
                context['is_approved'] = profile.is_approved()
            except:
                pass
                
        return context
    
    def form_valid(self, form):
        messages.success(self.request, "Position created successfully.")
        return super().form_valid(form)


class LineupPositionUpdateView(LoginRequiredMixin, UpdateView):
    model = LineupPosition
    form_class = LineupPositionForm
    template_name = 'teammanager/position_form.html'
    success_url = reverse_lazy('position-list')
    
    def dispatch(self, request, *args, **kwargs):
        if not is_coach_or_admin(request.user):
            messages.error(request, "You don't have permission to update positions.")
            return redirect('position-list')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Pass common user role flags to template
        if self.request.user.is_authenticated:
            try:
                profile = self.request.user.profile
                context['is_admin'] = profile.is_admin() and profile.is_approved()
                context['is_coach'] = profile.is_coach() and profile.is_approved() 
                context['is_player'] = profile.is_player() and profile.is_approved()
                context['is_approved'] = profile.is_approved()
            except:
                pass
                
        context['editing'] = True
        
        return context
    
    def form_valid(self, form):
        messages.success(self.request, "Position updated successfully.")
        return super().form_valid(form)


class LineupPositionDeleteView(LoginRequiredMixin, DeleteView):
    model = LineupPosition
    template_name = 'teammanager/position_confirm_delete.html'
    success_url = reverse_lazy('position-list')
    
    def dispatch(self, request, *args, **kwargs):
        if not is_coach_or_admin(request.user):
            messages.error(request, "You don't have permission to delete positions.")
            return redirect('position-list')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Pass common user role flags to template
        if self.request.user.is_authenticated:
            try:
                profile = self.request.user.profile
                context['is_admin'] = profile.is_admin() and profile.is_approved()
                context['is_coach'] = profile.is_coach() and profile.is_approved() 
                context['is_player'] = profile.is_player() and profile.is_approved()
                context['is_approved'] = profile.is_approved()
            except:
                pass
                
        return context
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, "Position deleted successfully.")
        return super().delete(request, *args, **kwargs)


@login_required
def create_default_positions(request):
    """Create a set of default football positions"""
    if not is_coach_or_admin(request.user):
        messages.error(request, "You don't have permission to create positions.")
        return redirect('position-list')
    
    if request.method != 'POST':
        return redirect('position-list')
    
    # Define default positions
    default_positions = [
        {'name': 'Goalkeeper', 'short_name': 'GK', 'position_type': 'GK'},
        {'name': 'Left Back', 'short_name': 'LB', 'position_type': 'DEF'},
        {'name': 'Center Back', 'short_name': 'CB', 'position_type': 'DEF'},
        {'name': 'Right Back', 'short_name': 'RB', 'position_type': 'DEF'},
        {'name': 'Defensive Midfielder', 'short_name': 'DM', 'position_type': 'MID'},
        {'name': 'Central Midfielder', 'short_name': 'CM', 'position_type': 'MID'},
        {'name': 'Left Midfielder', 'short_name': 'LM', 'position_type': 'MID'},
        {'name': 'Right Midfielder', 'short_name': 'RM', 'position_type': 'MID'},
        {'name': 'Attacking Midfielder', 'short_name': 'AM', 'position_type': 'MID'},
        {'name': 'Left Winger', 'short_name': 'LW', 'position_type': 'FWD'},
        {'name': 'Right Winger', 'short_name': 'RW', 'position_type': 'FWD'},
        {'name': 'Striker', 'short_name': 'ST', 'position_type': 'FWD'},
    ]
    
    # Count how many positions were created
    created_count = 0
    
    # Create positions if they don't already exist
    for pos in default_positions:
        # Check if position with this short_name already exists
        if not LineupPosition.objects.filter(short_name=pos['short_name']).exists():
            LineupPosition.objects.create(
                name=pos['name'],
                short_name=pos['short_name'],
                position_type=pos['position_type']
            )
            created_count += 1
    
    if created_count > 0:
        messages.success(request, f"Successfully created {created_count} default positions.")
    else:
        messages.info(request, "No new positions were created. All default positions already exist.")
    
    return redirect('position-list')