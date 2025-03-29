from django.shortcuts import redirect
from django.conf import settings
from django.utils.translation import activate
from django.http import HttpResponse
import logging

logger = logging.getLogger(__name__)

def change_language(request, language):
    """Change the language and redirect back to the previous page."""
    referer = request.META.get('HTTP_REFERER', '/')
    
    # Log the language change request for debugging
    logger.info(f"Language change requested to: {language}")
    logger.info(f"Referer: {referer}")
    
    # Check if the language is supported
    supported = False
    for lang_code, lang_name in settings.LANGUAGES:
        if lang_code == language:
            supported = True
            break
    
    if not supported:
        logger.warning(f"Unsupported language: {language}")
        return redirect(referer)
    
    # Set the language
    activate(language)
    response = redirect(referer)
    
    # Ensure we set a proper cookie with the language
    response.set_cookie(
        settings.LANGUAGE_COOKIE_NAME, 
        language,
        max_age=365 * 24 * 60 * 60,  # Set cookie for 1 year
        path='/',
        secure=request.is_secure(),
        httponly=False,
        samesite='Lax'
    )
    
    logger.info(f"Language changed to: {language}")
    
    return response