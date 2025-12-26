/**
 * API client for AgentCore Gateway with CyberArk authentication
 * Uses JSON-RPC 2.0 protocol via MCP
 */

import { cyberarkAuth } from './services/cyberark-auth';

// Gateway endpoint (replace with your actual gateway URL)
const GATEWAY_URL = 'https://<your-gateway-id>.gateway.bedrock-agentcore.<region>.amazonaws.com/mcp';

/**
 * Call gateway with JSON-RPC 2.0 format
 */
async function callGateway(method, params) {
  // Get access token
  let token = cyberarkAuth.getAccessToken();

  if (!token) {
    // Not authenticated, redirect to login
    cyberarkAuth.login();
    throw new Error('Authentication required');
  }

  // Prepare JSON-RPC request
  const payload = {
    jsonrpc: '2.0',
    id: `${method}-${Date.now()}`,
    method: method,
    params: params
  };

  console.log('Gateway request:', method, params);

  try {
    const response = await fetch(GATEWAY_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(payload)
    });

    // Handle 401 Unauthorized - token expired, redirect to login
    if (response.status === 401) {
      console.log('Token expired, redirecting to login...');
      cyberarkAuth.logout();
      cyberarkAuth.login();
      throw new Error('Session expired, please log in again');
    }

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Gateway error ${response.status}: ${errorText}`);
    }

    const data = await response.json();

    // Check for JSON-RPC error
    if (data.error) {
      throw new Error(`Gateway error: ${data.error.message || JSON.stringify(data.error)}`);
    }

    console.log('Gateway response:', data);

    return data;
  } catch (error) {
    console.error('Gateway call failed:', error);
    throw error;
  }
}

/**
 * List available tools
 */
export async function listTools() {
  const response = await callGateway('tools/list', {});
  return response.result;
}

/**
 * Call a specific tool
 */
export async function callTool(toolName, toolArgs) {
  const response = await callGateway('tools/call', {
    name: toolName,
    arguments: toolArgs
  });
  return response.result;
}

/**
 * Run LLM Council deliberation
 */
export async function runCouncil(question) {
  try {
    const result = await callTool('deep-research-lambda___invokeCouncil', {
      question: question
    });

    console.log('Raw gateway response:', result);

    // Parse the Lambda response
    if (result.content && result.content[0]?.text) {
      try {
        // Lambda returns JSON string in content
        const lambdaResponse = JSON.parse(result.content[0].text);
        console.log('Parsed Lambda response:', lambdaResponse);

        // Lambda might return the data nested in 'output' or directly
        if (lambdaResponse.output) {
          console.log('Returning lambdaResponse.output:', lambdaResponse.output);
          return lambdaResponse.output;
        }

        console.log('Returning lambdaResponse directly:', lambdaResponse);
        return lambdaResponse;
      } catch (e) {
        console.error('Failed to parse Lambda response:', e);
        // If not JSON, return error
        throw new Error('Invalid response format from agent');
      }
    }

    // Fallback - return result as-is
    console.warn('Unexpected response format:', result);
    return result;
  } catch (error) {
    console.error('Council error:', error);
    throw error;
  }
}

/**
 * Run DxO research workflow
 */
export async function runDxO(question) {
  try {
    const result = await callTool('deep-research-lambda___invokeDxO', {
      question: question
    });

    console.log('Raw gateway response:', result);

    // Parse the Lambda response
    if (result.content && result.content[0]?.text) {
      try {
        const lambdaResponse = JSON.parse(result.content[0].text);
        console.log('Parsed Lambda response:', lambdaResponse);

        // Lambda might return the data nested in 'output' or directly
        if (lambdaResponse.output) {
          return lambdaResponse.output;
        }

        return lambdaResponse;
      } catch (e) {
        console.error('Failed to parse Lambda response:', e);
        throw new Error('Invalid response format from agent');
      }
    }

    console.warn('Unexpected response format:', result);
    return result;
  } catch (error) {
    console.error('DxO error:', error);
    throw error;
  }
}

/**
 * Health check (via tools/list to verify gateway connectivity)
 */
export async function healthCheck() {
  try {
    const tools = await listTools();
    return {
      status: 'healthy',
      gateway: 'connected',
      tools: tools.tools?.length || 0
    };
  } catch (error) {
    return {
      status: 'error',
      error: error.message
    };
  }
}

export default {
  listTools,
  callTool,
  runCouncil,
  runDxO,
  healthCheck
};
