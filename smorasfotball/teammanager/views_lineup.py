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
        else:
            messages.success(self.request, "Lineup created successfully.")
        
        return response
    
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
            data = json.loads(request.body)
            positions = data.get('positions', [])
            
            # Process each position
            for pos in positions:
                player_id = pos.get('player_id')
                position_id = pos.get('position_id')
                x = pos.get('x')
                y = pos.get('y')
                is_starter = pos.get('is_starter', True)
                jersey_number = pos.get('jersey_number')
                notes = pos.get('notes', '')
                
                # Validate coordinate values
                x = max(0, min(100, float(x)))
                y = max(0, min(100, float(y)))
                
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
            
            return JsonResponse({'status': 'success', 'message': 'Lineup saved successfully'})
        
        except Exception as e:
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
    """Export a lineup as PDF"""
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
    
    # Draw the header
    p.setFont("Helvetica-Bold", 18)
    p.drawString(30, height - 30, f"Lineup: {lineup.name}")
    
    # Draw sub-header
    p.setFont("Helvetica", 12)
    match_info = f"Match: {lineup.match}" if lineup.match else "Practice/Template Lineup"
    p.drawString(30, height - 50, match_info)
    p.drawString(30, height - 70, f"Team: {lineup.team.name}")
    
    # Draw the pitch
    pitch_width = width - 100
    pitch_height = height - 150
    p.setStrokeColor(colors.darkgreen)
    p.setFillColor(colors.green)
    p.rect(50, 50, pitch_width, pitch_height, fill=True)
    
    # Draw pitch markings
    p.setStrokeColor(colors.white)
    p.setFillColor(colors.white)
    
    # Center line
    p.line(50 + pitch_width/2, 50, 50 + pitch_width/2, 50 + pitch_height)
    
    # Center circle
    p.circle(50 + pitch_width/2, 50 + pitch_height/2, 50, stroke=1, fill=0)
    
    # Penalty spots
    p.circle(50 + 60, 50 + pitch_height/2, 3, fill=1)
    p.circle(50 + pitch_width - 60, 50 + pitch_height/2, 3, fill=1)
    
    # Goal areas (6-yard boxes) - properly oriented
    goal_width = 40
    goal_height = 120
    # Left goal area
    p.rect(50, 50 + (pitch_height - goal_height)/2, goal_width, goal_height, fill=0)
    # Right goal area
    p.rect(50 + pitch_width - goal_width, 50 + (pitch_height - goal_height)/2, goal_width, goal_height, fill=0)
    
    # Penalty areas (18-yard boxes)
    penalty_width = 80
    penalty_height = 220
    # Left penalty area
    p.rect(50, 50 + (pitch_height - penalty_height)/2, penalty_width, penalty_height, fill=0)
    # Right penalty area
    p.rect(50 + pitch_width - penalty_width, 50 + (pitch_height - penalty_height)/2, penalty_width, penalty_height, fill=0)
    
    # Draw goals
    p.setFillColor(colors.white)
    goal_post_width = 5
    goal_post_depth = 8
    # Left goal
    p.rect(50 - goal_post_depth, 50 + (pitch_height - 80)/2, goal_post_depth, 80, fill=1, stroke=0)
    # Right goal
    p.rect(50 + pitch_width, 50 + (pitch_height - 80)/2, goal_post_depth, 80, fill=1, stroke=0)
    
    # Draw players
    player_positions = lineup.player_positions.all().select_related('player', 'position')
    
    # Debug info to console
    print(f"Lineup {lineup.id} has {player_positions.count()} player positions")
    
    # If there are no saved positions but lineup has a formation, create default positions
    if player_positions.count() == 0 and lineup.formation:
        print(f"No player positions found, applying default formation: {lineup.formation.formation_structure}")
        # In this case we'll display a placeholder setup based on the formation
        formation_string = lineup.formation.formation_structure
        layers = formation_string.split('-')
        
        # Draw a template formation with placeholder positions
        p.setFont("Helvetica-Bold", 14)
        p.setFillColor(colors.black)
        p.drawCentredString(50 + pitch_width/2, 50 + pitch_height/2, 
                           f"Formation: {formation_string} (No players positioned yet)")
        p.setFont("Helvetica", 10)
        p.drawCentredString(50 + pitch_width/2, 50 + pitch_height/2 - 20, 
                           "Open in the Lineup Builder to position players")
    
    # Draw each positioned player
    for pos in player_positions:
        # Make sure we have valid coordinates
        if pos.x_coordinate is None or pos.y_coordinate is None:
            print(f"Invalid coordinates for player position {pos.id}, player {pos.player.id}")
            continue
            
        player_x = 50 + (pos.x_coordinate / 100) * pitch_width
        player_y = 50 + (pos.y_coordinate / 100) * pitch_height
        
        # Draw player circle
        p.setFillColor(colors.blue if pos.is_starter else colors.lightblue)
        p.circle(player_x, player_y, 15, fill=1)
        
        # Draw jersey number if available
        p.setFillColor(colors.white)
        p.setFont("Helvetica-Bold", 10)
        number = str(pos.jersey_number) if pos.jersey_number else ""
        p.drawCentredString(player_x, player_y - 4, number)
        
        # Draw player name
        p.setFillColor(colors.black)
        p.setFont("Helvetica", 8)
        p.drawCentredString(player_x, player_y - 25, str(pos.player.first_name))
        
        # Draw position if available
        if pos.position:
            p.setFont("Helvetica-Oblique", 6)
            p.drawCentredString(player_x, player_y - 35, pos.position.short_name)
    
    # Add a legend
    p.setFont("Helvetica-Bold", 10)
    p.setFillColor(colors.black)
    p.drawString(50, 30, "Starting XI")
    p.setFillColor(colors.blue)
    p.circle(80, 30, 5, fill=1)
    
    p.setFillColor(colors.black)
    p.drawString(100, 30, "Substitutes")
    p.setFillColor(colors.lightblue)
    p.circle(150, 30, 5, fill=1)
    
    # Add footer with date
    p.setFont("Helvetica", 8)
    p.setFillColor(colors.black)
    p.drawString(50, 10, f"Generated on {timezone.now().strftime('%Y-%m-%d %H:%M')}")
    p.drawRightString(width - 50, 10, f"Smørås Fotball - G2015")
    
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