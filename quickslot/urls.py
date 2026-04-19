from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect  # Add this import 

urlpatterns = [
    path('', lambda request: redirect('admin/')), # Redirect root URL to admin 
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
]