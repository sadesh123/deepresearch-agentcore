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

### Step 4: Note Gateway Endpoint

After creation, note the gateway endpoint:
```
https://bedrock-agentcore.us-east-1.amazonaws.com/gateway/{GATEWAY_ID}/invocations
```

This is the URL your frontend will call (instead of the agent runtime URL).


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

## References

- [AgentCore Gateway Inbound Auth Documentation](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-inbound-auth.html)
- [CyberArk Identity Provider Configuration](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/identity-idp-cyberark.html)
- [CyberArk OpenID Connect Documentation](https://docs.cyberark.com/identity/latest/en/content/applications/appscustom/openidaddconfigapp.htm)
- [OAuth 2.0 PKCE (RFC 7636)](https://datatracker.ietf.org/doc/html/rfc7636)
