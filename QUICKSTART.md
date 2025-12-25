# Quick Start Guide - 5 Minutes to Running Demo

This guide gets you from zero to running demo in 5 minutes.

## Prerequisites Check

```bash
# Check Python (need 3.11+)
python --version

# Check Node.js (need 18+)
node --version

# Check AWS CLI
aws --version

# Check Docker (optional)
docker --version
```

## Option 1: Docker (Easiest - 2 Minutes)

**Step 1**: Configure AWS credentials

```bash
cp .env.example .env

# Edit .env and add:
# AWS_ACCESS_KEY_ID=your_key
# AWS_SECRET_ACCESS_KEY=your_secret
```

**Step 2**: Start everything

```bash
docker-compose up --build
```

**Step 3**: Open browser

```
http://localhost:5173
```

Done! 🎉

---

## Option 2: Manual Setup (5 Minutes)

### Step 1: AWS Bedrock Access

1. Go to AWS Console → Bedrock → Model access
2. Enable "Claude Opus 4.5" (anthropic.claude-opus-4-5-20251101-v1:0)
3. Wait ~2 minutes for approval

### Step 2: Backend Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Configure AWS
cp .env.example .env
# Edit .env with your AWS credentials

# Start backend
python -m backend.main
```

Keep this terminal open. Backend runs on port 8001.

### Step 3: Frontend Setup

**New terminal:**

```bash
cd frontend

# Install dependencies
npm install

# Start frontend
npm run dev
```

Keep this terminal open. Frontend runs on port 5173.

### Step 4: Test It

1. Open: `http://localhost:5173`
2. Click "LLM Council"
3. Ask: "What are the key challenges in quantum computing?"
4. Watch the 3-stage deliberation!

---

## Quick Test Commands

### Health Check

```bash
curl http://localhost:8001/health
```

Should return:
```json
{"status": "healthy", "aws_region": "us-east-1", ...}
```

### Test Council API

```bash
curl -X POST http://localhost:8001/api/council \
  -H "Content-Type: application/json" \
  -d '{"question": "What is quantum computing?", "mode": "council"}'
```

### Test DxO API

```bash
curl -X POST http://localhost:8001/api/dxo \
  -H "Content-Type: application/json" \
  -d '{"question": "Quantum error correction", "mode": "dxo"}'
```

---

## Common Issues

### "Access Denied" Error

**Cause**: AWS Bedrock model not enabled

**Fix**:
1. AWS Console → Bedrock → Model access
2. Enable Claude Opus 4.5
3. Wait 2 minutes

### "Connection Refused" Error

**Cause**: Backend not running

**Fix**:
```bash
# Check if backend is running
curl http://localhost:8001/health

# If not, start it:
python -m backend.main
```

### Frontend Shows "Network Error"

**Cause**: Backend URL incorrect

**Fix**:
```bash
# Check frontend/.env or vite.config.js
# Should proxy to http://localhost:8001
```

### Docker Issues

**Fix**:
```bash
# Stop everything
docker-compose down

# Remove volumes
docker-compose down -v

# Rebuild fresh
docker-compose up --build
```

---

## Demo Scenarios

### Try Council Mode

**Question**: "What are the ethical implications of AGI?"

**Watch**:
- Stage 1: 3 different AI perspectives
- Stage 2: Anonymous peer rankings
- Stage 3: Chairman's synthesis

### Try DxO Mode

**Question**: "Latest advances in quantum error correction"

**Watch**:
- Lead Researcher searches arXiv papers
- Critical Reviewer challenges findings
- Domain Expert validates
- Final comprehensive report

---

