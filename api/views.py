from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.db.models import Sum, Count
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
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data
            refresh = RefreshToken.for_user(user)
            return Response({
                'user': UserSerializer(user).data,
                'access': str(refresh.access_token),
                'refresh': str(refresh)
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# ============ USER MANAGEMENT ============

class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user

# ============ GADGET MANAGEMENT ============

class GadgetListView(generics.ListCreateAPIView):
    queryset = Gadget.objects.all()
    serializer_class = GadgetSerializer
    permission_classes = [permissions.AllowAny]  # Public access for now
    
    def get_queryset(self):
        queryset = Gadget.objects.all()
        category = self.request.query_params.get('category')
        status = self.request.query_params.get('status')
        
        if category:
            queryset = queryset.filter(category__name=category)
        if status:
            queryset = queryset.filter(status=status)
        return queryset

class GadgetDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Gadget.objects.all()
    serializer_class = GadgetSerializer
    permission_classes = [permissions.AllowAny]  # Public access for now

# ============ RENTAL MANAGEMENT ============

class MyRentalsView(generics.ListAPIView):
    serializer_class = RentalSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Rental.objects.filter(user=self.request.user).order_by('-created_at')

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
        }
        return Response(stats)