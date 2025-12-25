"""
Backend configuration for Deep Research Agent.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# AWS Configuration
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
BEDROCK_MODEL_ID = os.getenv('BEDROCK_MODEL_ID', 'us.anthropic.claude-3-5-haiku-20241022-v1:0')

# Backend Configuration
BACKEND_PORT = int(os.getenv('BACKEND_PORT', 8001))
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:5173')

# arXiv Configuration
ARXIV_MAX_RESULTS = int(os.getenv('ARXIV_MAX_RESULTS', 5))

# Council Configuration
COUNCIL_NUM_MEMBERS = int(os.getenv('COUNCIL_NUM_MEMBERS', 3))

# CORS Origins
CORS_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://localhost:8000",
    FRONTEND_URL
]

# Data storage
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
CONVERSATIONS_DIR = os.path.join(DATA_DIR, 'conversations')

# Ensure directories exist
os.makedirs(CONVERSATIONS_DIR, exist_ok=True)
