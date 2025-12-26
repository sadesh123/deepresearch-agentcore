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


## References

- [AgentCore Gateway Outbound Auth](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-outbound-auth.html)
- [CyberArk as IdP for AgentCore](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/identity-idp-cyberark.html)
- [CyberArk OAuth App Setup](https://docs.cyberark.com/identity/latest/en/content/applications/appscustom/openidaddconfigapp.htm)
- [AgentCore Identity Authentication](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/identity-authentication.html)

---

**Document Status**: Ready for implementation
**Last Updated**: 2025-12-25
