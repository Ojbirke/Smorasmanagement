"""
URL configuration for smorasfotball project.
"""

from django.contrib import admin
from django.urls import path, include
from django.utils.translation import gettext_lazy as _
from django.views.generic.base import TemplateView
from django.conf.urls.i18n import i18n_patterns
from django.views.i18n import set_language

from .views import change_language

urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
    path('set-language/<str:language>/', change_language, name='change_language'),
    path('rosetta/', include('rosetta.urls')),  # Translation interface
]

# Configure admin site
admin.site.site_header = _('Smørås Fotball Administration')
admin.site.index_title = _('Team Management')
admin.site.site_title = _('Smørås Fotball')

urlpatterns += i18n_patterns(
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
    path('team/', include('teammanager.urls')),
    prefix_default_language=False,
)
