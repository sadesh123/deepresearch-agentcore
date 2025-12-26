# AgentCore Gateway Setup with CyberArk Inbound Authentication

## Architecture Overview

```
┌──────────┐         ┌──────────┐        ┌─────────────────┐        ┌──────────┐
│  Client  │         │ CyberArk │        │  AgentCore      │        │  Target  │
│   App    │         │ Identity │        │    Gateway      │        │ (Agent)  │
└────┬─────┘         └────┬─────┘        └────────┬────────┘        └─────┬────┘
     │                    │                       │                       │
     │ 1. OAuth Login     │                       │                       │
     ├───────────────────>│                       │                       │
     │                    │                       │                       │
     │ 2. JWT Token       │                       │                       │
     │<───────────────────┤                       │                       │
     │                    │                       │                       │
     │ 3. POST /invocations with Bearer Token     │                       │
     ├───────────────────────────────────────────>│                       │
     │                    │                       │                       │
     │                    │ 4. Validate JWT       │                       │
     │                    │    - Discovery URL    │                       │
     │                    │    - Client ID        │                       │
     │                    │    - Audience         │                       │
     │                    │    - Scopes           │                       │
     │                    │<──────────────────────┤                       │
     │                    │                       │                       │
     │                    │                       │ 5. Route to Target    │
     │                    │                       ├──────────────────────>│
     │                    │                       │                       │
     │                    │                       │ 6. Target Response    │
     │                    │                       │<──────────────────────┤
     │                    │                       │                       │
     │ 7. Gateway Response│                       │                       │
     │<───────────────────────────────────────────┤                       │
```

## What is an AgentCore Gateway?

An **AgentCore Gateway** is a managed service layer that:
- **Authenticates** incoming requests (inbound auth)
- **Routes** requests to targets (MCP servers, Lambda functions, REST APIs, etc.)
- **Manages** outbound authentication to downstream services
- **Enforces** authorization policies and rate limiting

### Gateway vs Direct Agent Runtime Invocation

| Aspect | Gateway | Direct Agent Runtime |
|--------|---------|---------------------|
| **Entry Point** | `/gateway/{gateway-id}/invocations` | `/runtimes/{agent-arn}/invocations` |
| **Auth Options** | JWT, IAM SigV4, No Auth | JWT only (via authorizer config) |
| **Routing** | Multiple targets (MCP, Lambda, REST API) | Single agent container |
| **Management** | Managed service, auto-scaling | User-managed container |
| **Use Case** | Multi-tool orchestration | Single agent execution |

## Your CyberArk Configuration

Based on your existing setup:

```yaml
Tenant: <your-cyberark-tenant>.id.cyberark.cloud
Client ID: <your-client-id>
Discovery URL: https://<your-cyberark-tenant>.id.cyberark.cloud/.well-known/openid-configuration
Authorization Endpoint: https://<your-cyberark-tenant>.id.cyberark.cloud/OAuth2/Authorize/agentcoredemo
Token Endpoint: https://<your-cyberark-tenant>.id.cyberark.cloud/OAuth2/Token/agentcoredemo
Issuer: https://<your-cyberark-tenant>.id.cyberark.cloud
Scopes: openid, profile, email
```

## Gateway Setup Steps

### Step 1: Verify CyberArk OpenID Configuration

First, verify your CyberArk discovery URL is accessible:

```bash
curl https://<your-cyberark-tenant>.id.cyberark.cloud/.well-known/openid-configuration | jq
```

Expected response should include:
```json
{
  "issuer": "https://<your-cyberark-tenant>.id.cyberark.cloud",
  "authorization_endpoint": "https://<your-cyberark-tenant>.id.cyberark.cloud/OAuth2/Authorize/...",
  "token_endpoint": "https://<your-cyberark-tenant>.id.cyberark.cloud/OAuth2/Token/...",
  "jwks_uri": "https://<your-cyberark-tenant>.id.cyberark.cloud/.well-known/jwks",
  "response_types_supported": ["code", "token", "id_token"],
  "subject_types_supported": ["public"],
  "id_token_signing_alg_values_supported": ["RS256"],
  "scopes_supported": ["openid", "profile", "email"]
}
```

### Step 2: Configure Redirect URI in CyberArk

In your CyberArk application configuration, ensure the **redirect URI** is set to:

```
https://bedrock-agentcore.us-east-1.amazonaws.com/identities/oauth2/callback
```

**Note:** Replace `us-east-1` with your AWS region if different.

### Step 3: Create Gateway with JWT Inbound Auth

#### Option A: Using AWS Console (Recommended for First Setup)

1. Navigate to **Amazon Bedrock AgentCore** → **Gateways**
2. Click **Create Gateway**
3. Fill in **Gateway Details**:
   - **Gateway name**: `deep-research-gateway` (a-z, A-Z, 0-9, hyphen, max 50 chars)
   - **Description**: "Gateway for Deep Research Agent with CyberArk authentication"

4. **Inbound Auth Configuration**:
   - Select: **Use JSON Web Tokens (JWT)**
   - JWT schema: **Use existing Identity provider configurations**
   - **Discovery URL**: `https://<your-cyberark-tenant>.id.cyberark.cloud/.well-known/openid-configuration`

5. **JWT Authorization Configuration**:
   ```yaml
   Allowed audiences: (Optional - leave blank or specify your app URL)
   Allowed clients: <your-client-id>
   Allowed scopes: openid, profile, email
   Custom claims: (Optional - leave blank)
   ```

6. **IAM Permissions**:
   - Select: **Create and use a new service role**
   - Service role name: `deep-research-gateway-role` (auto-generated)

7. **Target Configuration**:
   - **Target name**: `deep-research-agent-target`
   - **Target type**: Select based on your agent implementation:
     - **MCP server**: If using Model Context Protocol
     - **Lambda ARN**: If agent is deployed as Lambda
     - **REST API**: If agent exposes REST endpoints
     - **API Gateway**: If using existing API Gateway

8. For **REST API** target type:
   - **API endpoint**: Your agent's base URL (e.g., `http://localhost:8001` for dev)
   - **OpenAPI schema**: Upload your agent's OpenAPI spec or define inline

9. **Outbound Auth** (for target):
   - Select: **No authorization** (if agent doesn't need outbound auth)
   - Or configure OAuth client if agent needs to access external services

10. Click **Create Gateway**

#### Option B: Using AWS CLI

```bash
aws bedrock-agentcore-control create-gateway \
  --gateway-name deep-research-gateway \
  --authorizer-configuration '{
    "customJWTAuthorizer": {
      "discoveryUrl": "https://<your-cyberark-tenant>.id.cyberark.cloud/.well-known/openid-configuration",
      "allowedClients": ["<your-client-id>"],
      "allowedScopes": ["openid", "profile", "email"]
    }
  }' \
  --targets '[
    {
      "name": "deep-research-agent-target",
      "type": "REST_API",
      "configuration": {
        "baseUrl": "http://localhost:8001",
        "authorizationType": "NONE"
      }
    }
  ]' \
  --service-role-arn arn:aws:iam::ACCOUNT_ID:role/deep-research-gateway-role \
  --region us-east-1
```

#### Option C: Using Python Boto3

```python
import boto3

client = boto3.client('bedrock-agentcore-control', region_name='us-east-1')

response = client.create_gateway(
    gatewayName='deep-research-gateway',
    authorizerConfiguration={
        'customJWTAuthorizer': {
            'discoveryUrl': 'https://<your-cyberark-tenant>.id.cyberark.cloud/.well-known/openid-configuration',
            'allowedClients': ['<your-client-id>'],
            'allowedScopes': ['openid', 'profile', 'email']
        }
    },
    targets=[
        {
            'name': 'deep-research-agent-target',
            'type': 'REST_API',
            'configuration': {
                'baseUrl': 'http://localhost:8001',
                'authorizationType': 'NONE'
            }
        }
    ],
    serviceRoleArn='arn:aws:iam::ACCOUNT_ID:role/deep-research-gateway-role'
)

print(f"Gateway ID: {response['gatewayId']}")
print(f"Gateway ARN: {response['gatewayArn']}")
print(f"Gateway Endpoint: https://bedrock-agentcore.us-east-1.amazonaws.com/gateway/{response['gatewayId']}/invocations")
```

### Step 4: Note Gateway Endpoint

After creation, note the gateway endpoint:
```
https://bedrock-agentcore.us-east-1.amazonaws.com/gateway/{GATEWAY_ID}/invocations
```

This is the URL your frontend will call (instead of the agent runtime URL).

## Client Implementation

### Step 1: Implement CyberArk OAuth Flow (Frontend)

```javascript
// src/services/cyberark-auth.js
export class CyberArkAuth {
  constructor() {
    this.clientId = '<your-client-id>';
    this.authEndpoint = 'https://<your-cyberark-tenant>.id.cyberark.cloud/OAuth2/Authorize/agentcoredemo';
    this.tokenEndpoint = 'https://<your-cyberark-tenant>.id.cyberark.cloud/OAuth2/Token/agentcoredemo';
    this.redirectUri = 'http://localhost:5173/callback';
    this.scopes = 'openid profile email';
  }

  // Generate code verifier and challenge for PKCE
  generatePKCE() {
    const verifier = this.base64URLEncode(crypto.getRandomValues(new Uint8Array(32)));
    const challenge = this.base64URLEncode(
      new Uint8Array(Array.from(new TextEncoder().encode(verifier)))
    );

    return { verifier, challenge };
  }

  base64URLEncode(buffer) {
    return btoa(String.fromCharCode(...buffer))
      .replace(/\+/g, '-')
      .replace(/\//g, '_')
      .replace(/=/g, '');
  }

  // Step 1: Redirect to CyberArk for authentication
  async login() {
    const { verifier, challenge } = this.generatePKCE();

    // Store verifier for token exchange
    sessionStorage.setItem('pkce_verifier', verifier);

    const state = Math.random().toString(36).substring(7);
    sessionStorage.setItem('oauth_state', state);

    const authUrl = `${this.authEndpoint}?` +
      `client_id=${encodeURIComponent(this.clientId)}` +
      `&redirect_uri=${encodeURIComponent(this.redirectUri)}` +
      `&response_type=code` +
      `&scope=${encodeURIComponent(this.scopes)}` +
      `&state=${state}` +
      `&code_challenge=${challenge}` +
      `&code_challenge_method=S256`;

    window.location.href = authUrl;
  }

  // Step 2: Handle callback and exchange code for token
  async handleCallback() {
    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get('code');
    const state = urlParams.get('state');

    // Verify state
    const savedState = sessionStorage.getItem('oauth_state');
    if (state !== savedState) {
      throw new Error('Invalid state parameter');
    }

    // Exchange code for token
    const verifier = sessionStorage.getItem('pkce_verifier');

    const response = await fetch(this.tokenEndpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      body: new URLSearchParams({
        grant_type: 'authorization_code',
        code: code,
        redirect_uri: this.redirectUri,
        client_id: this.clientId,
        code_verifier: verifier
      })
    });

    if (!response.ok) {
      throw new Error('Token exchange failed');
    }

    const data = await response.json();

    // Store tokens securely
    this.storeTokens(data.access_token, data.refresh_token, data.expires_in);

    return data.access_token;
  }

  storeTokens(accessToken, refreshToken, expiresIn) {
    const expiryTime = Date.now() + (expiresIn * 1000);
    localStorage.setItem('cyberark_access_token', accessToken);
    localStorage.setItem('cyberark_refresh_token', refreshToken);
    localStorage.setItem('cyberark_token_expiry', expiryTime);
  }

  getAccessToken() {
    const token = localStorage.getItem('cyberark_access_token');
    const expiry = localStorage.getItem('cyberark_token_expiry');

    if (!token || Date.now() >= parseInt(expiry)) {
      return null; // Token expired
    }

    return token;
  }

  async refreshAccessToken() {
    const refreshToken = localStorage.getItem('cyberark_refresh_token');

    const response = await fetch(this.tokenEndpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      body: new URLSearchParams({
        grant_type: 'refresh_token',
        refresh_token: refreshToken,
        client_id: this.clientId
      })
    });

    const data = await response.json();
    this.storeTokens(data.access_token, data.refresh_token, data.expires_in);

    return data.access_token;
  }

  logout() {
    localStorage.removeItem('cyberark_access_token');
    localStorage.removeItem('cyberark_refresh_token');
    localStorage.removeItem('cyberark_token_expiry');
    sessionStorage.removeItem('pkce_verifier');
    sessionStorage.removeItem('oauth_state');
  }
}
```

### Step 2: Update API Client to Use Gateway

```javascript
// src/services/gateway-api.js
import { CyberArkAuth } from './cyberark-auth';

const auth = new CyberArkAuth();
const GATEWAY_URL = 'https://bedrock-agentcore.us-east-1.amazonaws.com/gateway/{GATEWAY_ID}/invocations';

export async function invokeGateway(prompt, mode) {
  // Get valid token (refresh if needed)
  let token = auth.getAccessToken();

  if (!token) {
    // Redirect to login
    auth.login();
    return;
  }

  try {
    const response = await fetch(GATEWAY_URL, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
        'X-Amzn-Bedrock-AgentCore-Gateway-Session-Id': generateSessionId()
      },
      body: JSON.stringify({
        prompt: prompt,
        mode: mode
      })
    });

    if (response.status === 401) {
      // Token expired, try refresh
      token = await auth.refreshAccessToken();
      return invokeGateway(prompt, mode); // Retry
    }

    if (!response.ok) {
      throw new Error(`Gateway error: ${response.status}`);
    }

    return response.json();
  } catch (error) {
    console.error('Gateway invocation error:', error);
    throw error;
  }
}

function generateSessionId() {
  return `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}
```

### Step 3: Update Frontend Components

```javascript
// src/components/Login.jsx
import React, { useEffect } from 'react';
import { CyberArkAuth } from '../services/cyberark-auth';

const auth = new CyberArkAuth();

export function Login() {
  const handleLogin = () => {
    auth.login();
  };

  return (
    <div className="login-container">
      <h2>Login with CyberArk</h2>
      <button onClick={handleLogin}>
        Sign In
      </button>
    </div>
  );
}

// src/components/AuthCallback.jsx
export function AuthCallback() {
  useEffect(() => {
    const handleAuth = async () => {
      try {
        await auth.handleCallback();
        // Redirect to main app
        window.location.href = '/';
      } catch (error) {
        console.error('Authentication failed:', error);
      }
    };

    handleAuth();
  }, []);

  return <div>Completing authentication...</div>;
}
```

## Backend Agent Updates

Your backend agent doesn't need to change much - the gateway handles authentication. However, you can extract user context from headers:

```python
# backend/main.py
@app.post("/api/council")
async def run_council(request: ResearchRequest, http_request: Request):
    """
    Run LLM Council with user context from gateway.

    The gateway forwards JWT claims as headers with prefix 'X-Amzn-Bedrock-AgentCore-'
    """
    # Extract user context from gateway headers
    user_id = http_request.headers.get('X-Amzn-Bedrock-AgentCore-User-Id')
    user_email = http_request.headers.get('X-Amzn-Bedrock-AgentCore-User-Email')
    client_id = http_request.headers.get('X-Amzn-Bedrock-AgentCore-Client-Id')

    logger.info(f"Council request from user: {user_email} (ID: {user_id})")

    # Your existing logic...
    result = await council_agent.deliberate(request.question)

    # Add user context to response metadata
    result['metadata']['user'] = {
        'id': user_id,
        'email': user_email,
        'client_id': client_id
    }

    return CouncilResponse(**result)
```

## Testing the Setup

### Step 1: Test CyberArk Token Generation

```bash
# Manual token generation for testing
curl -X POST https://<your-cyberark-tenant>.id.cyberark.cloud/OAuth2/Token/agentcoredemo \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=<your-client-id>" \
  -d "client_secret=YOUR_CLIENT_SECRET" \
  -d "scope=openid profile email"
```

### Step 2: Decode Token to Verify Claims

```bash
TOKEN="your-cyberark-token"

# Decode JWT payload
echo $TOKEN | cut -d '.' -f2 | base64 -d | jq

# Expected claims:
# {
#   "iss": "https://<your-cyberark-tenant>.id.cyberark.cloud",
#   "sub": "user-id",
#   "aud": "audience",
#   "client_id": "<your-client-id>",
#   "scope": "openid profile email",
#   "exp": 1234567890
# }
```

### Step 3: Test Gateway Invocation

```bash
GATEWAY_URL="https://bedrock-agentcore.us-east-1.amazonaws.com/gateway/{GATEWAY_ID}/invocations"
TOKEN="your-cyberark-token"

curl -X POST $GATEWAY_URL \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-Amzn-Bedrock-AgentCore-Gateway-Session-Id: test-session-123" \
  -d '{
    "prompt": "What is quantum computing?",
    "mode": "council"
  }'
```

### Expected Success Response

```json
{
  "output": {
    "message": {
      "role": "assistant",
      "content": [
        {
          "text": "# LLM Council Deliberation Results\n\n..."
        }
      ]
    },
    "timestamp": "2025-12-26T10:30:00Z"
  }
}
```

### Expected Error Responses

**401 Unauthorized (Invalid Token):**
```
HTTP/1.1 401 Unauthorized
WWW-Authenticate: Bearer error="invalid_token"
```

**403 Forbidden (Valid Token, Wrong Client ID):**
```json
{
  "error": "access_denied",
  "error_description": "Client ID not allowed"
}
```

## Troubleshooting

### Issue: "Invalid discovery URL"
**Cause:** Discovery URL not accessible or malformed
**Solution:**
```bash
# Verify discovery URL
curl https://<your-cyberark-tenant>.id.cyberark.cloud/.well-known/openid-configuration

# Ensure it returns valid JSON with required fields:
# - issuer
# - authorization_endpoint
# - token_endpoint
# - jwks_uri
```

### Issue: "Client ID not allowed"
**Cause:** Token's `client_id` claim doesn't match gateway configuration
**Solution:** Verify the client ID in gateway matches CyberArk application

### Issue: "Token signature verification failed"
**Cause:** Gateway can't fetch CyberArk's public keys
**Solution:**
```bash
# Verify JWKS endpoint is accessible
curl https://<your-cyberark-tenant>.id.cyberark.cloud/.well-known/jwks

# Ensure gateway's network allows outbound HTTPS to CyberArk
```

### Issue: "Audience validation failed"
**Cause:** Token's `aud` claim doesn't match allowed audiences
**Solution:**
- Option 1: Configure CyberArk to include correct audience in tokens
- Option 2: Leave "Allowed audiences" blank in gateway config (less secure)

### Issue: "CORS error in browser"
**Cause:** Gateway doesn't support direct browser calls
**Solution:** Use a backend proxy or configure CORS policy on gateway

## Security Best Practices

1. **Token Storage:**
   - Store tokens in httpOnly cookies (preferred) or secure localStorage
   - Never log full tokens (log last 4 chars only)

2. **Token Lifecycle:**
   - Implement automatic token refresh before expiry
   - Handle 401 responses with re-authentication flow

3. **PII in JWT:**
   - Avoid using email or name in `sub` claim
   - Use GUID or pairwise identifier per OIDC spec

4. **Scope Principle:**
   - Request minimum necessary scopes
   - Use role-based claims for fine-grained authorization

5. **Audit Logging:**
   - Log all authentication attempts
   - Monitor CloudTrail for gateway invocations
   - Track user actions using `sub` claim

6. **Network Security:**
   - Use HTTPS everywhere
   - Configure VPC if gateway accesses internal resources
   - Implement rate limiting and throttling

## IAM Policy for Gateway Invocation

Clients need this IAM permission to invoke the gateway:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowGatewayInvocation",
      "Effect": "Allow",
      "Action": "bedrock-agentcore:InvokeGateway",
      "Resource": "arn:aws:bedrock-agentcore:us-east-1:ACCOUNT_ID:gateway/GATEWAY_ID"
    }
  ]
}
```

**Note:** When using JWT authentication, IAM permissions are typically not required from the client side - the JWT token itself provides the authorization.

## Next Steps

1. ✅ Create Gateway with CyberArk JWT authorizer
2. ✅ Note the Gateway ID and endpoint URL
3. ✅ Implement CyberArk OAuth flow in frontend
4. ✅ Update API client to call gateway endpoint with Bearer token
5. ✅ Add OAuth callback route (`/callback`) to frontend
6. ✅ Test end-to-end authentication flow
7. ✅ Configure IAM policies and network access
8. ✅ Set up monitoring and logging
9. ✅ Deploy to production

## References

- [AgentCore Gateway Inbound Auth Documentation](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-inbound-auth.html)
- [CyberArk Identity Provider Configuration](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/identity-idp-cyberark.html)
- [CyberArk OpenID Connect Documentation](https://docs.cyberark.com/identity/latest/en/content/applications/appscustom/openidaddconfigapp.htm)
- [OAuth 2.0 PKCE (RFC 7636)](https://datatracker.ietf.org/doc/html/rfc7636)
