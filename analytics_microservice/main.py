# main.py
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, Optional
import httpx
from datetime import datetime
from ml_predictor import predictor

from auth import get_current_user

# Create FastAPI app
app = FastAPI(
    title="QuickSlot Analytics Dashboard",
    description="Real-time analytics for QuickSlot Rental System",
    version="1.0.0"
)

# CORS - allow frontend to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",      # React Web
        "http://localhost:8081",      # React Native
        "http://127.0.0.1:3000",
        "http://192.168.1.63:3000",
        "http://192.168.1.63:8081",
        "exp://192.168.1.63:8081",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ EXAM WEEK DETECTION ============
# Define Exam Week date ranges
EXAM_WEEKS = [
    # 1st Semester
    {'month': 9, 'start_day': 15, 'end_day': 21, 'name': 'Midterms (1st Sem)', 'priority': 10},
    {'month': 11, 'start_day': 15, 'end_day': 21, 'name': 'Finals (1st Sem)', 'priority': 10},
    # 2nd Semester
    {'month': 2, 'start_day': 15, 'end_day': 21, 'name': 'Midterms (2nd Sem)', 'priority': 10},
    # UPDATED: Changed from April (4) to May (5) for Finals
    {'month': 5, 'start_day': 19, 'end_day': 25, 'name': 'Finals (2nd Sem)', 'priority': 10},
]

NORMAL_DAY_PRIORITY = 7
EXAM_WEEK_PRIORITY = 10

def is_exam_week(date=None):
    """Check if given date (or current date) falls within exam week"""
    if date is None:
        date = datetime.now()
    
    for exam_week in EXAM_WEEKS:
        try:
            start_date = datetime(date.year, exam_week['month'], exam_week['start_day'])
            end_date = datetime(date.year, exam_week['month'], exam_week['end_day'])
            
            if start_date <= date <= end_date:
                return True, exam_week
        except ValueError:
            continue
    
    return False, None

def get_current_event_priority():
    """Get the current event priority based on date"""
    is_exam, exam_week = is_exam_week()
    return EXAM_WEEK_PRIORITY if is_exam else NORMAL_DAY_PRIORITY

def get_current_exam_week_name():
    """Get the name of the current exam week if applicable"""
    is_exam, exam_week = is_exam_week()
    return exam_week['name'] if is_exam else None

# ============ HEALTH CHECK ============

@app.get("/health")
async def health_check():
    """Check if analytics service is running"""
    return {
        "status": "ok",
        "service": "QuickSlot Analytics Dashboard",
        "timestamp": datetime.now().isoformat()
    }

# ============ EXAM WEEK STATUS ENDPOINT ============

@app.get("/api/exam-week/status")
async def get_exam_week_status():
    """Get current exam week status"""
    is_exam, exam_week = is_exam_week()
    current_priority = get_current_event_priority()
    
    # Convert numpy.bool to Python bool for JSON serialization
    is_exam = bool(is_exam)
    
    return {
        "is_exam_week": is_exam,
        "event_priority": current_priority,
        "exam_week_name": exam_week['name'] if exam_week else None,
        "normal_priority": NORMAL_DAY_PRIORITY,
        "exam_priority": EXAM_WEEK_PRIORITY,
        "current_date": datetime.now().isoformat(),
        "exam_weeks_schedule": EXAM_WEEKS,
        "timestamp": datetime.now().isoformat()
    }

# ============ SIMPLE TEST ENDPOINT (No Auth) ============

@app.get("/api/test")
async def test_endpoint():
    """Simple test endpoint - no authentication required"""
    return {
        "message": "FastAPI is working!",
        "status": "online",
        "timestamp": datetime.now().isoformat()
    }

# ============ REALTIME STATS (No Auth for testing) ============

@app.get("/api/analytics/realtime")
async def get_realtime_stats():
    """Get real-time stats - no authentication for testing"""
    return {
        "active_rentals": 42,
        "available_gadgets": 15,
        "total_gadgets": 20,
        "total_users": 50,
        "revenue_today": 1250.00,
        "timestamp": datetime.now().isoformat()
    }

# ============ PROTECTED ENDPOINT (Requires JWT) ============

@app.get("/api/analytics/protected")
async def protected_endpoint(current_user: dict = Depends(get_current_user)):
    """Test protected endpoint - requires valid JWT token"""
    return {
        "message": "You are authenticated!",
        "user": current_user,
        "timestamp": datetime.now().isoformat()
    }

# ============ FULL ANALYTICS (Requires Admin) ============

@app.get("/api/analytics/overview")
async def get_analytics_overview(current_user: dict = Depends(get_current_user)):
    """Get complete analytics overview - requires admin"""
    
    # Check if user is admin
    if current_user.get("type") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Try to get data from Django
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Call Django dashboard stats
            response = await client.get("http://localhost:8000/api/dashboard/stats/")
            django_stats = response.json() if response.status_code == 200 else {}
    except:
        django_stats = {}
    
    # Convert numpy.bool to Python bool
    is_exam_val = bool(is_exam_week()[0])
    
    # Return analytics data
    return {
        "overview": {
            "total_users": django_stats.get("total_users", 50),
            "total_gadgets": django_stats.get("total_gadgets", 20),
            "active_rentals": django_stats.get("active_rentals", 5),
            "available_gadgets": django_stats.get("available_gadgets", 15),
            "total_revenue": django_stats.get("total_revenue", 0),
            "monthly_revenue": django_stats.get("monthly_revenue", 0),
        },
        "exam_week_status": {
            "is_exam_week": is_exam_val,
            "event_priority": get_current_event_priority()
        },
        "user_info": current_user,
        "timestamp": datetime.now().isoformat()
    }

# ============ ML ENDPOINTS ============

@app.get("/api/ml/exam-week-predict")
async def predict_exam_week_demand(
    gadget_category: str = "Laptop",
    user_role: str = "Student",
    duration_days: int = 3,
    daily_rate: float = 100,
    event_priority: Optional[int] = None
):
    """
    Predict if a gadget will have high demand during Exam Week
    
    Parameters:
    - gadget_category: Laptop, Calculator, Camera, Tablet, Projector
    - user_role: Student, Faculty, Staff
    - duration_days: Expected rental duration in days
    - daily_rate: Rental price per day
    - event_priority: Event importance (1-10, Exam Week = 7-10)
                  If not provided, auto-detects based on current date
    """
    # Auto-detect exam week if priority not provided
    if event_priority is None:
        event_priority = get_current_event_priority()
    
    is_exam, exam_week = is_exam_week()
    
    # Convert numpy.bool to Python bool for JSON serialization
    is_exam = bool(is_exam)
    
    probability = predictor.predict_gadget_demand(
        gadget_category=gadget_category,
        user_role=user_role,
        duration_days=duration_days,
        daily_rate=daily_rate,
        event_priority=event_priority
    )
    
    # Convert probability to regular float
    probability = float(probability)
    
    return {
        "gadget_category": gadget_category,
        "user_role": user_role,
        "duration_days": duration_days,
        "daily_rate": daily_rate,
        "event_priority": event_priority,
        "is_exam_week": is_exam,
        "exam_week_name": exam_week['name'] if exam_week else None,
        "exam_week_probability": probability,
        "is_high_demand": bool(probability > 0.6),
        "recommendation": "🔥 High Demand - Recommended for Exam Week" if probability > 0.6 else "📉 Standard demand",
        "timestamp": datetime.now().isoformat()
    }

# ============ FIXED: Get Exam Week Recommendations ============
@app.get("/api/ml/recommendations")
async def get_exam_week_recommendations():
    """
    Get Exam Week recommendations for all gadgets
    Calls Django API to get gadget data and returns top recommendations
    """
    try:
        # Get gadgets from Django API
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get("http://localhost:8000/api/gadgets/")
            
            if response.status_code == 200:
                data = response.json()
                
                # Handle paginated response (Django REST framework format)
                if isinstance(data, dict) and 'results' in data:
                    gadgets = data['results']
                elif isinstance(data, list):
                    gadgets = data
                else:
                    gadgets = []
                
                # Get current event priority (auto-detect exam week)
                event_priority = get_current_event_priority()
                is_exam, exam_week = is_exam_week()
                
                # Convert numpy.bool to Python bool
                is_exam = bool(is_exam)
                
                # Prepare data for prediction
                gadgets_data = []
                for gadget in gadgets:
                    # Safely get values with fallbacks
                    gadget_id = gadget.get('id')
                    gadget_name = gadget.get('name')
                    category = gadget.get('category_name') or gadget.get('category', 'Laptop')
                    daily_rate = gadget.get('daily_rate', 0)
                    
                    # Skip if no valid data
                    if not gadget_name:
                        continue
                    
                    gadgets_data.append({
                        'gadget_id': gadget_id,
                        'gadget_name': gadget_name,
                        'gadget_category': category,
                        'daily_rate': float(daily_rate) if daily_rate else 0,
                        'user_role': 'Student',
                        'duration_days': 3,
                        'event_priority': event_priority
                    })
                
                # Get predictions
                recommendations = predictor.get_recommendations(gadgets_data)
                
                return {
                    "status": "success",
                    "is_exam_week": is_exam,
                    "exam_week_name": exam_week['name'] if exam_week else None,
                    "event_priority": event_priority,
                    "count": len(recommendations),
                    "recommendations": recommendations[:10],
                    "message": "Top Exam Week recommendations" if is_exam else "Regular recommendations",
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to fetch gadgets from Django: {response.status_code}",
                    "timestamp": datetime.now().isoformat()
                }
                
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }

# ============ FIXED: Get Category Recommendations ============
@app.get("/api/ml/recommendations/{gadget_category}")
async def get_category_recommendations(gadget_category: str):
    """
    Get Exam Week predictions for a specific category
    
    Parameters:
    - gadget_category: Laptop, Calculator, Camera, Tablet, Projector
    """
    event_priority = get_current_event_priority()
    is_exam, exam_week = is_exam_week()
    
    # Convert numpy.bool to Python bool
    is_exam = bool(is_exam)
    
    probability = predictor.predict_gadget_demand(
        gadget_category=gadget_category,
        user_role="Student",
        duration_days=3,
        daily_rate=100,
        event_priority=event_priority
    )
    
    # Convert probability to regular float
    probability = float(probability)
    
    # Get all gadgets of this category from Django
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get("http://localhost:8000/api/gadgets/")
            
            if response.status_code == 200:
                data = response.json()
                
                # Handle paginated response
                if isinstance(data, dict) and 'results' in data:
                    gadgets = data['results']
                elif isinstance(data, list):
                    gadgets = data
                else:
                    gadgets = []
                
                # Filter by category
                category_gadgets = [g for g in gadgets if (g.get('category_name') or g.get('category')) == gadget_category]
                
                # Calculate demand level based on probability
                demand_level = "High" if probability > 0.6 else "Normal"
                
                return {
                    "status": "success",
                    "category": gadget_category,
                    "is_exam_week": is_exam,
                    "exam_week_name": exam_week['name'] if exam_week else None,
                    "event_priority": event_priority,
                    "exam_week_demand_probability": probability,
                    "is_high_demand": bool(probability > 0.6),
                    "demand_level": demand_level,
                    "gadgets_count": len(category_gadgets),
                    "recommendation": "📦 Consider stocking more items" if probability > 0.6 else "✅ Standard stock levels are sufficient",
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "status": "partial",
                    "category": gadget_category,
                    "is_exam_week": is_exam,
                    "exam_week_demand_probability": probability,
                    "is_high_demand": bool(probability > 0.6),
                    "gadgets_count": 0,
                    "recommendation": "High demand expected during Exam Week" if probability > 0.6 else "📉 Standard demand expected",
                    "timestamp": datetime.now().isoformat()
                }
                
    except Exception as e:
        return {
            "status": "error",
            "category": gadget_category,
            "exam_week_demand_probability": probability,
            "is_high_demand": bool(probability > 0.6),
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/api/ml/batch-predict")
async def batch_predict(
    categories: Optional[str] = None
):
    """
    Batch prediction for multiple gadget categories
    
    Parameters:
    - categories: Comma-separated list of categories (e.g., "Laptop,Calculator,Camera")
    """
    if categories:
        category_list = [c.strip() for c in categories.split(',')]
    else:
        category_list = ['Laptop', 'Calculator', 'Camera', 'Tablet', 'Projector']
    
    # Get current event priority (auto-detect exam week)
    event_priority = get_current_event_priority()
    is_exam, exam_week = is_exam_week()
    
    # Convert numpy.bool to Python bool
    is_exam = bool(is_exam)
    
    results = []
    for category in category_list:
        probability = predictor.predict_gadget_demand(
            gadget_category=category,
            user_role="Student",
            duration_days=3,
            daily_rate=100,
            event_priority=event_priority
        )
        # Convert probability to regular float
        probability = float(probability)
        results.append({
            "category": category,
            "exam_week_probability": probability,
            "is_high_demand": bool(probability > 0.6),
            "demand_level": "High" if probability > 0.6 else "Standard"
        })
    
    return {
        "status": "success",
        "is_exam_week": is_exam,
        "exam_week_name": exam_week['name'] if exam_week else None,
        "event_priority": event_priority,
        "categories_analyzed": len(results),
        "high_demand_categories": [r for r in results if r["is_high_demand"]],
        "results": results,
        "timestamp": datetime.now().isoformat()
    }

# ============ RUN SERVER ============
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=False
    )