# config.py
import os

# From your Django settings.py
SECRET_KEY = 'django-insecure-your-secret-key-change-this-in-production'
ALGORITHM = "HS256"

# FastAPI server
FASTAPI_HOST = "0.0.0.0"
FASTAPI_PORT = 8001

# Redis (optional - we can run without it first)
REDIS_HOST = "localhost"
REDIS_PORT = 6379