# Inbound Authentication Implementation Guide
## Adding User Authentication to Deep Research Agent

---

## Overview

This guide walks through implementing **inbound authentication** for the Deep Research Agent using AWS Bedrock AgentCore Identity with Amazon Cognito.

### What You'll Build

```
User logs in with Cognito → Gets JWT token → Calls agent with token
    ↓
AgentCore validates token → Allows access → User-specific session
    ↓
Research history + preferences tied to authenticated user
```

---

## Current vs. Target Architecture

### Current (No Authentication)
```
Browser → API Gateway → Lambda → AgentCore Runtime
  ↓
Anonymous, no user context, no personalization
```

### Target (With Inbound Auth)
```
Browser → Login (Cognito) → Get JWT Token
  ↓
Browser → API Gateway → Lambda (validates token) → AgentCore Runtime
  ↓
AgentCore knows user_id → Personalized research + history
```

---

## Implementation Plan

### Phase 1: Cognito Setup (Infrastructure)
### Phase 2: AgentCore Runtime Configuration
### Phase 3: Lambda Proxy Updates
### Phase 4: Frontend Authentication
### Phase 5: User-Specific Features

---

## Phase 1: Cognito Setup

### Step 1.1: Create Cognito User Pool

Create `setup_cognito.sh`:

```bash
#!/bin/bash
set -e

REGION="us-east-1"
POOL_NAME="DeepResearchAgentUsers"

echo "Creating Cognito User Pool..."

# Create user pool with password policy
POOL_RESPONSE=$(aws cognito-idp create-user-pool \
  --pool-name "$POOL_NAME" \
  --policies '{
    "PasswordPolicy": {
      "MinimumLength": 8,
      "RequireUppercase": true,
      "RequireLowercase": true,
      "RequireNumbers": true,
      "RequireSymbols": false
    }
  }' \
  --auto-verified-attributes email \
  --username-attributes email \
  --mfa-configuration OPTIONAL \
  --region $REGION \
  --output json)

USER_POOL_ID=$(echo $POOL_RESPONSE | jq -r '.UserPool.Id')

echo "✓ User Pool Created: $USER_POOL_ID"

# Create user pool domain for hosted UI
DOMAIN_PREFIX="deep-research-$(date +%s)"
aws cognito-idp create-user-pool-domain \
  --domain "$DOMAIN_PREFIX" \
  --user-pool-id $USER_POOL_ID \
  --region $REGION

echo "✓ User Pool Domain: $DOMAIN_PREFIX"

# Create app client (for web application)
CLIENT_RESPONSE=$(aws cognito-idp create-user-pool-client \
  --user-pool-id $USER_POOL_ID \
  --client-name "DeepResearchWebApp" \
  --no-generate-secret \
  --explicit-auth-flows \
    "ALLOW_USER_PASSWORD_AUTH" \
    "ALLOW_USER_SRP_AUTH" \
    "ALLOW_REFRESH_TOKEN_AUTH" \
  --supported-identity-providers "COGNITO" \
  --allowed-o-auth-flows "code" "implicit" \
  --allowed-o-auth-scopes "openid" "profile" "email" \
  --allowed-o-auth-flows-user-pool-client \
  --callback-urls "http://localhost:5173" "https://yourdomain.com" \
  --logout-urls "http://localhost:5173" "https://yourdomain.com" \
  --region $REGION \
  --output json)

CLIENT_ID=$(echo $CLIENT_RESPONSE | jq -r '.UserPoolClient.ClientId')

echo "✓ App Client Created: $CLIENT_ID"

# Construct URLs
DISCOVERY_URL="https://cognito-idp.$REGION.amazonaws.com/$USER_POOL_ID/.well-known/openid-configuration"
HOSTED_UI_URL="https://$DOMAIN_PREFIX.auth.$REGION.amazoncognito.com"

# Create test user
TEST_USER_EMAIL="testuser@example.com"
TEST_USER_PASSWORD="TestPass123"

aws cognito-idp admin-create-user \
  --user-pool-id $USER_POOL_ID \
  --username "$TEST_USER_EMAIL" \
  --user-attributes Name=email,Value="$TEST_USER_EMAIL" Name=email_verified,Value=true \
  --temporary-password "$TEST_USER_PASSWORD" \
  --message-action SUPPRESS \
  --region $REGION

# Set permanent password
aws cognito-idp admin-set-user-password \
  --user-pool-id $USER_POOL_ID \
  --username "$TEST_USER_EMAIL" \
  --password "$TEST_USER_PASSWORD" \
  --permanent \
  --region $REGION

echo "✓ Test User Created: $TEST_USER_EMAIL / $TEST_USER_PASSWORD"

# Output configuration
echo ""
echo "========================================="
echo "Cognito Configuration Complete"
echo "========================================="
echo ""
echo "User Pool ID: $USER_POOL_ID"
echo "Client ID: $CLIENT_ID"
echo "Discovery URL: $DISCOVERY_URL"
echo "Hosted UI URL: $HOSTED_UI_URL"
echo "Test User: $TEST_USER_EMAIL"
echo "Test Password: $TEST_USER_PASSWORD"
echo ""
echo "# Environment variables (add to .env):"
echo "COGNITO_USER_POOL_ID='$USER_POOL_ID'"
echo "COGNITO_CLIENT_ID='$CLIENT_ID'"
echo "COGNITO_REGION='$REGION'"
echo "COGNITO_DISCOVERY_URL='$DISCOVERY_URL'"
echo ""
echo "========================================="

# Save to config file
cat > cognito_config.json <<EOF
{
  "userPoolId": "$USER_POOL_ID",
  "clientId": "$CLIENT_ID",
  "region": "$REGION",
  "discoveryUrl": "$DISCOVERY_URL",
  "hostedUiUrl": "$HOSTED_UI_URL",
  "testUser": {
    "email": "$TEST_USER_EMAIL",
    "password": "$TEST_USER_PASSWORD"
  }
}
EOF

echo "Configuration saved to cognito_config.json"
```

Run the script:
```bash
chmod +x setup_cognito.sh
./setup_cognito.sh
```

---

## Phase 2: Configure AgentCore Runtime

### Step 2.1: Update AgentCore Runtime with JWT Authorization

```bash
#!/bin/bash

# Load Cognito config
USER_POOL_ID=$(jq -r '.userPoolId' cognito_config.json)
CLIENT_ID=$(jq -r '.clientId' cognito_config.json)
REGION=$(jq -r '.region' cognito_config.json)
DISCOVERY_URL=$(jq -r '.discoveryUrl' cognito_config.json)

# Get your AgentCore Runtime ARN
RUNTIME_ARN="arn:aws:bedrock-agentcore:$REGION:ACCOUNT_ID:agent-runtime/YOUR_RUNTIME_NAME"

echo "Updating AgentCore Runtime with JWT authorization..."

aws bedrock-agentcore-control update-agent-runtime \
  --agent-runtime-arn "$RUNTIME_ARN" \
  --authorizer-configuration '{
    "customJWTAuthorizer": {
      "discoveryUrl": "'$DISCOVERY_URL'",
      "allowedClients": ["'$CLIENT_ID'"]
    }
  }' \
  --region $REGION

echo "✓ AgentCore Runtime updated with Cognito authorization"
```

### Step 2.2: Verify Configuration

```bash
aws bedrock-agentcore-control get-agent-runtime \
  --agent-runtime-arn "$RUNTIME_ARN" \
  --region $REGION
```

---

## Phase 3: Update Lambda Proxy

### Step 3.1: Add JWT Validation to Lambda

Update `/mnt/c/Users/Admin/Desktop/deepresearch-agentcore/lambda/agentcore_proxy.py`:

```python
"""
AWS Lambda function to proxy requests from API Gateway to AgentCore Runtime.
Now with JWT token validation and user context.
"""

import json
import boto3
import uuid
import os
import jwt
from jwt import PyJWKClient
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize clients
RUNTIME_ARN = os.environ['AGENTCORE_RUNTIME_ARN']
COGNITO_USER_POOL_ID = os.environ['COGNITO_USER_POOL_ID']
COGNITO_CLIENT_ID = os.environ['COGNITO_CLIENT_ID']
COGNITO_REGION = os.environ['COGNITO_REGION']

agentcore_client = boto3.client('bedrock-agentcore')

# Construct JWKs URL for token validation
JWKS_URL = f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}/.well-known/jwks.json"
jwks_client = PyJWKClient(JWKS_URL)


def validate_jwt_token(token):
    """
    Validate JWT token from Cognito

    Returns:
        dict: Decoded token claims including user_id (sub)
    """
    try:
        # Remove 'Bearer ' prefix if present
        if token.startswith('Bearer '):
            token = token[7:]

        # Get signing key from JWKS
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        # Decode and validate token
        decoded_token = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=COGNITO_CLIENT_ID,
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_aud": True
            }
        )

        logger.info(f"Token validated for user: {decoded_token.get('sub')}")
        return decoded_token

    except jwt.ExpiredSignatureError:
        logger.error("Token has expired")
        raise Exception("Token expired")
    except jwt.InvalidAudienceError:
        logger.error("Invalid token audience")
        raise Exception("Invalid token audience")
    except jwt.InvalidTokenError as e:
        logger.error(f"Invalid token: {str(e)}")
        raise Exception(f"Invalid token: {str(e)}")
    except Exception as e:
        logger.error(f"Token validation error: {str(e)}")
        raise Exception(f"Token validation failed: {str(e)}")


def lambda_handler(event, context):
    """
    Lambda handler for AgentCore proxy with authentication.
    """

    print(f"Event: {json.dumps(event)}")

    try:
        # Parse request
        http_method = event.get('requestContext', {}).get('http', {}).get('method', 'POST')
        path = event.get('rawPath', '/')

        # Extract and validate JWT token
        headers = event.get('headers', {})
        auth_header = headers.get('authorization') or headers.get('Authorization')

        if not auth_header:
            return {
                'statusCode': 401,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'Missing authorization token'})
            }

        # Validate token and extract user info
        try:
            token_claims = validate_jwt_token(auth_header)
            user_id = token_claims.get('sub')  # Cognito user ID
            user_email = token_claims.get('email', '')
            username = token_claims.get('cognito:username', user_email)

            logger.info(f"Authenticated user: {username} ({user_id})")

        except Exception as e:
            return {
                'statusCode': 401,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': f'Authentication failed: {str(e)}'})
            }

        # Parse body
        body = event.get('body', '{}')
        if isinstance(body, str):
            body = json.loads(body)

        # Determine mode from path
        if '/council' in path:
            mode = 'council'
        elif '/dxo' in path:
            mode = 'dxo'
        else:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'Invalid path. Use /council or /dxo'})
            }

        # Get question from request
        question = body.get('question', '')
        if not question:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'Missing question in request body'})
            }

        print(f"Mode: {mode}, Question: {question[:100]}..., User: {username}")

        # Generate user-specific session ID
        session_id = f"{user_id}_{str(uuid.uuid4())}"

        # Prepare payload for AgentCore with user context
        payload = json.dumps({
            "input": {
                "mode": mode,
                "prompt": question,
                "user_context": {
                    "user_id": user_id,
                    "username": username,
                    "email": user_email
                }
            }
        })

        print(f"Invoking AgentCore Runtime with user context: {session_id}")

        # Invoke AgentCore Runtime with bearer token
        response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=RUNTIME_ARN,
            runtimeSessionId=session_id,
            payload=payload.encode('utf-8'),
            qualifier='DEFAULT',
            # Pass the bearer token to AgentCore
            authenticationToken=auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else auth_header
        )

        # Parse response
        response_body = response['response'].read()
        response_json = json.loads(response_body.decode('utf-8'))

        print(f"AgentCore response received for user: {username}")

        # Extract and parse the response
        if 'output' in response_json:
            output = response_json['output']

            if 'message' in output and 'content' in output['message']:
                text_content = output['message']['content'][0].get('text', '')

                if mode == 'council':
                    # Parse markdown to structured format
                    stage1_responses = parse_stage1_from_markdown(text_content)
                    stage2_rankings = parse_stage2_from_markdown(text_content)
                    stage3_content = parse_stage3_from_markdown(text_content)
                    aggregate_rankings = parse_aggregate_rankings_from_markdown(text_content)

                    return {
                        'statusCode': 200,
                        'headers': {
                            'Content-Type': 'application/json',
                            'Access-Control-Allow-Origin': '*'
                        },
                        'body': json.dumps({
                            'question': question,
                            'stage1': stage1_responses,
                            'stage2': stage2_rankings,
                            'stage3': stage3_content,
                            'metadata': {
                                'timestamp': output.get('timestamp', ''),
                                'aggregate_rankings': aggregate_rankings,
                                'user': {
                                    'user_id': user_id,
                                    'username': username
                                }
                            }
                        })
                    }

                elif mode == 'dxo':
                    return {
                        'statusCode': 200,
                        'headers': {
                            'Content-Type': 'application/json',
                            'Access-Control-Allow-Origin': '*'
                        },
                        'body': json.dumps({
                            'question': question,
                            'workflow': [
                                {
                                    'role': 'Complete Analysis',
                                    'output': text_content
                                }
                            ],
                            'metadata': {
                                'timestamp': output.get('timestamp', ''),
                                'user': {
                                    'user_id': user_id,
                                    'username': username
                                }
                            }
                        })
                    }

        # Fallback response
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(response_json)
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()

        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': f'Request failed: {str(e)}'
            })
        }


# Keep existing parsing functions...
def parse_stage1_from_markdown(text):
    # ... existing implementation ...
    pass

def parse_stage2_from_markdown(text):
    # ... existing implementation ...
    pass

def parse_stage3_from_markdown(text):
    # ... existing implementation ...
    pass

def parse_aggregate_rankings_from_markdown(text):
    # ... existing implementation ...
    pass
```

### Step 3.2: Update Lambda Requirements

Create/update `lambda/requirements.txt`:

```txt
boto3
PyJWT[crypto]
```

### Step 3.3: Update Lambda Environment Variables

```bash
aws lambda update-function-configuration \
  --function-name DeepResearchAgentProxy \
  --environment "Variables={
    AGENTCORE_RUNTIME_ARN=$RUNTIME_ARN,
    COGNITO_USER_POOL_ID=$USER_POOL_ID,
    COGNITO_CLIENT_ID=$CLIENT_ID,
    COGNITO_REGION=$REGION
  }"
```

### Step 3.4: Deploy Updated Lambda

```bash
cd lambda
zip -r function.zip agentcore_proxy.py
aws lambda update-function-code \
  --function-name DeepResearchAgentProxy \
  --zip-file fileb://function.zip
```

---

## Phase 4: Frontend Authentication

### Step 4.1: Install AWS Amplify

```bash
cd frontend
npm install aws-amplify @aws-amplify/ui-react
```

### Step 4.2: Configure Amplify

Create `frontend/src/aws-config.js`:

```javascript
const awsConfig = {
  Auth: {
    Cognito: {
      userPoolId: import.meta.env.VITE_COGNITO_USER_POOL_ID,
      userPoolClientId: import.meta.env.VITE_COGNITO_CLIENT_ID,
      region: import.meta.env.VITE_COGNITO_REGION || 'us-east-1',
      loginWith: {
        email: true,
        oauth: {
          domain: import.meta.env.VITE_COGNITO_DOMAIN,
          scopes: ['openid', 'email', 'profile'],
          redirectSignIn: [window.location.origin],
          redirectSignOut: [window.location.origin],
          responseType: 'code'
        }
      }
    }
  }
};

export default awsConfig;
```

### Step 4.3: Update Frontend Environment

Create `frontend/.env`:

```bash
VITE_API_BASE_URL=https://your-api-gateway-url.amazonaws.com
VITE_COGNITO_USER_POOL_ID=us-east-1_xxxxx
VITE_COGNITO_CLIENT_ID=xxxxxxxxxxxxxxxxxx
VITE_COGNITO_REGION=us-east-1
VITE_COGNITO_DOMAIN=deep-research-xxxxx.auth.us-east-1.amazoncognito.com
```

### Step 4.4: Add Authentication to App

Update `frontend/src/main.jsx`:

```javascript
import React from 'react'
import ReactDOM from 'react-dom/client'
import { Amplify } from 'aws-amplify'
import { Authenticator } from '@aws-amplify/ui-react'
import '@aws-amplify/ui-react/styles.css'
import App from './App'
import './index.css'
import awsConfig from './aws-config'

// Configure Amplify
Amplify.configure(awsConfig)

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <Authenticator>
      {({ signOut, user }) => (
        <App user={user} signOut={signOut} />
      )}
    </Authenticator>
  </React.StrictMode>,
)
```

### Step 4.5: Update API Client with Token

Update `frontend/src/api.js`:

```javascript
import axios from 'axios';
import { fetchAuthSession } from 'aws-amplify/auth';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add token to all requests
api.interceptors.request.use(async (config) => {
  try {
    const session = await fetchAuthSession();
    const token = session.tokens?.idToken?.toString();

    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  } catch (error) {
    console.error('Error getting auth token:', error);
  }

  return config;
});

// Existing API functions...
export const healthCheck = async () => {
  const response = await api.get('/health');
  return response.data;
};

export const runCouncil = async (question) => {
  const response = await api.post('/council', {
    question,
    mode: 'council'
  });
  return response.data;
};

export const runDxO = async (question) => {
  const response = await api.post('/dxo', {
    question,
    mode: 'dxo'
  });
  return response.data;
};

export default api;
```

### Step 4.6: Update App Component

Update `frontend/src/App.jsx`:

```javascript
import { useState } from 'react'
import './App.css'
import ChatInterface from './components/ChatInterface'
import CouncilView from './components/CouncilView'
import DxOView from './components/DxOView'
import { runCouncil, runDxO } from './api'

function App({ user, signOut }) {
  const [mode, setMode] = useState('council')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)

  const handleSubmit = async (question) => {
    setLoading(true)
    setError(null)
    setResult(null)

    try {
      let data
      if (mode === 'council') {
        data = await runCouncil(question)
      } else {
        data = await runDxO(question)
      }
      setResult(data)
    } catch (err) {
      console.error('Error:', err)
      if (err.response?.status === 401) {
        setError('Authentication failed. Please sign out and sign in again.')
      } else {
        setError(err.response?.data?.detail || err.message || 'An error occurred')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>Deep Research Agent</h1>
        <p className="subtitle">AI-Powered Research with LLM Council & DxO Framework</p>
        <div className="user-info">
          <span>Welcome, {user.signInDetails?.loginId || 'User'}!</span>
          <button onClick={signOut} className="signout-button">Sign Out</button>
        </div>
      </header>

      <div className="container">
        <div className="mode-selector card">
          <h3>Select Research Mode</h3>
          <div className="mode-buttons">
            <button
              className={`mode-button ${mode === 'council' ? 'active' : ''}`}
              onClick={() => setMode('council')}
              disabled={loading}
            >
              <div className="mode-icon">⚖️</div>
              <div className="mode-title">LLM Council</div>
              <div className="mode-desc">3-stage democratic deliberation</div>
            </button>
            <button
              className={`mode-button ${mode === 'dxo' ? 'active' : ''}`}
              onClick={() => setMode('dxo')}
              disabled={loading}
            >
              <div className="mode-icon">🔬</div>
              <div className="mode-title">DxO Research</div>
              <div className="mode-desc">Sequential expert workflow</div>
            </button>
          </div>
        </div>

        <ChatInterface
          onSubmit={handleSubmit}
          loading={loading}
          mode={mode}
        />

        {error && (
          <div className="error card">
            <strong>Error:</strong> {error}
          </div>
        )}

        {loading && (
          <div className="loading card">
            <div className="spinner"></div>
            <p>
              {mode === 'council'
                ? 'Council members are deliberating...'
                : 'Research team is working...'}
            </p>
          </div>
        )}

        {result && !loading && (
          <div className="results">
            {mode === 'council' ? (
              <CouncilView result={result} />
            ) : (
              <DxOView result={result} />
            )}
          </div>
        )}
      </div>

      <footer className="app-footer">
        <p>Powered by AWS Bedrock AgentCore | Built for IHL Demo</p>
      </footer>
    </div>
  )
}

export default App
```

### Step 4.7: Add User Info Styles

Update `frontend/src/App.css`:

```css
/* Add to existing styles */

.app-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 2rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  position: relative;
}

.user-info {
  position: absolute;
  top: 1rem;
  right: 2rem;
  display: flex;
  align-items: center;
  gap: 1rem;
}

.user-info span {
  font-size: 0.9rem;
  opacity: 0.9;
}

.signout-button {
  padding: 0.5rem 1rem;
  background: rgba(255, 255, 255, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: white;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: all 0.3s ease;
}

.signout-button:hover {
  background: rgba(255, 255, 255, 0.3);
  border-color: rgba(255, 255, 255, 0.5);
}
```

---

## Phase 5: Testing

### Step 5.1: Test Authentication Flow

1. **Start Frontend**:
```bash
cd frontend
npm run dev
```

2. **Open Browser**: Navigate to `http://localhost:5173`

3. **Login Flow**:
   - You'll see Amplify's Authenticator UI
   - Sign in with test credentials:
     - Email: `testuser@example.com`
     - Password: `TestPass123`

4. **Test Research**:
   - Select "LLM Council" mode
   - Enter: "What are the latest advances in quantum computing?"
   - Verify research completes with your username displayed

### Step 5.2: Verify Token in Network Tab

1. Open browser DevTools → Network tab
2. Submit a research question
3. Find the `/council` or `/dxo` request
4. Check Headers → Authorization: `Bearer eyJraWQ...`
5. Verify request succeeds with 200 OK

### Step 5.3: Test Token Expiration

1. Wait 60 minutes (default Cognito token TTL)
2. Try to submit research
3. Should get 401 Unauthorized
4. Sign out and sign in again
5. Research should work again

---

## Troubleshooting

### Issue: "Token validation failed"

**Check:**
```bash
# Verify Cognito configuration
aws cognito-idp describe-user-pool --user-pool-id $USER_POOL_ID

# Verify AgentCore authorizer configuration
aws bedrock-agentcore-control get-agent-runtime --agent-runtime-arn $RUNTIME_ARN
```

**Common causes:**
- Client ID mismatch between Cognito and AgentCore
- Discovery URL incorrect
- Token expired (> 60 minutes old)

### Issue: "CORS error in browser"

**Fix API Gateway CORS:**
```bash
aws apigatewayv2 update-api \
  --api-id YOUR_API_ID \
  --cors-configuration '{
    "AllowOrigins": ["http://localhost:5173", "https://yourdomain.com"],
    "AllowMethods": ["GET", "POST", "OPTIONS"],
    "AllowHeaders": ["Content-Type", "Authorization"],
    "MaxAge": 300
  }'
```

### Issue: "Missing authorization token"

**Check frontend:**
```javascript
// In browser console
import { fetchAuthSession } from 'aws-amplify/auth';
const session = await fetchAuthSession();
console.log(session.tokens?.idToken?.toString());
```

If undefined, user is not signed in or session expired.

---

## Next Steps

Once inbound authentication is working:

### 1. **Add AgentCore Memory**
Store user research history:
```python
# In agent code
await agentcore_memory.store(
    user_id=user_context["user_id"],
    memory_type="research_session",
    content={
        "question": question,
        "result": result,
        "timestamp": datetime.now()
    }
)
```

### 2. **Add User Preferences**
Let users customize their experience:
```python
user_prefs = await agentcore_memory.retrieve(
    user_id=user_id,
    memory_type="preferences"
)
```

### 3. **Add Usage Quotas**
Implement AgentCore Policy:
```cedar
permit(
    principal has role::"free_tier",
    action == Action::"research",
    resource == Service::"deep-research-agent"
)
when {
    context.daily_query_count < 10
};
```

---

## Security Best Practices

✅ **Never expose Cognito Client Secret** in frontend code
✅ **Always validate tokens in Lambda** before invoking AgentCore
✅ **Use HTTPS** for all API calls in production
✅ **Rotate Cognito Client Secret** regularly
✅ **Monitor failed authentication attempts** in CloudWatch
✅ **Set appropriate token TTL** (default 60 min is reasonable)
✅ **Implement token refresh** in frontend for long sessions

---

## Cost Estimate

| Service | Usage | Cost |
|---------|-------|------|
| **Cognito** | 10K MAU | Free tier |
| **Lambda** | +1ms per request (JWT validation) | +$0.0000002 |
| **AgentCore** | No additional cost | Included |
| **CloudWatch Logs** | JWT validation logs | ~$0.50/month |

**Total Additional Cost**: ~$0.50/month for authentication

---

## Sources

- [AgentCore Runtime OAuth Authentication](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-oauth.html)
- [Building Authenticated Agents with Cognito](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/identity-getting-started-cognito.html)
- [Amazon Cognito as Identity Provider](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/identity-idp-cognito.html)
- [AgentCore Identity Blog Post](https://aws.amazon.com/blogs/machine-learning/introducing-amazon-bedrock-agentcore-identity-securing-agentic-ai-at-scale/)

---

**Document Version**: 1.0
**Last Updated**: December 2025
**Status**: Ready for Implementation
