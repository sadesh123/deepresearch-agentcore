# CyberArk OAuth Integration - Implementation Guide

## Context

This document provides step-by-step instructions to implement a "Connect CyberArk" button in the Deep Research Agent as a proof-of-concept for AgentCore Gateway outbound authentication.

**Goal**: Demonstrate AgentCore's ability to use CyberArk as an OAuth 2.0 identity provider for agents to access downstream services on behalf of users.

## Background

### What is Outbound Authentication?
- **Inbound Auth**: Who can ACCESS the agent (user → agent)
- **Outbound Auth**: What can the agent ACCESS on behalf of user (agent → downstream service)

We're implementing **outbound authentication** - allowing the Deep Research Agent to authenticate to downstream services (like enterprise research repositories) using the user's CyberArk credentials.

### OAuth Flow
```
User clicks "Connect CyberArk"
  → Agent tool calls @requires_access_token
  → Returns authorization URL
  → Frontend opens CyberArk login popup
  → User authenticates with CyberArk
  → CyberArk redirects with auth code
  → AgentCore exchanges code for token
  → Token stored in AWS Token Vault
  → Agent returns user info from token
  → Frontend displays connection status
```

---

## Prerequisites (User Must Complete First)

### 1. Create CyberArk Web Application

**Reference**: https://docs.cyberark.com/identity/latest/en/content/applications/appscustom/openidaddconfigapp.htm

Steps:
1. Log into CyberArk admin portal
2. Navigate to Applications → Add Web App
3. Configure OAuth 2.0 settings:
   - **Application Type**: Web Application
   - **Grant Types**: Authorization Code
   - **Scopes**: `openid`, `profile`, `email`
   - **Redirect URIs**: (Will be provided by AgentCore - see step 2)
4. Save and note down:
   - ✅ Client ID
   - ✅ Client Secret
   - ✅ Discovery URL (format: `https://{tenant}.cyberark.cloud/.well-known/openid-configuration`)

### 2. Create AgentCore OAuth2 Credential Provider

**Reference**: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/identity-idp-cyberark.html

Steps:
1. AWS Console → Bedrock → AgentCore → Identity
2. Click "Create OAuth2 Credential Provider"
3. Configure:
   - **Provider Name**: `CyberArk-Demo` (or your preferred name)
   - **Provider Type**: Custom OAuth 2.0
   - **Discovery URL**: From CyberArk app (step 1)
   - **Client ID**: From CyberArk app (step 1)
   - **Client Secret**: From CyberArk app (step 1)
   - **Scopes**: `openid profile email`
   - **Grant Type**: Authorization Code (3-legged OAuth)
4. Save and note down:
   - ✅ Credential Provider ARN
   - ✅ OAuth Callback URL (copy this and add to CyberArk app's redirect URIs)

### 3. Update CyberArk App with Callback URL

Return to CyberArk admin portal and add the callback URL from step 2 to the application's redirect URIs list.

## Implementation Steps

### Step 1: Create Agent Tool for OAuth

**File**: `agents/cyberark_demo_tool.py`

```python
"""
CyberArk OAuth integration tool for AgentCore.
Demonstrates outbound authentication for downstream service access.
"""

from bedrock_agentcore.identity.auth import requires_access_token
import jwt
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

@requires_access_token(
    provider_name="CyberArk-Demo",  # ⚠️ REPLACE with actual provider name from AWS
    scopes=["openid", "profile", "email"],
    auth_flow="USER_FEDERATION",  # 3-legged OAuth (user consent required)
    on_auth_url=lambda url: {
        "authorization_url": url,
        "needs_auth": True,
        "message": "Please authenticate with CyberArk to continue"
    },
    force_authentication=False,  # Use cached token if available
    callback_url='INSERT_CALLBACK_URL_HERE'  # ⚠️ REPLACE with callback URL from AWS
)
async def connect_cyberark(*, access_token: str) -> Dict[str, Any]:
    """
    Connects to CyberArk via OAuth and returns user information from token.

    This is a demo tool to validate OAuth integration. In production, you would
    use this token to access actual downstream services (internal research repos, etc.)

    Args:
        access_token: OAuth access token from CyberArk (injected by @requires_access_token)

    Returns:
        Dictionary with connection status and user information
    """
    try:
        # Decode token to extract user claims (without signature verification for demo)
        token_claims = jwt.decode(access_token, options={"verify_signature": False})

        logger.info(f"Successfully connected to CyberArk for user: {token_claims.get('sub')}")

        return {
            "status": "success",
            "message": f"Connected as {token_claims.get('name', 'Unknown User')}",
            "connected": True,
            "user_info": {
                "user_id": token_claims.get("sub"),
                "email": token_claims.get("email"),
                "name": token_claims.get("name"),
                "token_issued_at": token_claims.get("iat"),
                "token_expires_at": token_claims.get("exp")
            },
            "token_metadata": {
                "issuer": token_claims.get("iss"),
                "audience": token_claims.get("aud"),
                "scopes": token_claims.get("scope", "").split()
            }
        }
    except Exception as e:
        logger.error(f"Error processing CyberArk token: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to process token: {str(e)}",
            "connected": False
        }


async def handle_cyberark_connect() -> Dict[str, Any]:
    """
    Wrapper function to trigger CyberArk OAuth flow.
    This is called by the backend API endpoint.
    """
    return await connect_cyberark()
```


### Step 2: Update Backend API

**File**: `backend/main.py`

Add this endpoint after existing `/council` and `/dxo` endpoints:

```python
@app.post("/api/cyberark/connect")
async def cyberark_connect():
    """
    Triggers CyberArk OAuth flow and returns user information.
    This is a demo endpoint to validate OAuth integration.
    """
    try:
        # Import the agent tool
        from agents.cyberark_demo_tool import handle_cyberark_connect

        # Trigger OAuth flow
        result = await handle_cyberark_connect()

        return result
    except Exception as e:
        logger.error(f"CyberArk connection error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to connect to CyberArk: {str(e)}"
        )
```

### Step 3: Create React Component

**File**: `frontend/src/components/CyberArkConnect.jsx`

```jsx
import React, { useState, useEffect } from 'react';
import './CyberArkConnect.css';

const CyberArkConnect = () => {
  const [connected, setConnected] = useState(false);
  const [userInfo, setUserInfo] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleConnect = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch('http://localhost:8001/api/cyberark/connect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });

      const data = await response.json();

      if (data.needs_auth && data.authorization_url) {
        // Open OAuth popup
        const popup = window.open(
          data.authorization_url,
          'CyberArk Authentication',
          'width=500,height=600,scrollbars=yes'
        );

        // Poll for popup closure (token exchange happens on backend)
        const pollTimer = setInterval(async () => {
          if (popup.closed) {
            clearInterval(pollTimer);
            // Re-call endpoint to get token after OAuth completion
            const retryResponse = await fetch('http://localhost:8001/api/cyberark/connect', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' }
            });
            const retryData = await retryResponse.json();

            if (retryData.connected) {
              setConnected(true);
              setUserInfo(retryData.user_info);
            }
            setLoading(false);
          }
        }, 1000);
      } else if (data.connected) {
        // Already connected (cached token)
        setConnected(true);
        setUserInfo(data.user_info);
        setLoading(false);
      } else {
        setError(data.message || 'Failed to connect');
        setLoading(false);
      }
    } catch (err) {
      setError(`Connection error: ${err.message}`);
      setLoading(false);
    }
  };

  const handleDisconnect = () => {
    setConnected(false);
    setUserInfo(null);
    // In production, you'd call an endpoint to revoke the token
  };

  const formatTimestamp = (timestamp) => {
    if (!timestamp) return 'N/A';
    return new Date(timestamp * 1000).toLocaleString();
  };

  return (
    <div className="cyberark-connect">
      <div className="cyberark-header">
        <h3>🔐 CyberArk Integration</h3>
        {connected ? (
          <span className="status-badge connected">✓ Connected</span>
        ) : (
          <span className="status-badge disconnected">○ Not Connected</span>
        )}
      </div>

      {!connected ? (
        <div className="connect-section">
          <p>Connect your CyberArk identity to access downstream services</p>
          <button
            onClick={handleConnect}
            disabled={loading}
            className="connect-button"
          >
            {loading ? '⏳ Connecting...' : '🔗 Connect CyberArk'}
          </button>
          {error && <p className="error-message">{error}</p>}
        </div>
      ) : (
        <div className="user-info-section">
          <div className="user-details">
            <h4>Connected User</h4>
            <p><strong>Name:</strong> {userInfo?.name || 'N/A'}</p>
            <p><strong>Email:</strong> {userInfo?.email || 'N/A'}</p>
            <p><strong>User ID:</strong> {userInfo?.user_id || 'N/A'}</p>
            <p><strong>Token Issued:</strong> {formatTimestamp(userInfo?.token_issued_at)}</p>
            <p><strong>Token Expires:</strong> {formatTimestamp(userInfo?.token_expires_at)}</p>
          </div>
          <button
            onClick={handleDisconnect}
            className="disconnect-button"
          >
            Disconnect
          </button>
        </div>
      )}
    </div>
  );
};

export default CyberArkConnect;
```

**File**: `frontend/src/components/CyberArkConnect.css`

```css
.cyberark-connect {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 24px;
  color: white;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.cyberark-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.cyberark-header h3 {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 600;
}

.status-badge {
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 0.875rem;
  font-weight: 500;
}

.status-badge.connected {
  background-color: rgba(16, 185, 129, 0.2);
  border: 2px solid #10b981;
}

.status-badge.disconnected {
  background-color: rgba(239, 68, 68, 0.2);
  border: 2px solid #ef4444;
}

.connect-section {
  text-align: center;
}

.connect-section p {
  margin-bottom: 16px;
  opacity: 0.9;
}

.connect-button {
  background-color: white;
  color: #667eea;
  border: none;
  padding: 12px 24px;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.connect-button:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.connect-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.error-message {
  margin-top: 12px;
  padding: 8px;
  background-color: rgba(239, 68, 68, 0.2);
  border-radius: 6px;
  font-size: 0.875rem;
}

.user-info-section {
  background-color: rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  padding: 16px;
}

.user-details h4 {
  margin-top: 0;
  margin-bottom: 12px;
  font-size: 1.125rem;
}

.user-details p {
  margin: 8px 0;
  font-size: 0.875rem;
  opacity: 0.95;
}

.user-details strong {
  font-weight: 600;
  margin-right: 8px;
}

.disconnect-button {
  margin-top: 16px;
  background-color: rgba(239, 68, 68, 0.8);
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 0.875rem;
  cursor: pointer;
  transition: background-color 0.3s ease;
}

.disconnect-button:hover {
  background-color: rgba(239, 68, 68, 1);
}
```

### Step 4: Integrate Component into App

**File**: `frontend/src/App.jsx`

Add import at the top:
```jsx
import CyberArkConnect from './components/CyberArkConnect';
```

Add component before mode selector (around line 50-60):
```jsx
<div className="app-container">
  <h1>Deep Research Agent</h1>

  {/* Add CyberArk integration */}
  <CyberArkConnect />

  {/* Existing mode selector */}
  <div className="mode-selector">
    {/* ... existing code ... */}
  </div>
</div>
```

### Step 5: Update IAM Permissions

The Lambda function (or local AgentCore runtime) needs permissions to access AgentCore Identity and Token Vault.

**For Lambda**: Update `lambda/agentcore_proxy.py` execution role with these permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock-agentcore:GetWorkloadAccessToken",
        "bedrock-agentcore:GetResourceOauth2Token",
        "bedrock-agentcore:InvokeAgent"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:*:*:secret:bedrock-agentcore/*"
    }
  ]
}
```

## Troubleshooting

### Issue: "Provider not found"
**Cause**: Provider name mismatch between code and AWS configuration
**Fix**: Verify `provider_name` in `cyberark_demo_tool.py` matches exactly in AWS console

### Issue: "Invalid redirect URI"
**Cause**: Callback URL not registered in CyberArk app
**Fix**: Copy callback URL from AWS and add to CyberArk app's redirect URIs list

### Issue: "Insufficient permissions"
**Cause**: Lambda/AgentCore missing IAM permissions
**Fix**: Add permissions from Step 5, wait 1-2 minutes for propagation

### Issue: Popup blocked
**Cause**: Browser blocking popup
**Fix**: Allow popups for localhost:5173 or use browser extension

### Issue: "Token expired"
**Cause**: Cached token has expired
**Fix**: Set `force_authentication=True` in decorator to force new token

## Success Criteria

✅ Button appears in frontend UI
✅ Clicking button opens CyberArk OAuth popup
✅ User can authenticate with CyberArk credentials
✅ UI displays connection status and user info
✅ Token is cached for subsequent requests
✅ No errors in browser console or backend logs

---

## Phase 2: Dynamic Authentication During Agent Execution

**Status**: Future enhancement after Phase 1 (button demo) is working

### Overview

Phase 2 implements the **real power** of AgentCore outbound authentication: agents that automatically trigger OAuth when they need to access protected resources during execution.

**User Experience**:
```
User: "Research CyberArk's PAM architecture using our internal docs"
  → Agent starts research
  → Agent realizes it needs internal CyberArk documentation
  → Agent triggers OAuth automatically
  → User sees popup: "Agent needs access to internal docs"
  → User authenticates
  → Agent continues with access and completes research
```

**No manual "Connect" button needed** - authentication happens inline when required!

### Architecture: Dynamic Auth Flow

```
User asks question with agent
    ↓
Agent starts processing
    ↓
Agent calls tool that needs auth (e.g., search_internal_docs)
    ↓
Tool decorated with @requires_access_token
    ↓
No token found → Returns authorization_url to frontend
    ↓
Frontend detects needs_auth: true in response
    ↓
Frontend opens OAuth popup automatically
    ↓
User authenticates with CyberArk
    ↓
Popup closes, token cached in AgentCore Token Vault
    ↓
Frontend automatically retries same question
    ↓
Agent calls tool again → Token now exists
    ↓
Tool accesses protected resource with token
    ↓
Agent completes execution with protected data
    ↓
Frontend displays complete results
```

### Implementation Steps

#### Step 1: Create Tool for Protected Resource

**File**: `agents/tools/cyberark_internal_search.py`

```python
"""
CyberArk internal documentation search tool.
Requires user authentication to access internal resources.
"""

import requests
import logging
from typing import Dict, Any, List
from bedrock_agentcore.identity.auth import requires_access_token

logger = logging.getLogger(__name__)


@requires_access_token(
    provider_name="CyberArk-Demo",  # ⚠️ REPLACE with actual provider name
    scopes=["openid", "profile", "email", "api.read"],
    auth_flow="USER_FEDERATION",
    on_auth_url=lambda url: {
        "needs_auth": True,
        "authorization_url": url,
        "message": "Agent needs access to CyberArk internal documentation to answer your question",
        "required_scopes": ["api.read"]
    },
    force_authentication=False,
    callback_url='INSERT_CALLBACK_URL_HERE'  # ⚠️ REPLACE
)
async def search_cyberark_internal_docs(
    query: str,
    max_results: int = 5,
    *,
    access_token: str  # Injected by decorator
) -> Dict[str, Any]:
    """
    Search internal CyberArk documentation (protected resource).

    This tool automatically triggers OAuth if the user hasn't authenticated yet.
    The agent can call this tool during execution and authentication will happen seamlessly.

    Args:
        query: Search query
        max_results: Maximum number of results to return
        access_token: OAuth access token (injected by decorator)

    Returns:
        Dictionary with search results or auth requirement
    """
    try:
        # In production, this would be your internal CyberArk API
        # For demo, we'll simulate with a public API or mock data

        # Example: Call internal documentation API
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        # DEMO: Replace this with actual internal API
        # response = requests.get(
        #     "https://internal-docs.cyberark.yourcompany.com/api/v1/search",
        #     headers=headers,
        #     params={"q": query, "limit": max_results},
        #     timeout=10
        # )
        # docs = response.json()

        # For demo purposes, return mock data
        logger.info(f"Searching internal docs for: {query}")
        docs = [
            {
                "title": f"Internal Doc: {query} - Architecture Overview",
                "content": "Detailed internal architecture documentation for CyberArk PAM...",
                "url": "https://internal-docs.cyberark.example.com/arch",
                "last_updated": "2024-12-15"
            },
            {
                "title": f"Internal Doc: {query} - Security Guidelines",
                "content": "Internal security implementation guidelines...",
                "url": "https://internal-docs.cyberark.example.com/security",
                "last_updated": "2024-12-10"
            }
        ]

        logger.info(f"Found {len(docs)} internal documents")

        return {
            "status": "success",
            "query": query,
            "results": docs,
            "count": len(docs),
            "source": "CyberArk Internal Documentation",
            "authenticated": True
        }

    except requests.exceptions.RequestException as e:
        logger.error(f"Error accessing internal docs: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to access internal documentation: {str(e)}",
            "results": []
        }


def format_search_results_for_llm(results: List[Dict[str, Any]]) -> str:
    """
    Format search results for LLM consumption.

    Args:
        results: List of search result dictionaries

    Returns:
        Formatted string for LLM context
    """
    if not results:
        return "No internal documentation found."

    formatted = "# Internal CyberArk Documentation\n\n"

    for i, doc in enumerate(results, 1):
        formatted += f"""## Document {i}: {doc['title']}

**Source**: {doc.get('url', 'Internal')}
**Last Updated**: {doc.get('last_updated', 'N/A')}

**Content**:
{doc['content']}

---

"""

    return formatted
```

**Action Items**:
- [ ] Replace provider name and callback URL
- [ ] Update API endpoint to actual internal documentation URL
- [ ] Configure appropriate scopes for your CyberArk API
- [ ] Test tool independently before integrating with agents

#### Step 2: Integrate Tool into Council Agent

**File**: `agents/council_agent.py`

Modify the `stage1_collect_responses` method to use internal docs when relevant:

```python
async def stage1_collect_responses(self, question: str) -> List[Dict[str, str]]:
    """
    Stage 1: Collect parallel responses from council members.
    Enhanced with dynamic authentication for internal resources.
    """
    logger.info(f"Stage 1: Collecting responses for question: {question[:100]}...")

    # Check if question requires internal CyberArk documentation
    internal_context = None
    needs_auth_response = None

    if self._requires_internal_docs(question):
        logger.info("Question requires internal documentation, attempting search...")

        from agents.tools.cyberark_internal_search import (
            search_cyberark_internal_docs,
            format_search_results_for_llm
        )

        try:
            # Try to search internal docs
            search_result = await search_cyberark_internal_docs(
                query=question,
                max_results=5
            )

            # Check if authentication is needed
            if search_result.get("needs_auth"):
                logger.info("Authentication required, returning auth URL to user")
                # Return auth requirement to frontend
                needs_auth_response = search_result
            elif search_result.get("status") == "success":
                # Got results, format for LLM
                internal_context = format_search_results_for_llm(
                    search_result["results"]
                )
                logger.info(f"Retrieved {search_result['count']} internal documents")

        except Exception as e:
            logger.warning(f"Could not access internal docs: {str(e)}")
            # Continue without internal docs

    # If auth is needed, return that immediately
    if needs_auth_response:
        return [needs_auth_response]

    # Build system prompt with optional internal context
    system_prompt = """You are a knowledgeable AI assistant and member of a research council.
Provide a thoughtful, well-reasoned response to the user's question.
Be analytical and consider multiple perspectives.
Keep your response concise but comprehensive (300-500 words)."""

    if internal_context:
        system_prompt += f"""

You have access to internal documentation that may be relevant:

{internal_context}

Use this internal documentation to provide more accurate and detailed insights."""

    # Create tasks for parallel execution
    tasks = []
    for i in range(self.num_members):
        tasks.append(
            self.bedrock_client.invoke_async(
                system_prompt=system_prompt,
                user_message=question,
                temperature=0.7 + (i * 0.1)
            )
        )

    # Execute in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results
    responses = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"Council member {i+1} failed: {str(result)}")
            continue

        responses.append({
            'member_id': f"Member {i+1}",
            'content': result['content'],
            'usage': result.get('usage', {}),
            'used_internal_docs': internal_context is not None
        })

    logger.info(f"Stage 1 complete: {len(responses)} responses collected")
    return responses


def _requires_internal_docs(self, question: str) -> bool:
    """
    Determine if question requires internal documentation.

    Args:
        question: User's question

    Returns:
        True if internal docs should be searched
    """
    # Simple keyword matching (can be enhanced with LLM classification)
    internal_keywords = [
        'cyberark internal',
        'internal documentation',
        'internal architecture',
        'our cyberark',
        'company cyberark',
        'internal implementation',
        'proprietary',
        'confidential'
    ]

    question_lower = question.lower()
    return any(keyword in question_lower for keyword in internal_keywords)
```

**Action Items**:
- [ ] Add import for tool at top of file
- [ ] Test `_requires_internal_docs()` logic with sample questions
- [ ] Verify internal context is properly formatted for LLM

#### Step 3: Update Backend to Handle Auth Responses

**File**: `backend/main.py`

Modify the council endpoint to detect and forward auth requirements:

```python
@app.post("/api/council", response_model=CouncilResponse)
async def run_council(request: ResearchRequest):
    """
    Run LLM Council 3-stage deliberation.
    Enhanced to handle dynamic authentication.
    """
    try:
        logger.info(f"Council request: {request.question[:100]}...")

        if not council_agent:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Council agent not initialized"
            )

        # Run council deliberation
        result = await council_agent.deliberate(request.question)

        # Check if stage1 returned auth requirement
        if isinstance(result.get('stage1'), list) and len(result['stage1']) > 0:
            first_response = result['stage1'][0]
            if isinstance(first_response, dict) and first_response.get('needs_auth'):
                # Return auth requirement to frontend
                logger.info("Returning authentication requirement to frontend")
                return JSONResponse(
                    status_code=200,
                    content={
                        "needs_auth": True,
                        "authorization_url": first_response['authorization_url'],
                        "message": first_response.get('message', 'Authentication required'),
                        "required_scopes": first_response.get('required_scopes', [])
                    }
                )

        # Normal response path
        response = CouncilResponse(
            question=result['question'],
            stage1=result['stage1'],
            stage2=result['stage2'],
            stage3=result['stage3'],
            metadata=result['metadata']
        )

        logger.info("Council deliberation completed successfully")
        return response

    except Exception as e:
        logger.error(f"Council error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Council deliberation failed: {str(e)}"
        )
```

**Action Items**:
- [ ] Import JSONResponse from fastapi.responses
- [ ] Test auth detection logic
- [ ] Verify normal responses still work correctly

#### Step 4: Update Frontend to Handle Dynamic Auth

**File**: `frontend/src/App.jsx`

Enhance the `handleSubmit` function to detect and handle authentication:

```javascript
const handleSubmit = async (question) => {
    setLoading(true)
    setError(null)
    setResult(null)

    try {
        let data

        // Call appropriate agent
        if (mode === 'council') {
            data = await runCouncil(question)
        } else {
            data = await runDxO(question)
        }

        // Check if agent needs authentication
        if (data.needs_auth && data.authorization_url) {
            logger.info('Agent requires authentication, opening popup...')

            // Show user-friendly message
            setError(`Agent needs access: ${data.message || 'Authentication required'}`)

            // Open OAuth popup
            const popup = window.open(
                data.authorization_url,
                'Authenticate to Continue',
                'width=500,height=600,scrollbars=yes'
            )

            if (!popup) {
                throw new Error('Popup blocked. Please allow popups for this site.')
            }

            // Poll for popup closure
            const pollTimer = setInterval(async () => {
                if (popup.closed) {
                    clearInterval(pollTimer)

                    logger.info('Authentication completed, retrying request...')
                    setError(null)

                    // Retry the same request (token should now be cached)
                    try {
                        let retryData
                        if (mode === 'council') {
                            retryData = await runCouncil(question)
                        } else {
                            retryData = await runDxO(question)
                        }

                        // Check if still needs auth (shouldn't happen)
                        if (retryData.needs_auth) {
                            throw new Error('Authentication failed. Please try again.')
                        }

                        setResult(retryData)
                    } catch (retryErr) {
                        console.error('Retry error:', retryErr)
                        setError(retryErr.response?.data?.detail || retryErr.message)
                    } finally {
                        setLoading(false)
                    }
                }
            }, 1000)
        } else {
            // Normal response, no auth needed
            setResult(data)
            setLoading(false)
        }

    } catch (err) {
        console.error('Error:', err)
        setError(err.response?.data?.detail || err.message || 'An error occurred')
        setLoading(false)
    }
}
```

**Optional: Add visual indicator for authenticated requests**

```javascript
// In your results display
{result && result.metadata?.used_internal_docs && (
    <div className="internal-docs-badge">
        🔐 Includes internal documentation
    </div>
)}
```

**Action Items**:
- [ ] Test popup handling on different browsers
- [ ] Add loading state during authentication
- [ ] Test retry logic after successful auth

#### Step 5: Enhance DxO Agent (Optional)

Apply the same pattern to DxO agent for lead researcher:

**File**: `agents/dxo_agent.py`

```python
async def lead_researcher_initial(self, question: str) -> Dict[str, Any]:
    """
    Role 1: Lead Researcher conducts initial research.
    Enhanced with internal documentation access.
    """
    logger.info("DxO Step 1: Lead Researcher - Initial research...")

    # Search public arXiv
    arxiv_results = self._search_arxiv(question)

    # Try to search internal docs if relevant
    internal_docs = None
    if self._requires_internal_docs(question):
        from agents.tools.cyberark_internal_search import (
            search_cyberark_internal_docs,
            format_search_results_for_llm
        )

        try:
            search_result = await search_cyberark_internal_docs(
                query=question,
                max_results=5
            )

            # Check if auth needed
            if search_result.get("needs_auth"):
                return search_result  # Return auth requirement

            if search_result.get("status") == "success":
                internal_docs = format_search_results_for_llm(
                    search_result["results"]
                )
        except Exception as e:
            logger.warning(f"Could not access internal docs: {str(e)}")

    # Continue with research using both public and internal sources
    system_prompt = """You are a lead researcher conducting initial research.

Your responsibilities:
1. Analyze the research question thoroughly
2. Review provided academic papers and internal documentation
3. Synthesize key findings
4. Propose a research approach"""

    sources = f"""Relevant Academic Papers from arXiv:
{arxiv_results}"""

    if internal_docs:
        sources += f"""

Internal Documentation (Authenticated Access):
{internal_docs}"""

    user_message = f"""Research Question: {question}

{sources}

Based on these sources, provide your initial research findings."""

    result = await self.bedrock_client.invoke_async(
        system_prompt=system_prompt,
        user_message=user_message,
        temperature=0.7,
        max_tokens=2000
    )

    return {
        'role': 'Lead Researcher',
        'step': 'Initial Research',
        'content': result['content'],
        'papers': arxiv_results,
        'internal_docs_used': internal_docs is not None,
        'usage': result.get('usage', {})
    }
```

### Testing Phase 2

#### Test Case 1: Question Requiring Auth

```bash
# Question that triggers internal doc search
Question: "Explain CyberArk's internal PAM architecture based on our documentation"

Expected Flow:
1. Agent starts processing
2. Detects need for internal docs
3. Calls search_cyberark_internal_docs()
4. Returns needs_auth: true
5. Frontend shows popup
6. User authenticates
7. Request retries automatically
8. Agent completes with internal docs
9. Response indicates "🔐 Includes internal documentation"
```

#### Test Case 2: Question NOT Requiring Auth

```bash
# Public question
Question: "What is quantum computing?"

Expected Flow:
1. Agent processes normally
2. No internal doc search triggered
3. Uses only public knowledge
4. Returns response immediately
5. No authentication popup
```

#### Test Case 3: Cached Token

```bash
# User already authenticated in Phase 1
Question: "Compare CyberArk with Hashicorp Vault using internal docs"

Expected Flow:
1. Agent detects need for internal docs
2. Calls search_cyberark_internal_docs()
3. Token already cached in Token Vault
4. No auth popup (seamless)
5. Returns results with internal docs immediately
```

### User Experience Comparison

**Phase 1 (Button)**:
```
User: Clicks "Connect CyberArk" → Authenticates → Connected
User: Asks question → Agent uses cached token → Response
```

**Phase 2 (Dynamic)**:
```
User: Asks question requiring auth
  → Agent triggers OAuth inline → User authenticates in popup
  → Agent continues automatically → Response with protected data
```

**Phase 1 + Phase 2 (Best UX)**:
```
Option A: User connects first → All subsequent questions work seamlessly
Option B: User asks question → Auth happens automatically → Cached for future
```

### Real-World Use Cases

Once Phase 2 is working, you can add tools for:

```python
# Lab data access
@requires_access_token(provider_name="CyberArk")
async def get_experiment_results(experiment_id: str, *, access_token: str):
    """Retrieve lab experiment data"""
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(f"https://lab-api.company.com/experiments/{experiment_id}", headers=headers)
    return response.json()

# Internal research database
@requires_access_token(provider_name="CyberArk")
async def search_research_database(query: str, *, access_token: str):
    """Search internal research papers"""
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.post("https://research-db.company.com/search",
                            headers=headers, json={"query": query})
    return response.json()

# Security reports
@requires_access_token(provider_name="CyberArk")
async def get_security_report(report_id: str, *, access_token: str):
    """Fetch confidential security reports"""
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(f"https://security.company.com/reports/{report_id}", headers=headers)
    return response.json()
```

Then your agents can say:
- *"Summarize experiment #12345"* → Auto-auth to lab API
- *"What do our internal research papers say about quantum?"* → Auto-auth to research DB
- *"Analyze security report VULN-2024-001"* → Auto-auth to security system

### Success Criteria (Phase 2)

✅ Agent detects when it needs protected resources
✅ Tool triggers OAuth automatically during execution
✅ Frontend handles auth popup seamlessly
✅ Request retries automatically after authentication
✅ Token is cached for subsequent requests
✅ Agent successfully accesses protected resource
✅ Response includes data from protected resource
✅ User experience is smooth (minimal disruption)
✅ Error handling works for auth failures

---

## Next Steps After POC

Once both Phase 1 and Phase 2 are working:

1. **Production-Grade Internal APIs**:
   - Replace mock data with actual internal API calls
   - Configure proper API endpoints in AgentCore Gateway
   - Test with real enterprise resources

2. **Enhanced Error Handling**:
   - Token refresh logic
   - Graceful degradation if CyberArk unavailable
   - User-friendly error messages
   - Retry logic for transient failures

3. **Token Management UI**:
   - Show token expiry countdown
   - Manual refresh button
   - Revoke token functionality
   - View active sessions

4. **Security Hardening**:
   - Enable token signature verification
   - Add PKCE to OAuth flow
   - Implement token rotation
   - Audit logging for all auth events

5. **Multi-Provider Support**:
   - Add other OAuth providers (Okta, Auth0, Azure AD)
   - Provider selection UI
   - Provider-specific scopes
   - Multiple simultaneous providers

6. **Advanced Agent Capabilities**:
   - Multi-step workflows requiring multiple auth providers
   - Conditional access based on user role
   - Federated identity across multiple systems
   - Session-based access patterns

## References

- [AgentCore Gateway Outbound Auth](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-outbound-auth.html)
- [CyberArk as IdP for AgentCore](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/identity-idp-cyberark.html)
- [CyberArk OAuth App Setup](https://docs.cyberark.com/identity/latest/en/content/applications/appscustom/openidaddconfigapp.htm)
- [AgentCore Identity Authentication](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/identity-authentication.html)

---

**Document Status**: Ready for implementation
**Last Updated**: 2025-12-25

**Phase 1 (Button Demo)**:
- Implementation Time: ~2-3 hours (after prerequisites complete)
- Complexity: Medium
- Risk Level: Low (isolated POC, no production dependencies)

**Phase 2 (Dynamic Auth)**:
- Implementation Time: ~4-6 hours (after Phase 1 complete)
- Complexity: Medium-High
- Risk Level: Low (extends Phase 1, graceful degradation if auth fails)

**Total Implementation**: ~6-9 hours for both phases
