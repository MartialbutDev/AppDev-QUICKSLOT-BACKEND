# api/urls.py
from django.urls import path
from . import views
from .ml_views import MLRecommendationView, MLAllRecommendationsView, MLBatchPredictView

urlpatterns = [
    # Auth
    path('auth/register/', views.RegisterView.as_view(), name='register'),
    path('auth/login/', views.LoginView.as_view(), name='login'),
    
    # User Management
    path('users/me/', views.UserProfileView.as_view(), name='user-profile'),
    path('users/', views.UserListView.as_view(), name='user-list'),
    path('users/<int:user_id>/status/', views.UpdateUserStatusView.as_view(), name='update-user-status'),
    path('users/pending/', views.PendingUsersView.as_view(), name='pending-users'),
    path('user/change-password/', views.ChangePasswordView.as_view(), name='change-password'),
    
    # Push Token
    path('users/update-push-token/', views.UpdatePushTokenView.as_view(), name='update-push-token'),
    path('notifications/test/', views.TestPushNotificationView.as_view(), name='test-notification'),
    
    # Categories
    path('categories/', views.CategoryListView.as_view(), name='categories'),
    
    # Gadgets
    path('gadgets/', views.GadgetListView.as_view(), name='gadgets-list'),
    path('gadgets/<int:pk>/', views.GadgetDetailView.as_view(), name='gadget-detail'),
    path('gadgets/available/', views.AvailableGadgetsView.as_view(), name='available-gadgets'),
    
    # ============ IMAGE UPLOAD ============
    path('upload-gadget-image/', views.UploadGadgetImageView.as_view(), name='upload-gadget-image'),
    
    # Rentals
    path('rentals/my-rentals/', views.MyRentalsView.as_view(), name='my-rentals'),
    path('rentals/my-rentals/<int:pk>/', views.MyRentalDetailView.as_view(), name='my-rental-detail'),
    path('rentals/history/', views.RentalHistoryView.as_view(), name='rental-history'),
    path('rentals/create/', views.RentalCreateView.as_view(), name='rental-create'),
    path('rentals/<int:rental_id>/status/', views.UpdateRentalStatusView.as_view(), name='update-rental-status'),
    path('rentals/process-return/<int:rental_id>/', views.ProcessReturnView.as_view(), name='process-return'),
    
    # ============ USER RENTAL STATUS (for mobile app limits) ============
    path('user/rental-status/', views.UserRentalStatusView.as_view(), name='user-rental-status'),
    
    # Favorites
    path('favorites/', views.FavoritesView.as_view(), name='favorites'),
    path('favorites/remove/<int:gadget_id>/', views.RemoveFavoriteView.as_view(), name='remove-favorite'),
    
    # Dashboard
    path('dashboard/stats/', views.DashboardStatsView.as_view(), name='dashboard-stats'),
    
    # Notifications
    path('notifications/', views.NotificationsView.as_view(), name='notifications'),
    path('notifications/<int:pk>/', views.NotificationDetailView.as_view(), name='notification-detail'),
    path('notifications/send/', views.SendNotificationView.as_view(), name='send-notification'),
    
    # Activity Logs
    path('admin/activities/', views.ActivityLogView.as_view(), name='activities'),
    
    # Analytics
    path('analytics/overview/', views.AnalyticsOverviewView.as_view(), name='analytics-overview'),
    
    # Admin Rentals
    path('admin/rentals/', views.AdminRentalListView.as_view(), name='admin-rentals'),
    path('admin/rentals/overdue/', views.OverdueRentalsView.as_view(), name='overdue-rentals'),
    
    # ============ ML ENDPOINTS ============
    path('ml/predict/', MLRecommendationView.as_view(), name='ml-predict'),
    path('ml/recommendations/', MLAllRecommendationsView.as_view(), name='ml-recommendations'),
    path('ml/batch-predict/', MLBatchPredictView.as_view(), name='ml-batch-predict'),
]