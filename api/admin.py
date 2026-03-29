from django.contrib import admin
from .models import User, Category, Gadget, Rental, Favorite, Notification, ActivityLog

admin.site.register(User)
admin.site.register(Category)
admin.site.register(Gadget)
admin.site.register(Rental)
admin.site.register(Favorite)
admin.site.register(Notification)
admin.site.register(ActivityLog)