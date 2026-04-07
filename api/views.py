from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta
from .models import User, Category, Gadget, Rental, Favorite, Notification, ActivityLog
from .serializers import *

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
                user.status = new_status
                user.save()
                
                # Log activity
                ActivityLog.objects.create(
                    user=request.user,
                    action='User Status Changed',
                    details=f"User {user.username} status changed to {new_status}"
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

# ============ RENTAL MANAGEMENT ============

class MyRentalsView(generics.ListAPIView):
    serializer_class = RentalSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Rental.objects.filter(user=self.request.user).order_by('-created_at')

class RentalHistoryView(generics.ListAPIView):
    """Get user's rental history (completed/cancelled)"""
    serializer_class = RentalSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Rental.objects.filter(
            user=self.request.user,
            status__in=['completed', 'cancelled']
        ).order_by('-created_at')

class RentalCreateView(generics.CreateAPIView):
    """Create a new rental"""
    serializer_class = RentalSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        gadget = serializer.validated_data['gadget']
        gadget.status = 'rented'
        gadget.times_rented += 1
        gadget.save()
        serializer.save(user=self.request.user, status='active')

class ProcessReturnView(APIView):
    """Process return of a rental"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, rental_id):
        try:
            rental = Rental.objects.get(id=rental_id)
            rental.actual_return = timezone.now().date()
            rental.status = 'completed'
            
            # Calculate late fee if applicable
            if rental.actual_return > rental.expected_return:
                days_late = (rental.actual_return - rental.expected_return).days
                rental.late_fee = days_late * 50
                rental.total_amount += rental.late_fee
            
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