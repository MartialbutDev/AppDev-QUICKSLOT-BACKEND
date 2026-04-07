from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User, Category, Gadget, Rental, Favorite, Notification, ActivityLog

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name',
                  'user_type', 'status', 'student_id', 'college', 'phone',
                  'total_rentals', 'registered_date']

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'first_name', 'last_name', 
                  'student_id', 'user_type', 'college', 'phone']
    
    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()
    
    def validate(self, data):
        user = authenticate(**data)
        if user and user.is_active:
            return user
        raise serializers.ValidationError("Invalid credentials")

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'icon']

class GadgetSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = Gadget
        fields = ['id', 'name', 'category', 'category_name', 'brand', 'model',
                  'description', 'specs', 'daily_rate', 'condition', 'status', 'times_rented']

class RentalSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    gadget_name = serializers.CharField(source='gadget.name', read_only=True)
    
    class Meta:
        model = Rental
        fields = ['id', 'user', 'user_name', 'gadget', 'gadget_name', 'rent_date',
                  'expected_return', 'actual_return', 'status', 'total_amount',
                  'late_fee', 'created_at']

class FavoriteSerializer(serializers.ModelSerializer):
    gadget_details = GadgetSerializer(source='gadget', read_only=True)
    
    class Meta:
        model = Favorite
        fields = ['id', 'gadget', 'gadget_details', 'added_at']

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'notification_type', 'read', 'sent_date']

# ============ ADD THIS NEW SERIALIZER ============

class ActivityLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = ActivityLog
        fields = ['id', 'user', 'user_name', 'action', 'details', 'timestamp']