# analytics_microservice/ml_predictor.py
import joblib
import pandas as pd
import numpy as np
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# Get the directory of this file
BASE_DIR = Path(__file__).resolve().parent
ML_DIR = BASE_DIR / 'ml'

class ExamWeekPredictor:
    """ML Predictor for Exam Week gadget demand using RandomForest"""
    
    def __init__(self):
        self.model = None
        self.label_encoders = None
        self.scaler = None
        self.feature_columns = None
        self.loaded = False
        self.load_models()
    
    def load_models(self):
        """Load all trained models"""
        try:
            # Check if ML directory exists
            if not ML_DIR.exists():
                print(f"⚠️ ML directory not found at {ML_DIR}")
                return
            
            # Load model
            model_path = ML_DIR / 'exam_week_predictor.pkl'
            if model_path.exists():
                self.model = joblib.load(model_path)
                print(f"✅ RandomForest model loaded from {model_path}")
                self.loaded = True
            else:
                print(f"⚠️ Model file not found: {model_path}")
                return
            
            # Load label encoders
            encoder_path = ML_DIR / 'label_encoders.pkl'
            if encoder_path.exists():
                self.label_encoders = joblib.load(encoder_path)
                print(f"✅ Label encoders loaded")
            
            # Load scaler
            scaler_path = ML_DIR / 'scaler.pkl'
            if scaler_path.exists():
                self.scaler = joblib.load(scaler_path)
                print(f"✅ Scaler loaded")
                # Check what features the scaler expects
                if hasattr(self.scaler, 'feature_names_in_'):
                    print(f"   Scaler expects: {self.scaler.feature_names_in_}")
            
            # Load feature columns
            features_path = ML_DIR / 'feature_columns.pkl'
            if features_path.exists():
                self.feature_columns = joblib.load(features_path)
                print(f"✅ Feature columns loaded: {self.feature_columns}")
            
            print(f"🎯 ML Model ready! Using RandomForest with {self.model.n_estimators if self.model else 0} trees")
            
        except Exception as e:
            print(f"❌ Error loading ML models: {e}")
            self.loaded = False
    
    def _get_current_datetime_features(self) -> Dict[str, Any]:
        """Get current date/time features for prediction"""
        now = datetime.now()
        
        # Day of week
        day_of_week = now.strftime('%A')
        
        # Month - convert to month name for encoder
        month_names = ['January', 'February', 'March', 'April', 'May', 'June', 
                       'July', 'August', 'September', 'October', 'November', 'December']
        month_name = month_names[now.month - 1]
        
        # Season based on month (Philippines context)
        if now.month in [11, 12, 1, 2, 3, 4]:
            season = 'Dry'
        else:
            season = 'Rainy'
        
        # Calculate days until next exam week
        days_until_event = self._calculate_days_until_exam_week()
        
        return {
            'day_of_week': day_of_week,
            'month': month_name,
            'season': season,
            'days_until_event': days_until_event
        }
    
    def _calculate_days_until_exam_week(self) -> int:
        """Calculate days until next exam week"""
        EXAM_WEEKS = [
            (9, 15, 9, 21),   # Midterms September
            (11, 15, 11, 21), # Finals November
            (2, 15, 2, 21),   # Midterms February
            (4, 15, 4, 21),   # Finals April
        ]
        
        today = datetime.now()
        min_days = 365
        
        for start_month, start_day, end_month, end_day in EXAM_WEEKS:
            try:
                start_date = datetime(today.year, start_month, start_day)
                if start_date > today:
                    days = (start_date - today).days
                    min_days = min(min_days, days)
                
                # Also check if currently IN exam week
                end_date = datetime(today.year, end_month, end_day)
                if start_date <= today <= end_date:
                    return 0
            except ValueError:
                continue
        
        return min_days if min_days < 365 else 30
    
    def _determine_price_tier(self, daily_rate: float) -> str:
        """Determine price tier based on daily rate"""
        if daily_rate < 100:
            return 'Budget'
        elif daily_rate < 300:
            return 'Mid-range'
        else:
            return 'Premium'
    
    def _encode_categorical(self, encoder_name: str, value: str) -> int:
        """Safely encode categorical value"""
        try:
            encoder = self.label_encoders.get(encoder_name)
            if encoder is None:
                print(f"⚠️ Encoder '{encoder_name}' not found")
                return 0
            
            # Check if value exists in encoder classes
            if value in encoder.classes_:
                return int(encoder.transform([value])[0])  # Convert to Python int
            else:
                # Try to find a default/fallback value
                print(f"⚠️ Value '{value}' not in {encoder_name} encoder classes")
                return 0
        except Exception as e:
            print(f"⚠️ Error encoding {encoder_name}='{value}': {e}")
            return 0
    
    def _prepare_features(self, gadget_category: str, user_role: str, 
                          brand: str, duration_days: int, 
                          daily_rate: float, event_priority: int) -> np.ndarray:
        """Prepare features array in the exact order expected by the model"""
        
        # Get current datetime features
        datetime_features = self._get_current_datetime_features()
        
        # Determine price tier
        price_tier = self._determine_price_tier(daily_rate)
        
        # Encode all categorical features (convert to Python ints)
        user_role_encoded = self._encode_categorical('user_role', user_role)
        gadget_category_encoded = self._encode_categorical('gadget_category', gadget_category)
        brand_encoded = self._encode_categorical('brand', brand)
        day_of_week_encoded = self._encode_categorical('day_of_week', datetime_features['day_of_week'])
        month_encoded = self._encode_categorical('month', datetime_features['month'])
        season_encoded = self._encode_categorical('season', datetime_features['season'])
        price_tier_encoded = self._encode_categorical('price_tier', price_tier)
        
        # Numerical features (convert to Python floats)
        days_until_event = float(datetime_features['days_until_event'])
        
        # Create features array in the exact order from feature_columns.pkl
        features = np.array([[
            float(user_role_encoded),
            float(gadget_category_encoded),
            float(brand_encoded),
            float(day_of_week_encoded),
            float(month_encoded),
            float(season_encoded),
            float(price_tier_encoded),
            float(duration_days),
            float(daily_rate),
            float(event_priority),
            days_until_event
        ]])
        
        return features
    
    def _scale_numerical_features(self, features: np.ndarray) -> np.ndarray:
        """Scale only the numerical features (indices 7, 8, 9, 10)"""
        if self.scaler is None:
            return features
        
        # The scaler was trained on 4 features: duration_days, daily_rate, event_priority, days_until_event
        # Extract these 4 numerical features
        numerical_features = features[:, 7:11]  # indices 7,8,9,10
        
        # Scale them
        numerical_scaled = self.scaler.transform(numerical_features)
        
        # Replace the original numerical features with scaled ones
        features_scaled = features.copy()
        features_scaled[:, 7:11] = numerical_scaled
        
        return features_scaled
    
    def predict_gadget_demand(self, gadget_category: str, user_role: str, 
                               duration_days: int, daily_rate: float, 
                               event_priority: int = 7,
                               brand: str = "Generic") -> float:
        """
        Predict demand probability for a gadget during Exam Week
        
        Returns:
            float: Probability between 0 and 1 (0% to 100%)
        """
        
        # ============ USE RANDOMFOREST MODEL ============
        if self.loaded and self.model is not None:
            try:
                # Prepare features
                features = self._prepare_features(
                    gadget_category=gadget_category,
                    user_role=user_role,
                    brand=brand,
                    duration_days=duration_days,
                    daily_rate=daily_rate,
                    event_priority=event_priority
                )
                
                # Scale numerical features only
                if self.scaler is not None:
                    features_scaled = self._scale_numerical_features(features)
                else:
                    features_scaled = features
                
                # Predict probability of high demand (class 1)
                probability = self.model.predict_proba(features_scaled)[0][1]
                
                # Convert to Python float and round to 2 decimal places
                probability = float(round(probability, 2))
                
                print(f"🤖 ML Prediction: {gadget_category} -> {probability*100:.1f}% demand probability")
                
                return probability
                
            except Exception as e:
                print(f"❌ ML prediction failed: {e}")
                print("   Falling back to rule-based prediction...")
        
        # ============ RULE-BASED FALLBACK ============
        return self._rule_based_prediction(
            gadget_category=gadget_category,
            user_role=user_role,
            duration_days=duration_days,
            daily_rate=daily_rate,
            event_priority=event_priority
        )
    
    def _rule_based_prediction(self, gadget_category: str, user_role: str,
                                duration_days: int, daily_rate: float, 
                                event_priority: int) -> float:
        """Rule-based fallback when ML model is unavailable"""
        base_prob = 0.50
        
        # Category impact
        high_demand_categories = ['Calculator', 'Laptop', 'Laptops']
        if gadget_category in high_demand_categories:
            base_prob += 0.15
        
        # Event priority impact
        if event_priority >= 8:
            base_prob += 0.10
        
        # Student vs Faculty
        if user_role == 'Student':
            base_prob += 0.05
        
        # Duration impact
        if duration_days <= 3:
            base_prob += 0.05
        elif duration_days > 7:
            base_prob -= 0.05
        
        # Price impact
        if daily_rate <= 50:
            base_prob += 0.05
        elif daily_rate >= 300:
            base_prob -= 0.05
        
        probability = max(0.05, min(base_prob, 0.95))
        
        return float(round(probability, 2))
    
    def get_recommendations(self, gadgets_data: List[Dict]) -> List[Dict]:
        """Get exam week recommendations for multiple gadgets using ML model"""
        recommendations = []
        
        is_exam, _ = self._is_exam_week()
        event_priority = 10 if is_exam else 7
        
        for gadget in gadgets_data:
            gadget_id = gadget.get('gadget_id') or gadget.get('id')
            gadget_name = gadget.get('gadget_name') or gadget.get('name')
            gadget_category = gadget.get('gadget_category') or gadget.get('category')
            gadget_brand = gadget.get('brand') or 'Generic'
            
            if not gadget_category:
                print(f"⚠️ Skipping gadget with no category: {gadget}")
                continue
            
            probability = self.predict_gadget_demand(
                gadget_category=gadget_category,
                user_role=gadget.get('user_role', 'Student'),
                duration_days=gadget.get('duration_days', 3),
                daily_rate=float(gadget.get('daily_rate', 100)),
                event_priority=gadget.get('event_priority', event_priority),
                brand=gadget_brand
            )
            
            display_name = gadget_name or gadget_category
            
            # Convert probability to Python float and bools to Python bool
            probability = float(probability)
            
            recommendations.append({
                'gadget_id': gadget_id,
                'gadget_name': display_name,
                'gadget_category': gadget_category,
                'exam_week_probability': probability,
                'is_high_demand': bool(probability > 0.6),
                'demand_level': 'High' if probability > 0.6 else 'Standard',
                'recommendation_label': '🔥 High Demand' if probability > 0.6 else '📉 Standard Demand'
            })
        
        recommendations.sort(key=lambda x: x['exam_week_probability'], reverse=True)
        
        return recommendations
    
    def _is_exam_week(self, date=None) -> tuple:
        """Check if given date falls within exam week"""
        if date is None:
            date = datetime.now()
        
        EXAM_WEEKS = [
            {'month': 9, 'start_day': 15, 'end_day': 21, 'name': 'Midterms (1st Sem)'},
            {'month': 11, 'start_day': 15, 'end_day': 21, 'name': 'Finals (1st Sem)'},
            {'month': 2, 'start_day': 15, 'end_day': 21, 'name': 'Midterms (2nd Sem)'},
            {'month': 4, 'start_day': 15, 'end_day': 21, 'name': 'Finals (2nd Sem)'},
        ]
        
        for exam_week in EXAM_WEEKS:
            try:
                start_date = datetime(date.year, exam_week['month'], exam_week['start_day'])
                end_date = datetime(date.year, exam_week['month'], exam_week['end_day'])
                
                if start_date <= date <= end_date:
                    return True, exam_week
            except ValueError:
                continue
        
        return False, None
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model"""
        info = {
            'loaded': self.loaded,
            'model_type': 'RandomForestClassifier' if self.model else None,
            'n_estimators': self.model.n_estimators if self.model else None,
            'feature_columns': list(self.feature_columns) if self.feature_columns is not None else None,
        }
        
        if self.label_encoders:
            info['encoders'] = list(self.label_encoders.keys())
        
        return info


# Create singleton instance
predictor = ExamWeekPredictor()

# Print model status on startup
if predictor.loaded:
    print("\n" + "="*50)
    print("🎯 ML PREDICTOR STATUS: ACTIVE")
    print("="*50)
    model_info = predictor.get_model_info()
    print(f"📊 Model Type: {model_info['model_type']}")
    print(f"🌲 Number of Trees: {model_info['n_estimators']}")
    print(f"📋 Features: {len(model_info['feature_columns'])} features")
    print(f"🔧 Encoders: {model_info['encoders']}")
    print("="*50 + "\n")
else:
    print("\n" + "="*50)
    print("⚠️ ML PREDICTOR STATUS: FALLBACK MODE")
    print("="*50)
    print("Using rule-based predictions. ML model not loaded.")
    print("="*50 + "\n")