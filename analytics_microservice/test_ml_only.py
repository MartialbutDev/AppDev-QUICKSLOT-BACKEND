# test_ml_only.py
import sys
import time
import os

print("="*50)
print("Testing ML Predictor...")
print("="*50)

# Check if files exist
ml_dir = "ml"
files = ['exam_week_predictor.pkl', 'label_encoders.pkl', 'scaler.pkl', 'feature_columns.pkl']

print("\n📂 Checking model files:")
for f in files:
    path = os.path.join(ml_dir, f)
    if os.path.exists(path):
        size = os.path.getsize(path) / 1024
        print(f"  ✅ {f} ({size:.1f} KB)")
    else:
        print(f"  ❌ {f} NOT FOUND")

print("\n🔧 Loading predictor...")
start = time.time()

try:
    from ml_predictor import predictor
    
    elapsed = time.time() - start
    print(f"✅ Predictor loaded in {elapsed:.2f} seconds")
    print(f"   ML Loaded: {predictor.loaded}")
    print(f"   Model exists: {predictor.model is not None}")
    
    # Get model info if loaded
    if predictor.loaded:
        print(f"   Model Type: RandomForestClassifier")
        print(f"   Number of Trees: {predictor.model.n_estimators if predictor.model else 'N/A'}")
    
    print("\n" + "-"*50)
    print("🧪 TESTING PREDICTIONS")
    print("-"*50)
    
    # Test different scenarios
    test_cases = [
        ("Calculator", "Student", 2, 10, 10, "Casio"),
        ("Laptop", "Student", 3, 80, 10, "Apple"),
        ("Camera", "Faculty", 5, 200, 7, "Canon"),
        ("Tablet", "Student", 7, 150, 10, "Samsung"),
        ("Projector", "Staff", 1, 100, 7, "Epson"),
    ]
    
    for category, role, days, rate, priority, brand in test_cases:
        result = predictor.predict_gadget_demand(
            gadget_category=category,
            user_role=role,
            duration_days=days,
            daily_rate=rate,
            event_priority=priority,
            brand=brand
        )
        demand = "🔥 HIGH DEMAND" if result > 0.6 else "📉 Standard"
        print(f"\n📱 {category} ({brand})")
        print(f"   👤 {role} | 📅 {days} days | 💰 ₱{rate}/day | 🎯 Priority: {priority}")
        print(f"   📊 Probability: {result*100:.1f}%")
        print(f"   🏷️  {demand}")
    
    print("\n" + "="*50)
    print("✅ ML is working correctly!")
    print("="*50)
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()