from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView # <-- Import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # All your app's main URLs (dashboard, logout, etc.)
    path('portfolio/', include('portfolio.urls')),

    # --- ADD THIS ROOT REDIRECT ---
    # Redirect the site root "/" to the app's home page "/portfolio/"
    path('', RedirectView.as_view(url='/portfolio/', permanent=True)),

    # --- Manually add ONLY the password reset URLs ---
    path(
        'accounts/password_reset/', 
        auth_views.PasswordResetView.as_view(), 
        name='password_reset'
    ),
    path(
        'accounts/password_reset/done/', 
        auth_views.PasswordResetDoneView.as_view(), 
        name='password_reset_done'
    ),
    path(
        'accounts/password_reset_confirm/<uidb64>/<token>/', 
        auth_views.PasswordResetConfirmView.as_view(), 
        name='password_reset_confirm'
    ),
    path(
        'accounts/password_reset_complete/', 
        auth_views.PasswordResetCompleteView.as_view(), 
        name='password_reset_complete'
    ),
]