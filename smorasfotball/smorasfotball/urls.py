"""
URL configuration for smorasfotball project.
"""

from django.contrib import admin
from django.urls import path, include
from django.utils.translation import gettext_lazy as _
from django.views.generic.base import TemplateView
from django.conf.urls.i18n import i18n_patterns
from django.views.i18n import set_language
from django.contrib.auth.views import LoginView

from .views import change_language
from .views_documentation import documentation_index, download_pdf_documentation
from teammanager.views_auth import CustomLoginView

urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
    path('set-language/<str:language>/', change_language, name='change_language'),
    path('rosetta/', include('rosetta.urls')),  # Translation interface
]

# Configure admin site
admin.site.site_header = _('Smørås Fotball Administration')
admin.site.index_title = _('Team Management')
admin.site.site_title = _('Smørås Fotball')

# Add custom auth routes
from teammanager.views_auth import ajax_login

auth_patterns = [
    path('login/', CustomLoginView.as_view(), name='login'),
    path('ajax-login/', ajax_login, name='ajax-login'),  # CSRF-exempt login endpoint
]

# Add remaining auth routes from django.contrib.auth.urls
from django.contrib.auth import views as auth_views
for url_pattern in [
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('password_change/', auth_views.PasswordChangeView.as_view(), name='password_change'),
    path('password_change/done/', auth_views.PasswordChangeDoneView.as_view(), name='password_change_done'),
    path('password_reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
]:
    auth_patterns.append(url_pattern)

urlpatterns += i18n_patterns(
    path('admin/', admin.site.urls),
    path('accounts/', include(auth_patterns)),  # Use our custom auth patterns
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
    path('team/', include('teammanager.urls')),
    path('documentation/', documentation_index, name='documentation'),
    path('documentation/download/', download_pdf_documentation, name='download_documentation'),
    prefix_default_language=False,
)
