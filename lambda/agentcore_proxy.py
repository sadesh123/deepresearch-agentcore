"""
AWS Lambda function to proxy requests from API Gateway to AgentCore Runtime.

This function:
1. Receives HTTP requests from API Gateway
2. Invokes AgentCore Runtime using AWS SDK
3. Returns the response to the frontend
"""

import json
import boto3
import uuid
import os

# Initialize AgentCore clients
RUNTIME_ARN = os.environ['AGENTCORE_RUNTIME_ARN']

# Lambda automatically provides AWS_REGION, but boto3 can also auto-detect it
agentcore_client = boto3.client('bedrock-agentcore')


def parse_stage1_from_markdown(text):
    """Parse Stage 1 member responses from markdown text."""
    import re

    responses = []

    # Look for Stage 1 section
    stage1_match = re.search(r'## Stage 1:.*?\n(.*?)(?=## Stage 2:|$)', text, re.DOTALL | re.IGNORECASE)

    if not stage1_match:
        return []

    stage1_text = stage1_match.group(1)

    # Look for "### Member Member X" pattern
    member_pattern = r'### Member (Member \d+)\s*\n(.*?)(?=### Member|## |\Z)'
    matches = re.findall(member_pattern, stage1_text, re.DOTALL)

    for member_id, content in matches:
        responses.append({
            'member_id': member_id,
            'content': content.strip()
        })

    return responses if responses else []


def parse_stage2_from_markdown(text):
    """Parse Stage 2 rankings from markdown text."""
    import re

    rankings = []

    # This is simplified - you might need more robust parsing
    # For now, return empty array since it's complex to parse from markdown
    return rankings


def parse_stage3_from_markdown(text):
    """Parse Stage 3 chairman synthesis from markdown text."""
    import re

    # Look for "## Stage 3: Chairman Synthesis" section
    stage3_pattern = r'## Stage 3:.*?\n(.*?)$'
    match = re.search(stage3_pattern, text, re.DOTALL | re.IGNORECASE)

    if match:
        content = match.group(1).strip()
        # Remove the "Final Authoritative Council Response:" prefix if present
        content = re.sub(r'^Final Authoritative Council Response:.*?\n\n', '', content, flags=re.IGNORECASE)
        return {'content': content}

    # Fallback: return the whole text
    return {'content': text}


def parse_aggregate_rankings_from_markdown(text):
    """Parse aggregate rankings from markdown text."""
    import re

    rankings = []

    # Look for "### Aggregate Rankings" or "## Stage 2" section
    stage2_match = re.search(r'## Stage 2:.*?\n(.*?)(?=## Stage 3:|$)', text, re.DOTALL | re.IGNORECASE)

    if not stage2_match:
        return []

    stage2_text = stage2_match.group(1)

    # Look for aggregate rankings section
    agg_pattern = r'### Aggregate Rankings\s*\n(.*?)(?=\n##|\Z)'
    match = re.search(agg_pattern, stage2_text, re.DOTALL)

    if match:
        ranking_text = match.group(1)
        # Parse individual ranking lines
        # Format: - {'response_label': 'Response A', 'member_id': 'Member 1', ...}
        ranking_lines = re.findall(
            r"['\"]response_label['\"]:\s*['\"]([^'\"]+)['\"],\s*['\"]member_id['\"]:\s*['\"]([^'\"]+)['\"],\s*['\"]average_position['\"]:\s*([\d.]+),\s*['\"]vote_count['\"]:\s*(\d+)",
            ranking_text
        )

        for response_label, member_id, avg_pos, vote_count in ranking_lines:
            rankings.append({
                'response_label': response_label,
                'member_id': member_id,
                'average_position': float(avg_pos),
                'vote_count': int(vote_count)
            })

    return rankings


def lambda_handler(event, context):
    """
    Lambda handler for AgentCore proxy.

    Handles both formats:
    1. API Gateway HTTP API format (backward compatibility)
    2. AgentCore Gateway MCP format (new)
    """

    print(f"Event: {json.dumps(event)}")

    try:
        # Detect format: MCP (from Gateway) or HTTP (from API Gateway)
        if 'question' in event:
            # MCP format from AgentCore Gateway
            mode = 'council'  # Default, will be inferred from context
            question = event.get('question', '')

            # Infer mode from Lambda function name or context
            function_name = context.function_name if context else ''
            if 'Council' in function_name or 'council' in str(event):
                mode = 'council'
            elif 'DxO' in function_name or 'dxo' in str(event).lower():
                mode = 'dxo'

            print(f"MCP Format - Mode: {mode}, Question: {question[:100]}...")

        else:
            # HTTP format from API Gateway
            http_method = event.get('requestContext', {}).get('http', {}).get('method', 'POST')
            path = event.get('rawPath', '/')

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

            print(f"HTTP Format - Mode: {mode}, Question: {question[:100]}...")

        # Generate session ID (must be 33+ characters)
        session_id = str(uuid.uuid4()) + str(uuid.uuid4())

        # Prepare payload for AgentCore
        payload = json.dumps({
            "input": {
                "mode": mode,
                "prompt": question
            }
        })

        print(f"Invoking AgentCore Runtime: {RUNTIME_ARN}")

        # Invoke AgentCore Runtime
        response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=RUNTIME_ARN,
            runtimeSessionId=session_id,
            payload=payload.encode('utf-8'),
            qualifier='DEFAULT'
        )

        # Parse response
        response_body = response['response'].read()
        response_json = json.loads(response_body.decode('utf-8'))

        print(f"AgentCore response received")

        # Extract the formatted response text
        if 'output' in response_json:
            output = response_json['output']

            if 'message' in output and 'content' in output['message']:
                text_content = output['message']['content'][0].get('text', '')

                # Parse the markdown text back to structured format for frontend
                # For Council mode
                if mode == 'council':
                    # Try to extract structured data from the text content
                    # The text_content might be the synthesis markdown or structured JSON
                    try:
                        # Try parsing as JSON first (if AgentCore returns structured data)
                        parsed_data = json.loads(text_content)
                        if 'stage1' in parsed_data and 'stage2' in parsed_data and 'stage3' in parsed_data:
                            # It's already structured, just return it
                            return {
                                'statusCode': 200,
                                'headers': {
                                    'Content-Type': 'application/json',
                                    'Access-Control-Allow-Origin': '*'
                                },
                                'body': json.dumps(parsed_data)
                            }
                    except (json.JSONDecodeError, TypeError):
                        # Not JSON, it's markdown text - parse it
                        pass

                    # Parse the markdown to extract structured data
                    stage1_responses = parse_stage1_from_markdown(text_content)
                    stage2_rankings = parse_stage2_from_markdown(text_content)
                    stage3_content = parse_stage3_from_markdown(text_content)
                    aggregate_rankings = parse_aggregate_rankings_from_markdown(text_content)

                    result = {
                        'question': question,
                        'stage1': stage1_responses,
                        'stage2': stage2_rankings,
                        'stage3': stage3_content,
                        'metadata': {
                            'timestamp': output.get('timestamp', ''),
                            'aggregate_rankings': aggregate_rankings
                        }
                    }

                    # Return in appropriate format
                    if 'question' in event:  # MCP format
                        return json.dumps(result)
                    else:  # HTTP format
                        return {
                            'statusCode': 200,
                            'headers': {
                                'Content-Type': 'application/json',
                                'Access-Control-Allow-Origin': '*'
                            },
                            'body': json.dumps(result)
                        }
                # For DxO mode
                elif mode == 'dxo':
                    result = {
                        'question': question,
                        'workflow': [
                            {
                                'role': 'Complete Analysis',
                                'output': text_content
                            }
                        ],
                        'metadata': {
                            'timestamp': output.get('timestamp', '')
                        }
                    }

                    # Return in appropriate format
                    if 'question' in event:  # MCP format
                        return json.dumps(result)
                    else:  # HTTP format
                        return {
                            'statusCode': 200,
                            'headers': {
                                'Content-Type': 'application/json',
                                'Access-Control-Allow-Origin': '*'
                            },
                            'body': json.dumps(result)
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
                'error': f'AgentCore invocation failed: {str(e)}'
            })
        }
