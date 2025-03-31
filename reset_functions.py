@csrf_exempt
def reset_match_time(request, pk):
    """Reset the match time to the beginning of the current period"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=405)
    
    match_session = get_object_or_404(MatchSession, pk=pk)
    
    if not is_coach_or_admin(request.user):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    if not match_session.is_active:
        return JsonResponse({'error': 'Match is not active'}, status=400)
    
    # Reset time by updating start_time to now
    match_session.start_time = timezone.now()
    match_session.save()
    
    return JsonResponse({'success': True})

@csrf_exempt
def reset_substitution_timer(request, pk):
    """Reset the substitution timer"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=405)
    
    match_session = get_object_or_404(MatchSession, pk=pk)
    
    if not is_coach_or_admin(request.user):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    if not match_session.is_active:
        return JsonResponse({'error': 'Match is not active'}, status=400)
    
    # We don't need to reset anything in the database
    # The substitution timer is calculated based on the current time
    # Just return success and let the frontend know to restart its calculations
    
    return JsonResponse({'success': True, 'reset_time': timezone.now().isoformat()})

@csrf_exempt
def set_match_period(request, pk):
    """Manually set the match period"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=405)
    
    match_session = get_object_or_404(MatchSession, pk=pk)
    
    if not is_coach_or_admin(request.user):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        data = json.loads(request.body)
        period = int(data.get('period', 1))
        
        if period < 1 or period > match_session.periods:
            return JsonResponse({'error': f'Period must be between 1 and {match_session.periods}'}, status=400)
        
        # Calculate elapsed time from previous periods
        elapsed_time = 0
        if period > 1:
            # Each previous period contributes period_length minutes to elapsed time
            elapsed_time = (period - 1) * match_session.period_length * 60
        
        # Update match session
        match_session.current_period = period
        match_session.elapsed_time = elapsed_time
        match_session.save()
        
        return JsonResponse({'success': True, 'current_period': period, 'elapsed_time': elapsed_time})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)