from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('auth/register/', views.RegisterView.as_view(), name='register'),
    path('auth/login/', views.LoginView.as_view(), name='login'),
    
    # User
    path('users/me/', views.UserProfileView.as_view(), name='user-profile'),
    
    # Categories
    path('categories/', views.CategoryListView.as_view(), name='categories'),
    
    # Gadgets
    path('gadgets/', views.GadgetListView.as_view(), name='gadgets-list'),
    path('gadgets/<int:pk>/', views.GadgetDetailView.as_view(), name='gadget-detail'),
    
    # Rentals
    path('rentals/my-rentals/', views.MyRentalsView.as_view(), name='my-rentals'),
    
    # Favorites
    path('favorites/', views.FavoritesView.as_view(), name='favorites'),
    path('favorites/remove/<int:gadget_id>/', views.RemoveFavoriteView.as_view(), name='remove-favorite'),
    
    # Dashboard
    path('dashboard/stats/', views.DashboardStatsView.as_view(), name='dashboard-stats'),
]