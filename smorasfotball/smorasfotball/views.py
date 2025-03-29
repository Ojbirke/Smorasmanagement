from django.shortcuts import redirect
from django.conf import settings
from django.utils.translation import activate

def change_language(request, language):
    """Change the language and redirect back to the previous page."""
    # Check if the language is supported
    for lang_code, lang_name in settings.LANGUAGES:
        if lang_code == language:
            activate(language)
            response = redirect(request.META.get('HTTP_REFERER', '/'))
            response.set_cookie(settings.LANGUAGE_COOKIE_NAME, language)
            return response
    
    # If language not found, redirect back with no changes
    return redirect(request.META.get('HTTP_REFERER', '/'))