from django.contrib.auth import authenticate, login
from django.contrib.auth.views import LoginView
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse_lazy, reverse
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.utils.decorators import method_decorator
from django.middleware.csrf import get_token
import json

class CustomLoginView(LoginView):
    """Enhanced login view that adds improved CSRF token handling for Replit environment"""
    
    template_name = 'registration/login.html'
    redirect_authenticated_user = True
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Ensure CSRF token is available in the context
        # This is already done by Django, but we're making it explicit
        if 'csrf_token' not in context:
            context['csrf_token'] = get_token(self.request)
            
        return context
    
    def form_invalid(self, form):
        """If the form is invalid, add more detailed error information."""
        # If there's a CSRF-related error, add a more specific message
        if '__all__' in form.errors and any('CSRF' in error for error in form.errors['__all__']):
            form.add_error(None, 'CSRF verification failed. Please try refreshing the page and logging in again.')
            # Add a debug message about the issue
            print(f"CSRF error detected. Request headers: {self.request.headers}")
            
        return super().form_invalid(form)
    
    def get(self, request, *args, **kwargs):
        """Override get to add additional headers for CSRF troubleshooting."""
        response = super().get(request, *args, **kwargs)
        # Add CORS headers to help with CSRF issues
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type, X-CSRFToken'
        return response
    
    def post(self, request, *args, **kwargs):
        """Override post to add additional headers and debugging."""
        print(f"Login POST request received. Headers: {request.headers}")
        try:
            response = super().post(request, *args, **kwargs)
            # Add CORS headers to help with CSRF issues
            response['Access-Control-Allow-Origin'] = '*'
            response['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
            response['Access-Control-Allow-Headers'] = 'Content-Type, X-CSRFToken'
            return response
        except Exception as e:
            print(f"Error in login POST: {e}")
            # Provide error context
            context = self.get_context_data()
            context['error_message'] = f"An error occurred: {e}"
            return self.render_to_response(context)


@csrf_exempt
def ajax_login(request):
    """
    Alternative login endpoint that doesn't use CSRF protection.
    This is only used as a fallback when the regular login doesn't work.
    """
    if request.method == 'POST':
        try:
            if request.content_type == 'application/json':
                data = json.loads(request.body)
                username = data.get('username')
                password = data.get('password')
            else:
                username = request.POST.get('username')
                password = request.POST.get('password')
                
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                login(request, user)
                return JsonResponse({
                    'success': True, 
                    'redirect': reverse('home')
                })
            else:
                return JsonResponse({
                    'success': False, 
                    'error': 'Invalid credentials'
                })
        except Exception as e:
            return JsonResponse({
                'success': False, 
                'error': str(e)
            })
    
    return JsonResponse({
        'success': False, 
        'error': 'Only POST requests are allowed'
    })