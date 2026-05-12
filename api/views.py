from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from .models import User, Category, Gadget, Rental, Favorite, Notification, ActivityLog, UserPushToken
from .serializers import *
import requests
import os
from django.conf import settings
from rest_framework.parsers import MultiPartParser, FormParser

# ============ AUTHENTICATION ============

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                'user': UserSerializer(user).data,
                'access': str(refresh.access_token),
                'refresh': str(refresh)
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password')
        
        print(f"🔐 Login attempt - username: {username}, email: {email}")
        
        user = None
        
        # Try to find user by username
        if username:
            user = User.objects.filter(username=username).first()
            if not user:
                # Try by student_id
                user = User.objects.filter(student_id=username).first()
                if user:
                    print(f"✅ Found user by student_id: {user.username}")
        
        # Try by email
        if not user and email:
            user = User.objects.filter(email=email).first()
        
        # If still not found, try by email in username field (for mobile app)
        if not user and username and '@' in username:
            user = User.objects.filter(email=username).first()
            if user:
                print(f"✅ Found user by email in username field: {user.username}")
        
        if not user:
            print(f"❌ User not found")
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)
        
        print(f"✅ User found: {user.username}, Status: {user.status}")
        
        # Check password
        if not user.check_password(password):
            print(f"❌ Password incorrect")
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if user is active
        if user.status != 'active':
            print(f"❌ User not active: {user.status}")
            return Response({'error': 'Account not activated. Please wait for admin approval.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Generate token
        refresh = RefreshToken.for_user(user)
        
        print(f"✅ Login successful for: {user.username}")
        
        return Response({
            'user': UserSerializer(user).data,
            'access': str(refresh.access_token),
            'refresh': str(refresh)
        })

# ============ HELPER FUNCTION FOR PUSH NOTIFICATIONS ============

def send_push_notification(user, title, body, data=None):
    """
    Send push notification to a user's registered devices using Expo
    """
    # Get all active push tokens for this user
    push_tokens = UserPushToken.objects.filter(user=user, is_active=True)
    
    if not push_tokens.exists():
        print(f"📱 No push tokens found for user {user.username}")
        return False
    
    # Expo push notification API endpoint
    EXPO_API_URL = 'https://exp.host/--/api/v2/push/send'
    
    # Prepare messages for all tokens
    messages = []
    for token_obj in push_tokens:
        messages.append({
            'to': token_obj.token,
            'sound': 'default',
            'title': title,
            'body': body,
            'data': data or {},
            'priority': 'high',
        })
    
    try:
        response = requests.post(EXPO_API_URL, json=messages, timeout=10)
        response.raise_for_status()
        
        # Check for errors in response
        result = response.json()
        if result.get('data'):
            for item in result['data']:
                if item.get('status') == 'error':
                    print(f"❌ Push error: {item.get('message')}")
                    # If token is invalid, deactivate it
                    if 'DeviceNotRegistered' in item.get('message', ''):
                        token_to_deactivate = item.get('to')
                        UserPushToken.objects.filter(token=token_to_deactivate).update(is_active=False)
        
        print(f"✅ Push notification sent to {user.username}")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to send push notification: {e}")
        return False

# ============ PUSH NOTIFICATION VIEWS ============

class UpdatePushTokenView(APIView):
    """
    Save or update user's Expo push token
    Mobile app calls this after getting the Expo token
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        expo_token = request.data.get('expo_push_token')
        device_name = request.data.get('device_name', '')
        
        if not expo_token:
            return Response({'error': 'expo_push_token is required'}, status=400)
        
        # Update or create token
        token_obj, created = UserPushToken.objects.update_or_create(
            user=request.user,
            token=expo_token,
            defaults={
                'device_name': device_name,
                'is_active': True,
                'last_used': timezone.now()
            }
        )
        
        return Response({
            'status': 'created' if created else 'updated',
            'message': 'Push token saved successfully'
        })
    
    def delete(self, request):
        """Remove push token (called when user logs out)"""
        expo_token = request.data.get('expo_push_token')
        
        if expo_token:
            UserPushToken.objects.filter(user=request.user, token=expo_token).delete()
            return Response({'message': 'Push token removed successfully'})
        
        # If no token specified, deactivate all tokens for this user
        UserPushToken.objects.filter(user=request.user).update(is_active=False)
        return Response({'message': 'All push tokens deactivated'})

class TestPushNotificationView(APIView):
    """
    Test endpoint to send a push notification
    Useful for debugging
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        title = request.data.get('title', 'Test Notification')
        body = request.data.get('body', 'This is a test push notification from QuickSlot!')
        
        success = send_push_notification(request.user, title, body)
        
        if success:
            return Response({'message': 'Test notification sent'})
        else:
            return Response({'error': 'No push tokens found for this user'}, status=404)

# ============ USER MANAGEMENT ============

class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user

class UserListView(generics.ListAPIView):
    """List all users (for admin)"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

class UpdateUserStatusView(APIView):
    """Update user status (approve/suspend/activate)"""
    permission_classes = [permissions.IsAuthenticated]
    
    def put(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            new_status = request.data.get('status')
            
            if new_status in ['pending', 'active', 'suspended']:
                old_status = user.status
                user.status = new_status
                user.save()
                
                # Log activity
                ActivityLog.objects.create(
                    user=request.user,
                    action='User Status Changed',
                    details=f"User {user.username} status changed from {old_status} to {new_status}"
                )
                
                # Send push notification if user becomes active
                if new_status == 'active' and old_status != 'active':
                    send_push_notification(
                        user,
                        "Account Approved! 🎉",
                        "Your QuickSlot account has been activated. You can now rent gadgets!",
                        {'screen': 'explore'}
                    )
                
                return Response({'message': f'User status updated to {new_status}'})
            return Response({'error': 'Invalid status'}, status=400)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)

class PendingUsersView(generics.ListAPIView):
    """Get all pending users"""
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return User.objects.filter(status='pending')

class ChangePasswordView(APIView):
    """Change user password"""
    permission_classes = [permissions.IsAuthenticated]
    
    def put(self, request):
        current_password = request.data.get('current_password')
        new_password = request.data.get('new_password')
        
        user = request.user
        
        if not user.check_password(current_password):
            return Response({'error': 'Current password is incorrect'}, status=400)
        
        if len(new_password) < 6:
            return Response({'error': 'New password must be at least 6 characters'}, status=400)
        
        user.set_password(new_password)
        user.save()
        
        return Response({'message': 'Password changed successfully'})

# ============ GADGET MANAGEMENT ============

class GadgetListView(generics.ListCreateAPIView):
    queryset = Gadget.objects.all()
    serializer_class = GadgetSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        queryset = Gadget.objects.all()
        category = self.request.query_params.get('category')
        status_filter = self.request.query_params.get('status')
        
        if category:
            queryset = queryset.filter(category__name=category)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset

class GadgetDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Gadget.objects.all()
    serializer_class = GadgetSerializer
    permission_classes = [permissions.AllowAny]

class AvailableGadgetsView(generics.ListAPIView):
    """Get all available gadgets"""
    serializer_class = GadgetSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Gadget.objects.filter(status='available')

# ============ IMAGE UPLOAD ============

class UploadGadgetImageView(APIView):
    """Upload image for gadget"""
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request):
        image = request.FILES.get('image')
        if not image:
            return Response({'error': 'No image provided'}, status=400)
        
        # Validate file type
        allowed_types = ['image/jpeg', 'image/png', 'image/jpg']
        if image.content_type not in allowed_types:
            return Response({'error': 'Only JPEG and PNG images are allowed'}, status=400)
        
        # Validate file size (max 5MB)
        if image.size > 5 * 1024 * 1024:
            return Response({'error': 'Image size must be less than 5MB'}, status=400)
        
        try:
            # Create media directory if it doesn't exist
            media_dir = os.path.join(settings.BASE_DIR, 'media', 'gadgets')
            os.makedirs(media_dir, exist_ok=True)
            
            # Generate unique filename
            import time
            file_extension = image.name.split('.')[-1]
            file_name = f"gadget_{request.user.id}_{int(time.time())}.{file_extension}"
            file_path = os.path.join(media_dir, file_name)
            
            # Save file
            with open(file_path, 'wb+') as destination:
                for chunk in image.chunks():
                    destination.write(chunk)
            
            # Return URL
            image_url = f'/media/gadgets/{file_name}'
            
            return Response({
                'image_url': image_url, 
                'success': True,
                'message': 'Image uploaded successfully'
            })
            
        except Exception as e:
            return Response({'error': f'Failed to save image: {str(e)}'}, status=500)

# ============ RENTAL MANAGEMENT ============

class MyRentalsView(generics.ListAPIView):
    serializer_class = RentalSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Rental.objects.filter(user=self.request.user).order_by('-created_at')

class MyRentalDetailView(generics.RetrieveAPIView):
    """Get a specific rental for the authenticated user"""
    serializer_class = RentalSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Rental.objects.filter(user=self.request.user)

class RentalHistoryView(generics.ListAPIView):
    """Get user's rental history (completed/cancelled)"""
    serializer_class = RentalSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Rental.objects.filter(
            user=self.request.user,
            status__in=['completed', 'cancelled']
        ).order_by('-created_at')

# ============ RENTAL CREATE VIEW WITH LIMITS ============
class RentalCreateView(generics.CreateAPIView):
    """Create a new rental with rental limits"""
    serializer_class = RentalSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        # Get gadget ID from request
        gadget_id = request.data.get('gadget')
        
        if not gadget_id:
            return Response({'error': 'Gadget ID is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            gadget = Gadget.objects.get(id=gadget_id)
        except Gadget.DoesNotExist:
            return Response({'error': 'Gadget not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # ============ RENTAL LIMIT CHECKS ============
        
        # 1. Check if gadget is available
        if gadget.status != 'available':
            return Response({'error': 'This gadget is not available for rent'}, status=status.HTTP_400_BAD_REQUEST)
        
        # 2. Check if user already has an active rental for this specific gadget
        existing_rental = Rental.objects.filter(
            user=request.user,
            gadget=gadget,
            status__in=['pending', 'active', 'overdue']
        ).exists()
        
        if existing_rental:
            return Response({
                'error': f'You already have an active rental for {gadget.name}. Please return it first.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 3. Check category limits (Laptop limit: 1 per user)
        # Define categories that have limits
        LIMITED_CATEGORIES = ['Laptop', 'Laptops', 'Gaming PC']
        
        if gadget.category.name in LIMITED_CATEGORIES:
            # Check if user already has any active laptop rental
            laptop_rentals = Rental.objects.filter(
                user=request.user,
                gadget__category__name__in=LIMITED_CATEGORIES,
                status__in=['pending', 'active', 'overdue']
            ).count()
            
            if laptop_rentals >= 1:
                return Response({
                    'error': 'You can only rent ONE laptop/PC at a time. Please return your current device before renting another.'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # 4. Check total active rentals limit (max 3 items total)
        MAX_TOTAL_RENTALS = 3
        total_active = Rental.objects.filter(
            user=request.user,
            status__in=['pending', 'active', 'overdue']
        ).count()
        
        if total_active >= MAX_TOTAL_RENTALS:
            return Response({
                'error': f'You have reached the maximum limit of {MAX_TOTAL_RENTALS} active rentals. Please return some items first.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # ============ END OF LIMIT CHECKS ============
        
        # Prepare rental data
        rental_data = {
            'gadget': gadget.id,
            'rent_date': request.data.get('rent_date'),
            'expected_return': request.data.get('expected_return'),
            'total_amount': request.data.get('total_amount'),
        }
        
        # Validate dates
        if not rental_data['rent_date'] or not rental_data['expected_return']:
            return Response({'error': 'Rent date and expected return date are required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Create serializer with user
        serializer = self.get_serializer(data=rental_data)
        serializer.is_valid(raise_exception=True)
        
        # Save rental with current user
        rental = serializer.save(user=request.user, status='pending')
        
        # Update gadget status
        gadget.status = 'rented'
        gadget.times_rented += 1
        gadget.save()
        
        # Send notification to admin about new rental request
        admins = User.objects.filter(user_type='admin')
        for admin in admins:
            send_push_notification(
                admin,
                "📦 New Rental Request",
                f"{request.user.username} wants to rent {gadget.name}",
                {'screen': 'admin/rentals', 'rental_id': rental.id}
            )
        
        # Return response
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

# ============ USER RENTAL STATUS VIEW ============
class UserRentalStatusView(APIView):
    """Get user's current rental status and limits"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        LIMITED_CATEGORIES = ['Laptop', 'Laptops', 'Gaming PC']
        MAX_TOTAL_RENTALS = 3
        
        active_rentals = Rental.objects.filter(
            user=request.user,
            status__in=['pending', 'active', 'overdue']
        )
        
        laptop_rentals = active_rentals.filter(
            gadget__category__name__in=LIMITED_CATEGORIES
        ).count()
        
        # Get current rentals details
        current_rentals = []
        for rental in active_rentals:
            current_rentals.append({
                'id': rental.id,
                'gadget_name': rental.gadget.name,
                'category': rental.gadget.category.name,
                'rent_date': rental.rent_date,
                'expected_return': rental.expected_return,
                'status': rental.status
            })
        
        return Response({
            'laptop_rentals': laptop_rentals,
            'laptop_limit': 1,
            'total_rentals': active_rentals.count(),
            'total_limit': MAX_TOTAL_RENTALS,
            'can_rent_laptop': laptop_rentals < 1,
            'can_rent_more': active_rentals.count() < MAX_TOTAL_RENTALS,
            'current_rentals': current_rentals
        })

# ============ UPDATE RENTAL STATUS VIEW ============
class UpdateRentalStatusView(APIView):
    """Update rental status (admin only)"""
    permission_classes = [permissions.IsAuthenticated]
    
    def patch(self, request, rental_id):
        try:
            rental = Rental.objects.get(id=rental_id)
            new_status = request.data.get('status')
            
            # Check if user is admin
            if request.user.user_type != 'admin':
                return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
            
            # Valid status transitions
            valid_statuses = ['active', 'cancelled', 'completed']
            if new_status not in valid_statuses:
                return Response({'error': f'Invalid status. Must be one of: {valid_statuses}'}, status=status.HTTP_400_BAD_REQUEST)
            
            old_status = rental.status
            rental.status = new_status
            rental.save()
            
            # If approving, send notification to user
            if new_status == 'active':
                send_push_notification(
                    rental.user,
                    "✅ Rental Approved!",
                    f"Your rental for {rental.gadget.name} has been approved. You can now pick it up.",
                    {'screen': 'orders'}
                )
                print(f"📧 Approval notification sent to {rental.user.username}")
            
            # If rejecting, make gadget available again and notify user
            elif new_status == 'cancelled':
                # Make gadget available again
                gadget = rental.gadget
                gadget.status = 'available'
                gadget.save()
                
                send_push_notification(
                    rental.user,
                    "❌ Rental Declined",
                    f"Your rental request for {rental.gadget.name} was declined. Please contact support.",
                    {'screen': 'explore'}
                )
                print(f"📧 Rejection notification sent to {rental.user.username}")
            
            # Log activity
            ActivityLog.objects.create(
                user=request.user,
                action='Rental Status Updated',
                details=f"Rental #{rental.id} status changed from {old_status} to {new_status}"
            )
            
            return Response({
                'message': f'Rental status updated to {new_status}',
                'status': new_status,
                'rental_id': rental.id
            })
            
        except Rental.DoesNotExist:
            return Response({'error': 'Rental not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ProcessReturnView(APIView):
    """Process return of a rental"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, rental_id):
        try:
            rental = Rental.objects.get(id=rental_id)
            rental.actual_return = timezone.now().date()
            rental.status = 'completed'
            
            # Calculate late fee if applicable
            late_fee = 0
            if rental.actual_return > rental.expected_return:
                days_late = (rental.actual_return - rental.expected_return).days
                late_fee = days_late * 50
                rental.late_fee = late_fee
                rental.total_amount += late_fee
            
            rental.save()
            
            # Update gadget status
            rental.gadget.status = 'available'
            rental.gadget.save()
            
            # Log activity
            ActivityLog.objects.create(
                user=request.user,
                action='Processed Return',
                details=f"Returned {rental.gadget.name} from {rental.user.username}"
            )
            
            # Send push notification to user
            if late_fee > 0:
                notification_body = f"Your rental of {rental.gadget.name} has been returned. Late fee of ₱{late_fee} applied."
            else:
                notification_body = f"Your rental of {rental.gadget.name} has been returned successfully. Thank you!"
            
            send_push_notification(
                rental.user,
                "✅ Rental Returned",
                notification_body,
                {'screen': 'history'}
            )
            
            return Response({'message': 'Return processed successfully'})
        except Rental.DoesNotExist:
            return Response({'error': 'Rental not found'}, status=404)

class AdminRentalListView(generics.ListAPIView):
    """List all rentals for admin"""
    queryset = Rental.objects.all()
    serializer_class = RentalSerializer
    permission_classes = [permissions.IsAuthenticated]

class OverdueRentalsView(generics.ListAPIView):
    """Get all overdue rentals"""
    serializer_class = RentalSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Rental.objects.filter(status='overdue').order_by('expected_return')

# ============ FAVORITES ============

class FavoritesView(generics.ListCreateAPIView):
    serializer_class = FavoriteSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Favorite.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class RemoveFavoriteView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def delete(self, request, gadget_id):
        try:
            favorite = Favorite.objects.get(user=request.user, gadget_id=gadget_id)
            favorite.delete()
            return Response({'message': 'Removed from favorites'})
        except Favorite.DoesNotExist:
            return Response({'error': 'Favorite not found'}, status=404)

# ============ CATEGORIES ============

class CategoryListView(generics.ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]

# ============ DASHBOARD STATS ============

class DashboardStatsView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        stats = {
            'total_users': User.objects.count(),
            'total_gadgets': Gadget.objects.count(),
            'active_rentals': Rental.objects.filter(status='active').count(),
            'available_gadgets': Gadget.objects.filter(status='available').count(),
            'total_revenue': Rental.objects.filter(status='completed').aggregate(
                total=Sum('total_amount')
            )['total'] or 0,
            'monthly_revenue': Rental.objects.filter(
                status='completed',
                created_at__month=timezone.now().month
            ).aggregate(total=Sum('total_amount'))['total'] or 0,
        }
        return Response(stats)

# ============ NOTIFICATIONS ============

class NotificationsView(generics.ListAPIView):
    """Get user's notifications"""
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-sent_date')

class NotificationDetailView(generics.RetrieveUpdateAPIView):
    """Get or update a single notification (mark as read)"""
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # Only allow users to access their own notifications
        return Notification.objects.filter(user=self.request.user)
    
    def perform_update(self, serializer):
        # Ensure the notification belongs to the current user
        notification = self.get_object()
        if notification.user != self.request.user:
            raise PermissionError("You cannot modify this notification")
        serializer.save()

class SendNotificationView(APIView):
    """Send notification to a user (admin only)"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        user_id = request.data.get('user_id')
        title = request.data.get('title')
        message = request.data.get('message')
        notification_type = request.data.get('type', 'info')
        
        try:
            user = User.objects.get(id=user_id)
            notification = Notification.objects.create(
                user=user,
                title=title,
                message=message,
                notification_type=notification_type
            )
            
            # Also send push notification
            send_push_notification(
                user,
                title,
                message,
                {'notification_id': notification.id, 'type': notification_type}
            )
            
            return Response(NotificationSerializer(notification).data)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)

# ============ ACTIVITY LOGS ============

class ActivityLogView(generics.ListAPIView):
    """Get all activity logs (admin only)"""
    queryset = ActivityLog.objects.all().order_by('-timestamp')
    serializer_class = ActivityLogSerializer
    permission_classes = [permissions.IsAuthenticated]

# ============ ANALYTICS ============

class AnalyticsOverviewView(APIView):
    """Get analytics overview"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        today = timezone.now().date()
        
        # User stats
        users_by_type = User.objects.values('user_type').annotate(count=Count('id'))
        
        # Rental stats
        rentals_by_status = Rental.objects.values('status').annotate(count=Count('id'))
        
        # Monthly data (last 6 months)
        last_6_months = []
        for i in range(6):
            month_date = today.replace(day=1) - timedelta(days=30*i)
            month_rentals = Rental.objects.filter(
                rent_date__year=month_date.year,
                rent_date__month=month_date.month
            ).count()
            month_revenue = Rental.objects.filter(
                rent_date__year=month_date.year,
                rent_date__month=month_date.month,
                status='completed'
            ).aggregate(total=Sum('total_amount'))['total'] or 0
            
            last_6_months.append({
                'month': month_date.strftime('%b'),
                'rentals': month_rentals,
                'revenue': month_revenue
            })
        
        return Response({
            'users_by_type': list(users_by_type),
            'rentals_by_status': list(rentals_by_status),
            'monthly_data': last_6_months,
            'total_users': User.objects.count(),
            'total_gadgets': Gadget.objects.count(),
            'total_rentals': Rental.objects.count(),
            'active_rentals': Rental.objects.filter(status='active').count(),
        })