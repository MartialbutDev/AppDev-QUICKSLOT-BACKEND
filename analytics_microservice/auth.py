# auth.py
from jose import JWTError, jwt
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from config import SECRET_KEY, ALGORITHM

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token from Django"""
    token = credentials.credentials
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        user_type = payload.get("user_type")
        
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
            
        return {"id": user_id, "type": user_type}
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")