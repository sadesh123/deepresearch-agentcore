# Migration to Inbound Authentication

## Summary of Changes

We've migrated from **outbound OAuth authentication** (agent accessing external services) to **inbound authentication** (authenticating requests TO the agent) using CyberArk as a JWT bearer token provider.

## What Was Removed

### 1. Outbound OAuth Files Deleted
- `agents/cyberark_demo_tool.py` - Tool using `@requires_access_token` decorator
- `frontend/src/components/CyberArkConnect.jsx` - OAuth connection component
- `frontend/src/components/CyberArkConnect.css` - Component styles

### 2. Backend Changes
- Removed `/api/cyberark/connect` endpoint from `backend/main.py`
- Removed CyberArk debug logging configuration
- Reset logging levels to INFO

### 3. Frontend Changes
- Removed `CyberArkConnect` import from `frontend/src/App.jsx`
- Removed component usage from application UI

## Why the Change?

The `@requires_access_token` decorator from `bedrock_agentcore.identity.auth` is designed for:
- **CLI applications** where a single process can print an auth URL and wait for user authentication
- **Outbound authentication** where the agent needs to access external services (Google Drive, etc.)

It does NOT work for:
- **Web applications** with popup-based OAuth flows
- **Inbound authentication** where clients authenticate before calling the agent

### The Problem We Encountered
Each frontend retry created a new OAuth session with a different `request_uri`, so tokens from previous authentication attempts could never be found. The decorator's session management is incompatible with web popup flows.

## New Architecture: Inbound Authentication

Instead of the agent authenticating to external services, we now authenticate **clients calling the agent**.

### Flow Comparison

#### Old Approach (Outbound - Removed ❌)
```
User → Agent → Agent needs Google Drive → OAuth flow → Token cached → Agent accesses Google
```

#### New Approach (Inbound - Implementing ✅)
```
User → Get CyberArk Token → Call Agent with Token → AgentCore validates → Agent executes
```

### Benefits of Inbound Auth
1. **Standard OAuth Pattern:** Uses Authorization Code flow that works with web apps
2. **User Context:** Agent knows WHO is calling it (user_id, email, etc.)
3. **Token Validation:** Handled by AWS AgentCore Runtime (not agent code)
4. **Scalable:** Works for CLI, web, mobile clients
5. **Secure:** Tokens validated against CyberArk's public keys via OpenID Connect

## Implementation Steps

See `CYBERARK_INBOUND_AUTH.md` for complete guide. High-level steps:

### 1. CyberArk Configuration
- Verify OpenID Connect discovery URL: `https://abl4150.id.cyberark.cloud/.well-known/openid-configuration`
- Configure OAuth application with `openid`, `profile`, `email` scopes
- Note Client ID: `<your-client-id>` (already have this)

### 2. AWS AgentCore Configuration
```bash
aws bedrock-agentcore-control create-agent-runtime \
  --authorizer-configuration '{
    "customJWTAuthorizer": {
      "discoveryUrl": "https://abl4150.id.cyberark.cloud/.well-known/openid-configuration",
      "allowedClients": ["<your-client-id>"]
    }
  }'
```

### 3. Agent Code Updates
Add JWT claim extraction to agent entrypoint:
```python
import jwt

@app.entrypoint
def invoke(payload, context):
    auth_header = context.request_headers.get('Authorization', '')
    token = auth_header.replace('Bearer ', '')
    claims = jwt.decode(token, options={"verify_signature": False})

    user_id = claims.get('sub')
    email = claims.get('email')

    # Process request with user context
    ...
```

### 4. Client Application Updates
Implement CyberArk OAuth flow:
```javascript
// 1. Redirect to CyberArk for authentication
const authUrl = 'https://abl4150.id.cyberark.cloud/OAuth2/Authorize/...'
window.location.href = authUrl

// 2. Handle callback, exchange code for token
const token = await exchangeCodeForToken(code)

// 3. Call agent with Bearer token
const response = await fetch(agentUrl, {
  headers: {
    'Authorization': `Bearer ${token}`
  }
})
```

## File Structure After Changes

```
deepresearch-agentcore/
├── backend/
│   └── main.py                          # Cleaned up, OAuth endpoint removed
├── frontend/
│   └── src/
│       ├── App.jsx                      # CyberArkConnect component removed
│       └── components/
│           ├── ChatInterface.jsx        # Unchanged
│           ├── CouncilView.jsx          # Unchanged
│           └── DxOView.jsx              # Unchanged
├── agents/
│   ├── council_agent.py                 # Unchanged
│   └── dxo_agent.py                     # Unchanged
│
├── CYBERARK_INBOUND_AUTH.md             # NEW: Complete setup guide
├── INBOUND_AUTH_MIGRATION.md            # NEW: This file - migration summary
├── CYBERARK_OAUTH_IMPLEMENTATION.md     # OLD: Outbound auth documentation (outdated)
└── IDENTITY_IMPLEMENTATION_GUIDE.md     # OLD: Outbound auth guide (outdated)
```

## What to Do Next

### Immediate Steps
1. **Review** `CYBERARK_INBOUND_AUTH.md` to understand the new architecture
2. **Test** CyberArk OpenID Connect discovery URL
3. **Configure** AgentCore Runtime with JWT authorizer
4. **Implement** CyberArk OAuth flow in frontend (Authorization Code Grant)
5. **Update** agent code to extract JWT claims
6. **Test** end-to-end authentication flow

### Testing Checklist
- [ ] CyberArk discovery URL returns valid OpenID configuration
- [ ] AgentCore Runtime configured with CyberArk as JWT authorizer
- [ ] Client can obtain JWT token from CyberArk
- [ ] Agent invocation with Bearer token succeeds (HTTP 200)
- [ ] Agent can extract user claims from JWT
- [ ] Invalid token returns HTTP 401
- [ ] Expired token handling works correctly

## Old Documentation Files

These files are now outdated and reference the removed outbound OAuth approach:
- `CYBERARK_OAUTH_IMPLEMENTATION.md` - Documents outbound OAuth (can be removed or archived)
- `IDENTITY_IMPLEMENTATION_GUIDE.md` - Documents `@requires_access_token` decorator (can be removed or archived)

Consider renaming or removing these to avoid confusion.

## Questions or Issues?

Refer to:
1. `CYBERARK_INBOUND_AUTH.md` - Complete implementation guide
2. [AWS Bedrock AgentCore Runtime OAuth Docs](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-oauth.html)
3. [CyberArk OpenID Connect Documentation](https://docs.cyberark.com/identity/latest/en/Content/Developer/OIDC.htm)

---

**Migration Date:** 2025-12-26
**Status:** Outbound OAuth code removed, ready for inbound auth implementation
**Next Step:** Configure AgentCore Runtime with CyberArk JWT authorizer
