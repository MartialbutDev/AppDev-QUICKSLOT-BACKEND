# main.py
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any
import httpx
from datetime import datetime

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
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ HEALTH CHECK ============

@app.get("/health")
async def health_check():
    """Check if analytics service is running"""
    return {
        "status": "ok",
        "service": "QuickSlot Analytics Dashboard",
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
        "user_info": current_user,
        "timestamp": datetime.now().isoformat()
    }

# ============ RUN SERVER ============
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=True
    )