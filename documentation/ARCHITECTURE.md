# Deep Research Agent - AWS Architecture

## Production Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          USER BROWSER                                │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 │ HTTPS
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     AWS CLOUDFRONT (CDN)                             │
│  - Global edge locations                                             │
│  - SSL/TLS termination                                               │
│  - Caching static assets                                             │
└──────────────┬──────────────────────────────┬───────────────────────┘
               │                              │
               │ /assets, /index.html         │ /council, /dxo, /health
               │ (Static Frontend)            │ (API calls)
               ▼                              ▼
┌──────────────────────────────┐   ┌────────────────────────────────┐
│      S3 BUCKET               │   │   API GATEWAY (HTTP API)       │
│                              │   │                                │
│  - React Build (dist/)       │   │  Routes:                       │
│  - index.html                │   │    POST /council               │
│  - JavaScript bundles        │   │    POST /dxo                   │
│  - CSS, assets               │   │    GET  /health                │
│  - Public read access        │   │                                │
└──────────────────────────────┘   └────────────┬───────────────────┘
                                                 │
                                                 │ Invokes
                                                 ▼
                                   ┌─────────────────────────────────┐
                                   │  AWS LAMBDA FUNCTION            │
                                   │  (agentcore_proxy.py)           │
                                   │                                 │
                                   │  - Receives HTTP requests       │
                                   │  - Parses question & mode       │
                                   │  - Invokes AgentCore Runtime    │
                                   │  - Parses markdown response     │
                                   │  - Returns structured JSON      │
                                   └────────────┬────────────────────┘
                                                │
                                                │ invoke_agent_runtime()
                                                ▼
                                   ┌─────────────────────────────────┐
                                   │  AWS BEDROCK AGENTCORE          │
                                   │  (Runtime)                      │
                                   │                                 │
                                   │  Contains:                      │
                                   │  - council_agent.py             │
                                   │  - dxo_agent.py                 │
                                   │  - bedrock_client.py            │
                                   │  - arxiv_tool.py                │
                                   └────────────┬────────────────────┘
                                                │
                                                │ Calls
                                                ▼
                            ┌───────────────────────────────────┐
                            │   AWS BEDROCK (Claude Models)     │
                            │                                   │
                            │   Model: Claude 3.5 Haiku         │
                            │   - Stage 1: Multiple responses   │
                            │   - Stage 2: Peer rankings        │
                            │   - Stage 3: Final synthesis      │
                            └───────────────────────────────────┘
                                                │
                                                │ (DxO mode also uses)
                                                ▼
                                   ┌─────────────────────────────────┐
                                   │   ARXIV API                     │
                                   │   (External - Free)             │
                                   │                                 │
                                   │   - Academic paper search       │
                                   │   - Research data               │
                                   └─────────────────────────────────┘
```

## Request Flow Example

**Council Mode Request Flow:**

1. **USER** enters question in browser
2. **CLOUDFRONT** serves React app from S3
3. **USER** clicks "Start Council Research"
4. **React app** sends: `POST /council {"question": "..."}`
5. **CLOUDFRONT** routes API call to API Gateway
6. **API GATEWAY** triggers Lambda function
7. **LAMBDA** invokes AgentCore with payload
8. **AGENTCORE** runs `council_agent.py`:
   - Stage 1: Calls Bedrock 3x (parallel responses)
   - Stage 2: Calls Bedrock 3x (rankings)
   - Stage 3: Calls Bedrock 1x (synthesis)
9. **AGENTCORE** returns markdown to Lambda
10. **LAMBDA** parses markdown → structured JSON
11. **API GATEWAY** returns JSON to frontend
12. **React** displays 3-stage deliberation results


## Key Components

### Backend Services
- **CloudFront (CDN)** - Content delivery, SSL, routing
- **S3** - Static frontend hosting
- **API Gateway** - REST API endpoints
- **Lambda** - AgentCore proxy function
- **AgentCore Runtime** - Multi-agent orchestration
- **Bedrock (Claude)** - LLM inference
- **arXiv API** - Academic research data

## Data Flow

### Council Mode
```
Question → Lambda → AgentCore → Bedrock (7 calls total)
  Stage 1: 3 parallel calls
  Stage 2: 3 parallel calls
  Stage 3: 1 call
Response: Structured JSON with stage1, stage2, stage3, metadata
```

### DxO Mode
```
Question → Lambda → AgentCore → Bedrock + arXiv (4 calls)
  1. Lead Researcher (with arXiv search)
  2. Critical Reviewer
  3. Domain Expert
  4. Final Synthesis
Response: Structured JSON with workflow array
```

## Security & Configuration

### Authentication
- AWS credentials via IAM roles
- Lambda execution role with Bedrock permissions
- S3 bucket policy for CloudFront access

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **CDN** | CloudFront | Global content delivery |
| **Storage** | S3 | Static file hosting |
| **API** | API Gateway | REST endpoints |
| **Compute** | Lambda | Serverless proxy |
| **AI Runtime** | Bedrock AgentCore | Multi-agent orchestration |
| **LLM** | Claude 3.5 Haiku | Language model inference |
| **Frontend** | React + Vite | User interface |
| **Backend** | FastAPI (local dev) | Local API server |
| **External API** | arXiv | Academic research data |



