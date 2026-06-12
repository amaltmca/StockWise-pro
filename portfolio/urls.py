from django.urls import path
from . import views

urlpatterns = [
    # Core pages
    path('', views.home_view, name='home'), # <-- Home URL pattern
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),
    path('about/', views.about_view, name='about'),
    path('explore/', views.explore_view, name='explore'),
    path('risk/', views.risk_analysis_view, name='risk_analysis'),

    # Goals
    path('goals/', views.goal_tracker_view, name='goal_tracker'),
    path('goals/edit/<int:pk>/', views.edit_goal, name='edit_goal'),
    path('goals/delete/<int:pk>/', views.delete_goal, name='delete_goal'),

    # Stock Detail
    path('stock/<int:pk>/', views.stock_detail_view, name='stock_detail_view'),

    # Alerts and Notifications
    path('alerts/', views.manage_alerts_view, name='manage_alerts'),
    path('notifications/read/<int:pk>/', views.mark_notification_read, name='mark_notification_read'),

    # Download Reports
    path('download/csv/', views.download_csv_view, name='download_csv'),
    path('download/pdf/', views.download_pdf_view, name='download_pdf'),

    # Authentication (App-specific URLs)
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    # Note: Password reset URLs are typically included from django.contrib.auth.urls in the project's main urls.py

    # Stock CRUD
    path('add/', views.add_stock, name='add_stock'),
    path('edit/<int:pk>/', views.edit_stock, name='edit_stock'),
    path('delete/<int:pk>/', views.delete_stock, name='delete_stock'),

    # API
    path('api/search-ticker/', views.search_ticker_api, name='search_ticker_api'),
    path('predictive-analytics/', views.predictive_analytics, name='predictive_analytics'),
    path('sector-analysis/', views.sector_analysis, name='sector_analysis'),
    path('stock/<str:ticker>/', views.stock_detail, name='stock_detail'),
    path('stock/<str:ticker>/analyze/', views.stock_mlr_analysis, name='stock_mlr_analysis'),
    path('stock/<str:ticker>/knn/', views.stock_knn_analysis, name='stock_knn_analysis'),
]
