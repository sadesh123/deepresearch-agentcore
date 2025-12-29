# Deep Research Agent

An AI-powered research system deployed on AWS Bedrock AgentCore, featuring two distinct multi-agent collaboration patterns for decision-making and research.

## What Does This Agent Do?

The Deep Research Agent provides two research modes:

### 1. LLM Council Mode
A democratic deliberation system with three stages:
- **Stage 1**: Multiple AI models independently analyze your question
- **Stage 2**: Models anonymously rank each other's responses
- **Stage 3**: A chairman synthesizes the best insights into a final answer

**Best for**: Questions requiring diverse perspectives and balanced analysis

### 2. DxO Research Mode
A sequential expert workflow for deep research:
- **Lead Researcher**: Conducts initial research using arXiv papers
- **Critical Reviewer**: Challenges assumptions and identifies gaps
- **Domain Expert**: Validates technical accuracy
- **Final Synthesis**: Integrates all feedback into a comprehensive report

**Best for**: Technical research questions and academic inquiries

## How to Run Locally

### Prerequisites
- Python 3.11+
- Node.js 18+
- AWS account with Bedrock access (Claude models enabled)

### Quick Start

**1. Setup Backend**
```bash
# Install dependencies
pip install -r requirements.txt

# Configure AWS credentials
cp .env.example .env
# Edit .env with your AWS credentials

# Start backend
python -m backend.main
```
Backend runs on `http://localhost:8001`

**2. Setup Frontend**
```bash
cd frontend
npm install
npm run dev
```
Frontend runs on `http://localhost:5173`

**3. Test It**
- Open `http://localhost:5173` in your browser
- Choose Council or DxO mode
- Ask a research question
- Watch the multi-agent collaboration!

### Using Docker
```bash
docker-compose up --build
```
Access at `http://localhost:5173`

## Deployment

**Live Deployment**: AWS Bedrock AgentCore
- **Frontend**: CloudFront + S3
- **API**: Lambda + API Gateway
- **Runtime**: AWS Bedrock AgentCore
- **Model**: Claude 3.5 Haiku

The system is fully deployed and accessible via CloudFront CDN.

## Architecture

```
React Frontend (Vite)
    ↓
API Gateway + Lambda
    ↓
AWS Bedrock AgentCore
    ↓
Claude 3.5 Haiku + arXiv API
```
<img width="4909" height="2400" alt="AWS-AgentCore (2)" src="https://github.com/user-attachments/assets/9fe9403e-363b-4046-a64e-29f5e40f8590" />

## Project Structure
```
deepresearch-agentcore/
├── agents/              # Agent implementations (Council & DxO)
├── backend/             # FastAPI backend server
├── frontend/            # React + Vite frontend
├── lambda/              # AWS Lambda proxy function
├── deploy/              # Deployment scripts
└── docker-compose.yml   # Local Docker setup
```

## Key Technologies
- **AI Models**: AWS Bedrock (Claude 3.5 Haiku)
- **Backend**: Python, FastAPI
- **Frontend**: React, Vite
- **Deployment**: AWS Lambda, API Gateway, CloudFront, S3
- **Research**: arXiv API integration

## API Endpoints

- `GET /health` - Health check
- `POST /council` - Run council deliberation
- `POST /dxo` - Run DxO research workflow

See API documentation at `http://localhost:8001/docs` when running locally.

## Additional Documentation

- `QUICKSTART.md` - 5-minute setup guide
- `DEPLOYMENT.md` - Detailed AWS deployment instructions (archived)
- `AGENTCORE_REFACTORING.md` - Implementation notes (archived)

## License

MIT License

---

**Built for IHL Demo | Powered by AWS Bedrock AgentCore**
