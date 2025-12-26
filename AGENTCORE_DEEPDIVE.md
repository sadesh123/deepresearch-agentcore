# AWS Bedrock AgentCore - Deep Dive

A comprehensive guide to understanding AWS Bedrock AgentCore and how it powers the Deep Research Agent.

---

## Table of Contents
1. [What is AgentCore?](#what-is-agentcore)
2. [Core Services](#core-services)
3. [Runtime Architecture](#runtime-architecture)
4. [Memory Management](#memory-management)
5. [Gateway](#gateway)
6. [Policy & Governance](#policy--governance)
7. [Identity & Authentication](#identity--authentication)
8. [How Deep Research Agent Uses AgentCore](#how-deep-research-agent-uses-agentcore)
9. [Production Deployment](#production-deployment)

---

## What is AgentCore?

**Amazon Bedrock AgentCore** is an agentic platform for building, deploying, and operating highly effective AI agents securely at scale. It's AWS's answer to the challenges of running production-grade AI agents in enterprise environments.

### Key Philosophy
- **Framework Agnostic**: Works with any open-source framework (CrewAI, LangGraph, LlamaIndex, Strands Agents)
- **Model Agnostic**: Compatible with any foundation model (Claude, OpenAI, Google Gemini, Amazon Nova, Meta Llama, Mistral)
- **Production Ready**: Enterprise-grade security, reliability, and scalability without infrastructure management

### Why AgentCore Exists
Traditional AI deployments face challenges:
- ❌ Managing infrastructure for scaling agents
- ❌ Securing agent access to tools and data
- ❌ Implementing proper authentication and authorization
- ❌ Monitoring agent performance in production
- ❌ Maintaining context across conversations
- ❌ Isolating sessions for security

AgentCore solves all of these out of the box.

---

## Core Services

AgentCore is composed of **9 modular services** that work together or independently:

### 1. **AgentCore Runtime** 🚀
**Purpose**: Secure, serverless hosting environment for deploying and scaling AI agents

**Key Features**:
- **Session Isolation**: Each user session runs in a dedicated microVM
- **Fast Cold Starts**: Optimized for production performance
- **8-Hour Execution Windows**: Support for long-running agent tasks
- **Multi-Protocol Support**: HTTP, WebSocket, MCP, A2A (Agent-to-Agent)
- **Bidirectional Streaming**: Natural conversations with interruptions

**How It Works**:
```
Container Image (ECR) → AgentCore Runtime → Auto-scaled Endpoints
                              ↓
                    Dedicated microVM per session
                    (Isolated CPU, memory, filesystem)
```

### 2. **AgentCore Memory** 🧠
**Purpose**: Enable context-aware agents with persistent memory

**Memory Types**:
- **Short-term Memory**: Multi-turn conversation context (within session)
- **Long-term Memory**: Cross-session knowledge persistence
- **Episodic Memory**: Learn from experiences and adapt over time

**New Feature (Dec 2025)**:
Episodic memory enables agents to capture "episodes" including context, reasoning, actions, and outcomes. A separate analyzer agent identifies patterns so your primary agent can reuse successful strategies.

### 3. **AgentCore Gateway** 🌉
**Purpose**: Transform APIs and services into agent-compatible tools

**Capabilities**:
- Convert REST APIs into MCP-compatible tools
- Integrate Lambda functions as agent tools
- Connect to existing MCP servers
- **IAM Authorization**: Leverage IAM for secure tool interactions
- **Real-time Interception**: Policy enforcement on every tool call

**Architecture**:
```
Your API/Lambda → Gateway → MCP Format → Agent Access
                     ↓
              Policy Enforcement
```

### 4. **AgentCore Identity** 🔐
**Purpose**: Centralized identity management for AI agents and non-human identities

**Key Principles**:
- **Zero-Trust Approach**: Every request verified independently
- **No Implicit Trust**: Explicit verification regardless of source

**Authentication Methods**:
- AWS SigV4 (for AWS services)
- OAuth 2.0 (standard flows)
- API Keys

**Integration Support**:
- AWS Services (seamless)
- Third-party services (Slack, Zoom, GitHub)
- Standard IdPs (Okta, Entra ID, Auth0, Cognito)

### 5. **AgentCore Code Interpreter** 💻
**Purpose**: Secure code execution sandbox

**Features**:
- Execute Python, JavaScript, TypeScript
- Isolated sandbox environment
- Safe code generation and execution
- No access to production systems

### 6. **AgentCore Browser** 🌐
**Purpose**: Enterprise-grade web automation

**Capabilities**:
- Navigate websites
- Complete multi-step forms
- Extract information from web pages
- Fully managed sandbox environment

### 7. **AgentCore Observability** 📊
**Purpose**: Unified monitoring and debugging

**Metrics Tracked**:
- Token usage (costs)
- Latency (performance)
- Session duration
- Error rates
- Agent decisions (audit trail)

**Integration**:
- Amazon CloudWatch dashboards
- OpenTelemetry support
- Trace and debug issues in production

### 8. **AgentCore Evaluations** 📈
**Purpose**: Automated assessment of agent quality (Preview - Dec 2025)

**Features**:
- Data-driven performance evaluation
- Quality metrics
- Reliability testing
- Real-world scenario validation

### 9. **AgentCore Policy** ⚖️
**Purpose**: Deterministic control and governance (Preview - Dec 2025)

**Announced at re:Invent 2025**:
- Natural language policy definition
- Cedar policy language support (fine-grained permissions)
- Real-time tool call interception at Gateway
- Ensure agents stay within defined boundaries

**Architecture**:
```
Agent → Tool Call → Gateway + Policy Engine → Evaluate → Allow/Deny
```

**Example Use Case**:
"Agents can read from database but never write"
"Agents cannot approve purchases over $1000"
"Agents must escalate to human for compliance-sensitive actions"

---

## Runtime Architecture

### How AgentCore Runtime Works

#### 1. **Core Components**

```
AgentCore Runtime
├── Versions (Immutable snapshots)
│   ├── V1 (auto-created on deployment)
│   ├── V2 (created on updates)
│   └── V3 (rollback capability)
│
├── Endpoints (Addressable access points)
│   ├── DEFAULT (auto-created, points to latest)
│   ├── dev-endpoint (custom)
│   ├── staging-endpoint (custom)
│   └── prod-endpoint (custom)
│
└── Sessions (Individual user interactions)
    ├── Unique runtimeSessionId
    ├── Dedicated microVM
    ├── 8-hour max lifetime
    └── 15-min idle timeout
```

#### 2. **Session Isolation (Critical Security Feature)**

Every session runs in a **dedicated microVM** with:
- Isolated CPU
- Isolated memory
- Isolated filesystem
- Complete data separation

**Security Guarantees**:
✅ Cross-session data contamination impossible
✅ Memory sanitized after termination
✅ New execution environment per session
✅ No shared state between users

#### 3. **Execution Model**

**Asynchronous Processing**:
- Background tasks up to 8 hours
- Automatic status tracking via `/ping` endpoint
- Long-running operations supported

**Streaming Responses**:
- Partial results streamed as available
- Improved UX for large content
- Bidirectional communication (listen + respond simultaneously)

**Protocol Support**:
- **HTTP**: Traditional REST API
- **WebSocket**: Real-time bidirectional streaming
- **MCP**: Model Context Protocol for tools/servers
- **A2A**: Agent-to-Agent protocol (multi-agent systems)

#### 4. **Lifecycle States**

**Endpoint States**:
```
CREATING → READY → UPDATING → READY
    ↓         ↓         ↓         ↓
CREATE_FAILED  ✓   UPDATE_FAILED  ✓
```

**Session States**:
```
Active → Processing requests/background tasks
  ↓
Idle → Waiting for next interaction (context maintained)
  ↓
Terminated → Ended (inactivity/max lifetime/health issues)
```

#### 5. **Zero-Downtime Updates**

AgentCore enables **seamless version transitions**:

1. Deploy new version → Creates V2
2. Update endpoint to point to V2
3. New sessions use V2
4. Existing sessions complete on V1
5. Rollback: Point endpoint back to V1

**No downtime. No service interruption.**

---

## Memory Management

### Memory Architecture

AgentCore Memory provides **three layers of context**:

#### 1. **Session Memory (Short-term)**
- **Scope**: Single conversation
- **Duration**: Up to 8 hours or until session termination
- **Use Case**: Multi-turn dialogue, maintaining context within a conversation
- **Implementation**: Stored in microVM memory (ephemeral)

#### 2. **Cross-Session Memory (Long-term)**
- **Scope**: Across multiple conversations
- **Duration**: Persistent (user configurable)
- **Use Case**: User preferences, historical context, learned patterns
- **Implementation**: Managed persistence layer

#### 3. **Episodic Memory (New in Dec 2025)**
- **Scope**: Learning from experiences
- **Duration**: Persistent and growing
- **Use Case**: Adaptive agents that improve over time

**How Episodic Memory Works**:
```
Primary Agent completes task
    ↓
Episode captured (context + reasoning + actions + outcome)
    ↓
Analyzer Agent identifies patterns across episodes
    ↓
Primary Agent reuses successful strategies in future tasks
```

**Example**:
- Episode 1: Agent searches for research papers on "quantum computing"
- Episode 2: Agent searches for papers on "machine learning"
- Pattern: User prefers arXiv papers from last 2 years
- Future: Agent automatically filters to recent papers

### Memory vs. Session State

| Feature | Session State | AgentCore Memory |
|---------|--------------|------------------|
| Duration | Up to 8 hours | Persistent |
| Scope | Single session | Cross-session |
| Storage | microVM (ephemeral) | Managed service |
| Use Case | Conversation flow | Long-term knowledge |
| Cost | Included | Pay per storage |

---

## Gateway

### What is AgentCore Gateway?

The Gateway is the **tool integration layer** that:
1. Converts any API into an agent-accessible tool
2. Enforces policies on tool usage
3. Provides IAM-based authorization
4. Connects to MCP (Model Context Protocol) servers

### Architecture

```
┌─────────────────────────────────────────┐
│         Your Agent (Runtime)            │
└──────────────┬──────────────────────────┘
               │
               │ "I need to call Tool X"
               ▼
┌─────────────────────────────────────────┐
│       AgentCore Gateway                 │
│  ┌─────────────────────────────────┐   │
│  │   Policy Engine (Cedar)         │   │
│  │   • Evaluate tool call          │   │
│  │   • Check boundaries            │   │
│  │   • Allow or Deny               │   │
│  └─────────────────────────────────┘   │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │   Tool Registry                 │   │
│  │   • REST APIs → MCP format      │   │
│  │   • Lambda functions            │   │
│  │   • Existing MCP servers        │   │
│  └─────────────────────────────────┘   │
└──────────────┬──────────────────────────┘
               │
               │ Authorized & Validated
               ▼
┌─────────────────────────────────────────┐
│    External Tools & Services            │
│  • AWS Services (DynamoDB, S3)          │
│  • Third-party APIs (Slack, GitHub)     │
│  • Custom Lambda functions              │
│  • Enterprise systems                   │
└─────────────────────────────────────────┘
```

### Key Features

#### 1. **Automatic Tool Conversion**
- **Input**: REST API with OpenAPI spec
- **Output**: MCP-compatible tool
- **Result**: Agent can call API without custom integration

#### 2. **IAM Authorization**
Gateway supports **IAM in addition to OAuth** for secure interactions:
```
Agent → Gateway (checks IAM policy) → Tool
```

#### 3. **Real-time Policy Enforcement**
Every tool call is intercepted:
```python
# Example Policy (Cedar language)
permit(
    principal == Agent::"research-agent",
    action == [Action::"read"],
    resource in Database::"arxiv-papers"
)
forbid(
    principal == Agent::"research-agent",
    action == [Action::"write"],
    resource in Database::"arxiv-papers"
)
```

#### 4. **MCP Server Support**
Connect existing MCP servers directly:
- Anthropic's MCP servers
- Community MCP tools
- Custom MCP implementations

---

## Policy & Governance

### Policy Engine (Preview - Dec 2025)

The Policy layer provides **deterministic control** over agent behavior.

#### How It Works

1. **Create Policy Engine** in AgentCore console
2. **Define Policies** using:
   - Natural language: "Agents cannot delete customer data"
   - Cedar language: Fine-grained permission rules
3. **Associate with Gateway**
4. **Real-time Enforcement** on every tool call

#### Policy Architecture

```
┌────────────────────────────────────────────┐
│  Agent attempts tool call                  │
└────────────┬───────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────┐
│  Gateway intercepts                        │
│  ┌──────────────────────────────────────┐ │
│  │  Policy Engine evaluates:            │ │
│  │  • Principal (which agent?)          │ │
│  │  • Action (what operation?)          │ │
│  │  • Resource (on what data?)          │ │
│  │  • Context (under what conditions?)  │ │
│  └──────────────────────────────────────┘ │
└────────────┬──────────┬────────────────────┘
             │          │
         ALLOW        DENY
             │          │
             ▼          ▼
      Execute Tool   Block & Log
```

#### Policy Use Cases

**Financial Services**:
```
"Agents can view account balances but cannot initiate transfers over $10,000"
```

**Healthcare**:
```
"Agents can read patient records only for scheduled appointments"
```

**Customer Support**:
```
"Agents can issue refunds up to $100, escalate higher amounts to humans"
```

**Data Privacy**:
```
"Agents cannot access PII without explicit user consent"
```

#### Cedar Policy Language

Cedar is an **open-source policy language** developed by AWS:
- **Fine-grained permissions**
- **Human-readable syntax**
- **Formally verified** (mathematically proven correctness)

**Example Policy**:
```cedar
permit(
    principal == Agent::"deep-research-agent",
    action in [Action::"search", Action::"read"],
    resource in Collection::"arxiv-papers"
)
when {
    context.time >= "09:00:00" &&
    context.time <= "17:00:00"
};

forbid(
    principal == Agent::"deep-research-agent",
    action == Action::"delete",
    resource in Collection::"arxiv-papers"
);
```

---

## Identity & Authentication

### AgentCore Identity Overview

AgentCore Identity provides **centralized identity management for AI agents** with a zero-trust security model.

### Inbound Authentication (Who can access your agent?)

#### Method 1: AWS IAM (SigV4)
- AWS credential-based verification
- Integrated with IAM roles and policies
- Best for: AWS service-to-service calls

#### Method 2: OAuth 2.0
- External identity provider integration
- Supports: Cognito, Okta, Entra ID, Auth0
- Best for: End-user applications

**OAuth Flow**:
```
1. User authenticates with IdP (Okta/Cognito/etc.)
   ↓
2. Client receives bearer token
   ↓
3. Client calls agent with token in Authorization header
   ↓
4. AgentCore validates token with authorization server
   ↓
5. Request processed if valid, rejected if invalid
```

**Configuration**:
```yaml
oauth:
  discovery_url: "https://cognito.amazonaws.com/.well-known/openid-configuration"
  allowed_audiences:
    - "agent-api"
  allowed_clients:
    - "mobile-app-client"
    - "web-app-client"
```

### Outbound Authentication (How agent accesses tools?)

Agents need credentials to access external services.

#### Method 1: OAuth (User-Delegated)
Agent acts **on behalf of the user**:
```
User grants permission → Agent uses user's OAuth token → Access Slack as user
```

#### Method 2: OAuth (Autonomous)
Agent acts **with service-level credentials**:
```
Agent has service account → Uses service OAuth token → Access GitHub as bot
```

#### Method 3: API Keys
Simple key-based authentication:
```
Agent → API Key → External Service
```

**Supported Services**:
- Enterprise: Slack, Zoom, GitHub, Jira
- AWS: DynamoDB, S3, Lambda
- Custom APIs: Any REST API

### Security Principles

AgentCore Identity implements **zero-trust**:

1. **No Implicit Trust**
   - Every request verified independently
   - Source doesn't matter—authentication required

2. **Principle of Least Privilege**
   - Agents only get access to what they need
   - Time-based access controls possible

3. **Credential Management**
   - Centralized secret storage
   - Automatic rotation support
   - Audit logging of all access

4. **Separation of Concerns**
   - User identity vs. agent identity
   - Different credentials for different agents
   - Scoped permissions per agent

---

## How Deep Research Agent Uses AgentCore

### Architecture Mapping

Our Deep Research Agent leverages **multiple AgentCore services**:

```
User Browser
    ↓
CloudFront + S3 (Frontend)
    ↓
API Gateway
    ↓
Lambda (agentcore_proxy.py)
    ↓
┌────────────────────────────────────────────┐
│     AWS BEDROCK AGENTCORE RUNTIME         │
│                                            │
│  ┌──────────────────────────────────────┐ │
│  │  council_agent.py                    │ │
│  │  • Stage 1: Parallel responses (3x)  │ │
│  │  • Stage 2: Peer rankings (3x)       │ │
│  │  • Stage 3: Synthesis (1x)           │ │
│  └──────────────────────────────────────┘ │
│                                            │
│  ┌──────────────────────────────────────┐ │
│  │  dxo_agent.py                        │ │
│  │  • Lead Researcher + arXiv           │ │
│  │  • Critical Reviewer                 │ │
│  │  • Domain Expert                     │ │
│  │  • Final Synthesis                   │ │
│  └──────────────────────────────────────┘ │
│                                            │
│  Uses:                                     │
│  • Session Isolation (microVM per user)   │
│  • 8-hour execution window               │
│  • Streaming responses                    │
└────────────────────────────────────────────┘
    ↓
AWS Bedrock (Claude 3.5 Haiku)
    ↓
arXiv API (external)
```

### AgentCore Services in Use

#### ✅ **AgentCore Runtime**
- **Deployment**: Container image deployed to AgentCore Runtime
- **Session Management**: Each user conversation = unique session
- **Scaling**: Auto-scaled based on demand
- **Isolation**: Each user's research runs in dedicated microVM

#### ✅ **AgentCore Gateway** (Potential Enhancement)
- Currently: Lambda directly invokes Runtime
- Enhancement: Use Gateway to expose tools (arXiv, custom APIs)
- Benefit: Policy enforcement, better tool management

#### ✅ **AgentCore Identity** (Potential Enhancement)
- Currently: Lambda handles authentication via API Gateway
- Enhancement: Integrate OAuth for user-specific research sessions
- Benefit: Personalized research history, saved preferences

#### ⚠️ **AgentCore Memory** (Not Yet Implemented)
- Potential: Store user research history across sessions
- Benefit: "Remember my previous research on quantum computing"
- Use Case: Long-term research projects

#### ⚠️ **AgentCore Policy** (Not Yet Implemented)
- Potential: Control agent behavior
- Example: "Only search papers from last 5 years"
- Example: "Never exceed 10 arXiv API calls per request"

### Why AgentCore for Deep Research Agent?

**Before AgentCore** (Manual Deployment):
- ❌ Manage Kubernetes/ECS clusters
- ❌ Configure auto-scaling
- ❌ Implement session isolation
- ❌ Build monitoring dashboards
- ❌ Handle security and authentication

**With AgentCore**:
- ✅ Deploy container → instant scaling
- ✅ Built-in session isolation
- ✅ CloudWatch monitoring included
- ✅ IAM and OAuth authentication ready
- ✅ Zero infrastructure management

**Result**: Focus on agent logic, not infrastructure.

---

## Production Deployment

### Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    PRODUCTION STACK                          │
└─────────────────────────────────────────────────────────────┘

┌──────────────┐
│ CloudFront   │ ← CDN, SSL termination, routing
└──────┬───────┘
       │
   ┌───┴───┐
   │       │
   ▼       ▼
┌────┐  ┌─────────────┐
│ S3 │  │ API Gateway │ ← HTTP API endpoints
└────┘  └──────┬──────┘
               │
               ▼
        ┌─────────────┐
        │   Lambda    │ ← agentcore_proxy.py
        │             │ • Parse requests
        │             │ • Invoke AgentCore Runtime
        │             │ • Parse markdown responses
        └──────┬──────┘
               │ invoke_agent_runtime()
               ▼
        ┌──────────────────────────────────┐
        │   AgentCore Runtime              │
        │   • council_agent.py             │
        │   • dxo_agent.py                 │
        │   • Session isolation (microVM)  │
        │   • Auto-scaling                 │
        │   • 8-hour execution windows     │
        └──────┬───────────────────────────┘
               │
               ▼
        ┌──────────────┐      ┌────────────┐
        │   Bedrock    │      │ arXiv API  │
        │ Claude Haiku │      │ (External) │
        └──────────────┘      └────────────┘
```

### Deployment Flow

#### 1. **Build Agent Code**
```bash
# Package agents into container
docker build -f Dockerfile.agentcore -t deep-research-agent .

# Push to ECR
aws ecr get-login-password | docker login --username AWS --password-stdin
docker tag deep-research-agent:latest <ecr-uri>
docker push <ecr-uri>
```

#### 2. **Deploy to AgentCore Runtime**
```python
# Create AgentCore Runtime
agentcore.create_agent_runtime(
    runtime_name="deep-research-agent",
    container_image=ecr_uri,
    protocol="HTTP",
    authentication={
        "inbound": "IAM",  # Who can invoke
        "outbound": "API_KEY"  # How agent accesses tools
    }
)
```

#### 3. **Create Endpoints**
```python
# DEFAULT endpoint (auto-created, points to latest version)
# Custom endpoints for environments
agentcore.create_endpoint(
    endpoint_name="production",
    version="V1",
    alias="DEFAULT"
)
```

#### 4. **Lambda Proxy Setup**
```python
# Lambda invokes AgentCore Runtime
response = agentcore_client.invoke_agent_runtime(
    agentRuntimeArn=RUNTIME_ARN,
    runtimeSessionId=session_id,
    payload=json.dumps({
        "input": {
            "mode": "council",
            "prompt": question
        }
    })
)
```

#### 5. **API Gateway Integration**
```yaml
routes:
  - path: /council
    method: POST
    integration:
      type: AWS_PROXY
      uri: !Sub "arn:aws:lambda:${AWS::Region}:${AWS::AccountId}:function:DeepResearchAgentProxy"

  - path: /dxo
    method: POST
    integration:
      type: AWS_PROXY
      uri: !Sub "arn:aws:lambda:${AWS::Region}:${AWS::AccountId}:function:DeepResearchAgentProxy"
```

### Cost Breakdown

| Service | Pricing Model | Estimated Cost |
|---------|--------------|----------------|
| **AgentCore Runtime** | Per session-minute | $0.10-$0.50 per research |
| **Bedrock (Claude Haiku)** | Per token | $0.05-$0.20 per research |
| **Lambda** | Per invocation | $0.0000002 per request |
| **API Gateway** | Per request | $0.000001 per request |
| **CloudFront** | Per request + data transfer | $0.01-$0.05 per 10K requests |
| **S3** | Per GB storage + requests | <$0.01/month |

**Total**: ~$0.20-$0.80 per research query

### Performance Characteristics

| Metric | Value | Notes |
|--------|-------|-------|
| **Cold Start** | 2-3s | Lambda + AgentCore initialization |
| **Warm Request** | 5-15s | Depends on LLM calls |
| **Council Mode** | 10-20s | 7 Bedrock calls (some parallel) |
| **DxO Mode** | 15-30s | 4 Bedrock calls + arXiv search |
| **Max Session** | 8 hours | AgentCore limit |
| **Frontend Load** | <500ms | Cached via CloudFront |

### Scaling Behavior

AgentCore Runtime **automatically scales**:

```
Low Traffic (< 10 req/min)
    ↓
AgentCore maintains minimal instances
    ↓
High Traffic Spike (100 req/min)
    ↓
AgentCore scales to 100+ instances within seconds
    ↓
Traffic Returns to Normal
    ↓
AgentCore scales down (pay only for what you use)
```

**No configuration needed. No capacity planning. Just works.**

---

## Key Takeaways for Blog Post

### 1. **AgentCore is a Complete Platform**
Not just a runtime—it's:
- Runtime + Memory + Gateway + Identity + Policy + Observability + Evaluations

### 2. **Production-Grade by Default**
- Session isolation (dedicated microVMs)
- Zero-downtime updates
- Built-in monitoring
- Enterprise authentication
- Policy enforcement

### 3. **Framework & Model Agnostic**
- Use any agent framework (LangGraph, CrewAI, custom)
- Use any LLM (Claude, GPT-4, Llama, etc.)
- Not locked into AWS-specific patterns

### 4. **Solves Real Problems**
- **Security**: Zero-trust identity, session isolation
- **Scalability**: Auto-scaling, no infrastructure management
- **Governance**: Policy enforcement, audit logging
- **Cost**: Pay per use, no idle costs

### 5. **Deep Research Agent Benefits**
- Deployed in minutes (vs. weeks of infrastructure work)
- Secure multi-user sessions (isolated microVMs)
- Auto-scaled to handle traffic spikes
- Monitored out-of-the-box (CloudWatch integration)
- Ready for enterprise (authentication, policies)

---

## Sources & References

- [Amazon Bedrock AgentCore Overview](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/what-is-bedrock-agentcore.html)
- [AgentCore Runtime Documentation](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-how-it-works.html)
- [AgentCore Identity Overview](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/identity-overview.html)
- [AWS Blog: AgentCore Quality Evaluations and Policy Controls](https://aws.amazon.com/blogs/aws/amazon-bedrock-agentcore-adds-quality-evaluations-and-policy-controls-for-deploying-trusted-ai-agents/)
- [AgentCore Policy and Evaluations Preview](https://aws.amazon.com/about-aws/whats-new/2025/12/amazon-bedrock-agentcore-policy-evaluations-preview/)
- [AgentCore General Availability](https://aws.amazon.com/about-aws/whats-new/2025/10/amazon-bedrock-agentcore-available/)
- [AgentCore Pricing](https://aws.amazon.com/bedrock/agentcore/pricing/)

---

**Document Version**: 1.0
**Last Updated**: December 2025
**Author**: Deep Research Agent Team
