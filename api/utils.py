from datetime import datetime

def is_exam_week():
    """Check if current date is within exam week"""
    exam_weeks = [
        # Format: (start_month, start_day, end_month, end_day)
        (9, 15, 9, 21),   # Midterms September
        (11, 15, 11, 21),  # Finals November
        (2, 15, 2, 21),    # Midterms February
        (4, 15, 4, 21),    # Finals April
    ]
    
    today = datetime.now()
    
    for start_month, start_day, end_month, end_day in exam_weeks:
        start_date = datetime(today.year, start_month, start_day)
        end_date = datetime(today.year, end_month, end_day)
        
        if start_date <= today <= end_date:
            return True
    
    return False

def get_event_priority():
    """Return event priority based on current date"""
    return 10 if is_exam_week() else 7