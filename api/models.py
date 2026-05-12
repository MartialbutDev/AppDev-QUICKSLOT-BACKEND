from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.exceptions import ValidationError

class User(AbstractUser):
    USER_TYPE_CHOICES = [
        ('student', 'Student'),
        ('faculty', 'Faculty'),
        ('staff', 'Staff'),
        ('admin', 'Admin'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
    ]
    
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default='student')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    student_id = models.CharField(max_length=50, unique=True, null=True, blank=True)
    college = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    total_rentals = models.IntegerField(default=0)
    registered_date = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.username} ({self.get_user_type_display()})"

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    icon = models.CharField(max_length=50, blank=True)
    
    def __str__(self):
        return self.name

class Gadget(models.Model):
    CONDITION_CHOICES = [
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('fair', 'Fair'),
    ]
    
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('rented', 'Rented'),
        ('maintenance', 'Maintenance'),
    ]
    
    name = models.CharField(max_length=200)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    brand = models.CharField(max_length=100, blank=True)
    model = models.CharField(max_length=100, blank=True)
    description = models.TextField()
    specs = models.JSONField(default=list)
    daily_rate = models.DecimalField(max_digits=10, decimal_places=2)
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default='good')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    times_rented = models.IntegerField(default=0)
    # ============ NEW FIELD FOR IMAGE URL ============
    image_url = models.CharField(max_length=500, blank=True, null=True, help_text="URL of the gadget image")
    
    def __str__(self):
        return self.name

class Rental(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('overdue', 'Overdue'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='rentals')
    gadget = models.ForeignKey(Gadget, on_delete=models.CASCADE, related_name='rentals')
    rent_date = models.DateField()
    expected_return = models.DateField()
    actual_return = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    late_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        # Optional: Add constraint to prevent duplicate active rentals for same gadget
        constraints = [
            models.UniqueConstraint(
                fields=['gadget'],
                condition=models.Q(status__in=['pending', 'active', 'overdue']),
                name='unique_active_gadget_rental'
            )
        ]
    
    def clean(self):
        """Validate rental limits before saving"""
        # Check if user already has an active rental for this specific gadget
        if Rental.objects.filter(
            user=self.user,
            gadget=self.gadget,
            status__in=['pending', 'active', 'overdue']
        ).exclude(id=self.id).exists():
            raise ValidationError(f'You already have an active rental for {self.gadget.name}. Please return it first.')
        
        # Check laptop/PC limit (1 per user)
        LIMITED_CATEGORIES = ['Laptop', 'Laptops', 'Gaming PC']
        if self.gadget.category.name in LIMITED_CATEGORIES:
            laptop_rentals = Rental.objects.filter(
                user=self.user,
                gadget__category__name__in=LIMITED_CATEGORIES,
                status__in=['pending', 'active', 'overdue']
            ).exclude(id=self.id).count()
            
            if laptop_rentals >= 1:
                raise ValidationError('You can only rent ONE laptop/PC at a time. Please return your current device before renting another.')
        
        # Check total active rentals limit (max 3)
        MAX_TOTAL_RENTALS = 3
        total_active = Rental.objects.filter(
            user=self.user,
            status__in=['pending', 'active', 'overdue']
        ).exclude(id=self.id).count()
        
        if total_active >= MAX_TOTAL_RENTALS:
            raise ValidationError(f'You have reached the maximum limit of {MAX_TOTAL_RENTALS} active rentals. Please return some items first.')
    
    def save(self, *args, **kwargs):
        self.full_clean()  # Run validation before saving
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Rental {self.id} - {self.gadget.name}"

class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites')
    gadget = models.ForeignKey(Gadget, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'gadget']

class Notification(models.Model):
    TYPE_CHOICES = [
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('success', 'Success'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='info')
    read = models.BooleanField(default=False)
    sent_date = models.DateTimeField(auto_now_add=True)

class ActivityLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    action = models.CharField(max_length=200)
    details = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

# ============ MODEL FOR PUSH NOTIFICATIONS ============

class UserPushToken(models.Model):
    """
    Stores Expo push notification tokens for users
    Allows sending push notifications to mobile devices
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='push_tokens')
    token = models.CharField(max_length=255, unique=True)
    device_name = models.CharField(max_length=100, blank=True, help_text="Optional: Device model or name")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-last_used']
        verbose_name = "User Push Token"
        verbose_name_plural = "User Push Tokens"
    
    def __str__(self):
        return f"{self.user.username} - {self.token[:30]}..."