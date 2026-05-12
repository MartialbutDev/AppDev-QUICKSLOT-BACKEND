# api/ml_views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
import httpx
import asyncio

class MLRecommendationView(APIView):
    """Get ML recommendations for Exam Week via FastAPI"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Get parameters from request
        gadget_category = request.query_params.get('category', 'Laptop')
        user_role = request.user.user_type
        event_priority = request.query_params.get('priority', 10)
        
        # Call FastAPI ML service synchronously
        import requests
        try:
            response = requests.get(
                "http://localhost:8001/api/ml/exam-week-predict",
                params={
                    'gadget_category': gadget_category,
                    'user_role': user_role,
                    'duration_days': 3,
                    'daily_rate': 100,
                    'event_priority': event_priority
                },
                timeout=10
            )
            
            if response.status_code == 200:
                return Response(response.json())
            else:
                return Response({'error': 'ML service error'}, status=500)
                
        except Exception as e:
            return Response({'error': str(e), 'message': 'ML service unavailable'}, status=503)

class MLAllRecommendationsView(APIView):
    """Get all gadget ML recommendations"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            import requests
            response = requests.get(
                "http://localhost:8001/api/ml/recommendations",
                timeout=10
            )
            
            if response.status_code == 200:
                return Response(response.json())
            else:
                return Response({'error': 'ML service error'}, status=500)
                
        except Exception as e:
            return Response({'error': str(e), 'message': 'ML service unavailable'}, status=503)

class MLBatchPredictView(APIView):
    """Batch predict for multiple categories"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        categories = request.query_params.get('categories', 'Laptop,Calculator,Camera')
        
        try:
            import requests
            response = requests.get(
                "http://localhost:8001/api/ml/batch-predict",
                params={'categories': categories},
                timeout=10
            )
            
            if response.status_code == 200:
                return Response(response.json())
            else:
                return Response({'error': 'ML service error'}, status=500)
                
        except Exception as e:
            return Response({'error': str(e), 'message': 'ML service unavailable'}, status=503)