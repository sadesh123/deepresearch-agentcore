# CyberArk Inbound Authentication Setup Guide

## Overview

This guide explains how to configure **inbound authentication** for the Deep Research Agent using CyberArk as a JWT bearer token provider. This authenticates requests TO the agent (not the agent accessing external services).

## Architecture: Inbound vs Outbound Authentication

### Inbound Authentication (What we're implementing)
- **Direction:** Client → Agent Runtime
- **Purpose:** Authenticate and authorize incoming API requests to the agent
- **Mechanism:** JWT bearer tokens validated via OpenID Connect
- **Example:** User gets CyberArk token → User calls agent with token → AgentCore validates token → Agent executes

### Outbound Authentication (What we removed)
- **Direction:** Agent → External Resources
- **Purpose:** Agent obtains OAuth tokens to access third-party services on behalf of user
- **Mechanism:** OAuth 2.0 Authorization Code Grant (3-legged OAuth)
- **Example:** Agent needs to access Google Drive → Requests OAuth token → User grants consent → Agent gets token

## Authentication Flow with CyberArk

```
┌─────────┐         ┌──────────┐        ┌────────────────┐        ┌───────────┐
│ Client  │         │ CyberArk │        │  AgentCore     │        │  Agent    │
│  App    │         │ Identity │        │  Runtime       │        │  Runtime  │
└────┬────┘         └────┬─────┘        └───────┬────────┘        └─────┬─────┘
     │                   │                      │                       │
     │ 1. Login to       │                      │                       │
     │ CyberArk          │                      │                       │
     ├──────────────────>│                      │                       │
     │                   │                      │                       │
     │ 2. JWT Token      │                      │                       │
     │<──────────────────┤                      │                       │
     │                   │                      │                       │
     │ 3. POST /runtimes/{arn}/invocations     │                       │
     │    Authorization: Bearer {token}         │                       │
     ├─────────────────────────────────────────>│                       │
     │                   │                      │                       │
     │                   │ 4. Validate JWT      │                       │
     │                   │    - Fetch OpenID    │                       │
     │                   │      config          │                       │
     │                   │<─────────────────────┤                       │
     │                   │    - Verify issuer   │                       │
     │                   │    - Verify client_id│                       │
     │                   │    - Verify signature│                       │
     │                   │                      │                       │
     │                   │                      │ 5. Exchange JWT for   │
     │                   │                      │    Workload Token     │
     │                   │                      ├──────────────────────>│
     │                   │                      │                       │
     │                   │                      │ 6. Execute with       │
     │                   │                      │    user context       │
     │                   │                      │<──────────────────────┤
     │                   │                      │                       │
     │ 7. Agent Response │                      │                       │
     │<─────────────────────────────────────────┤                       │
     │                   │                      │                       │
```

## Setup Steps

### Step 1: Get CyberArk OpenID Configuration

1. Determine your CyberArk discovery URL format:
   ```
   https://{tenant}.id.cyberark.cloud/.well-known/openid-configuration
   ```

2. For your tenant `<your-cyberark-tenant>`, the discovery URL should be:
   ```
   https://<your-cyberark-tenant>.id.cyberark.cloud/.well-known/openid-configuration
   ```

3. Verify the discovery URL returns valid OpenID configuration:
   ```bash
   curl https://<your-cyberark-tenant>.id.cyberark.cloud/.well-known/openid-configuration | jq
   ```

4. Note the following from the response:
   - `issuer` - Issuer identifier (e.g., `https://<your-cyberark-tenant>.id.cyberark.cloud`)
   - `authorization_endpoint` - OAuth authorization endpoint
   - `token_endpoint` - Token endpoint for exchanging codes
   - `jwks_uri` - JSON Web Key Set for signature verification

### Step 2: Register Application in CyberArk

1. Log into CyberArk Identity Admin Portal
2. Create an OAuth2 Web Application:
   - **Application Name:** `deep-research-agent`
   - **Application Type:** Web Application
   - **Redirect URIs:** (Not needed for Bearer token auth, but may be required)
3. Configure OAuth Settings:
   - **Grant Types:** `authorization_code`, `refresh_token`
   - **Scopes:** `openid`, `profile`, `email`
   - **Token Format:** JWT
4. Note the **Client ID** generated by CyberArk
5. Optionally configure **Audience** claim (usually your application URL)

### Step 3: Configure AgentCore Runtime with JWT Authorizer

#### Using AWS CLI

```bash
aws bedrock-agentcore-control create-agent-runtime \
  --agent-runtime-name deep-research-agent \
  --agent-runtime-artifact '{
    "containerConfiguration": {
      "containerUri": "YOUR_ECR_URI"
    }
  }' \
  --authorizer-configuration '{
    "customJWTAuthorizer": {
      "discoveryUrl": "https://<your-cyberark-tenant>.id.cyberark.cloud/.well-known/openid-configuration",
      "allowedClients": ["<your-client-id>"],
      "allowedAudience": ["YOUR_AUDIENCE_IF_CONFIGURED"],
      "allowedScopes": ["openid", "profile", "email"]
    }
  }' \
  --network-configuration '{"networkMode":"PUBLIC"}' \
  --role-arn "arn:aws:iam::ACCOUNT_ID:role/AgentRuntimeRole" \
  --region us-east-1
```

#### Configuration Parameters Explained

| Parameter | JWT Claim | Purpose |
|-----------|-----------|---------|
| `discoveryUrl` | `iss` (issuer) | OpenID Connect discovery URL for fetching public keys and metadata |
| `allowedClients` | `client_id` | List of permitted OAuth client IDs |
| `allowedAudience` | `aud` | List of permitted token audiences |
| `allowedScopes` | `scope` | Required scopes in the token |
| `requiredCustomClaims` | Custom claims | Additional claim validation (format: `"claim_name:claim_value"`) |

### Step 4: Update Agent Code to Read JWT Claims

Modify your agent's `main.py` or entry point to extract user context from the JWT:

```python
import jwt
import json
import logging

logger = logging.getLogger(__name__)

@app.entrypoint
def invoke(payload, context):
    """
    Agent entrypoint that receives authenticated requests.

    The JWT token is already validated by AgentCore Runtime,
    so we just need to decode it (without signature verification).
    """

    # Extract Authorization header
    auth_header = context.request_headers.get('Authorization', '')

    if not auth_header:
        logger.warning("No Authorization header found")
        return {
            "error": "Authentication required",
            "message": "No bearer token provided"
        }

    # Remove "Bearer " prefix
    token = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else auth_header

    try:
        # Decode JWT without signature verification (AgentCore already validated it)
        claims = jwt.decode(token, options={"verify_signature": False})

        logger.info(f"Authenticated request from user: {claims.get('sub')}")
        logger.debug(f"Full claims: {json.dumps(claims, indent=2)}")

        # Extract user context
        user_context = {
            'user_id': claims.get('sub'),
            'email': claims.get('email'),
            'name': claims.get('name'),
            'client_id': claims.get('client_id'),
            'scopes': claims.get('scope', '').split(),
            'expires_at': claims.get('exp')
        }

        # Process request with user context
        prompt = payload.get('prompt', '')
        mode = payload.get('mode', 'council')

        # Your agent logic here...
        # You now have authenticated user context available

        return {
            "status": "success",
            "user": user_context,
            "response": "Agent response here..."
        }

    except jwt.InvalidTokenError as e:
        logger.error(f"Invalid JWT token: {str(e)}")
        return {
            "error": "Invalid token",
            "message": str(e)
        }
```

### Step 5: Test Authentication Flow

1. **Verify Response:**
   - Successful authentication: Agent processes request and returns response
   - Failed authentication: HTTP 401 with `WWW-Authenticate` header

## Troubleshooting

### 401 Unauthorized Error

**Error Response:**
```
HTTP/1.1 401 Unauthorized
WWW-Authenticate: Bearer resource_metadata="https://bedrock-agentcore.us-east-1.amazonaws.com/..."
```

**Possible Causes:**
1. **Invalid Token:** Token is malformed or expired
   - Solution: Obtain a fresh token from CyberArk

2. **Issuer Mismatch:** Token's `iss` claim doesn't match discovery URL
   - Solution: Verify CyberArk issuer matches discovery URL base

3. **Client ID Not Allowed:** Token's `client_id` not in `allowedClients`
   - Solution: Add client ID to authorizer configuration

4. **Audience Mismatch:** Token's `aud` claim not in `allowedAudience`
   - Solution: Configure correct audience in both CyberArk and AgentCore

5. **Scope Missing:** Token doesn't contain required scopes
   - Solution: Request required scopes during CyberArk OAuth flow

### Signature Verification Failure

**Cause:** AgentCore cannot fetch or verify JWT signature against CyberArk's public keys

## References

- [AWS Bedrock AgentCore Runtime OAuth Documentation](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-oauth.html)
- [CyberArk OpenID Connect Documentation](https://docs.cyberark.com/identity/latest/en/Content/Developer/OIDC.htm)
- [OAuth 2.0 RFC 6749](https://datatracker.ietf.org/doc/html/rfc6749)
- [JWT RFC 7519](https://datatracker.ietf.org/doc/html/rfc7519)
- [OpenID Connect Core Specification](https://openid.net/specs/openid-connect-core-1_0.html)
