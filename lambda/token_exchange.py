"""
Lambda function to securely exchange OAuth authorization code for tokens
Handles CORS and keeps client secret secure
Uses AWS Secrets Manager for secure credential storage
"""
import json
import urllib.request
import urllib.parse
import urllib.error
import os
import boto3
from botocore.exceptions import ClientError

# Secrets Manager configuration
SECRET_NAME = "<your-secret-name>"  # e.g., "test/agentcoredemo/tokenexchange"
REGION_NAME = "<your-aws-region>"  # e.g., "us-east-1"

# CyberArk OAuth configuration
TOKEN_ENDPOINT = "https://<your-cyberark-tenant>.id.cyberark.cloud/OAuth2/Token/<your-app-id>"

# Cache for secrets (Lambda container reuse)
_cached_secrets = None

def get_secrets():
    """
    Retrieve CLIENT_ID and CLIENT_SECRET from AWS Secrets Manager
    Uses Lambda container caching to minimize API calls
    """
    global _cached_secrets

    # Return cached secrets if available
    if _cached_secrets:
        return _cached_secrets

    print(f"Retrieving secrets from Secrets Manager: {SECRET_NAME}")

    # Create Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=REGION_NAME
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=SECRET_NAME
        )
    except ClientError as e:
        print(f"Error retrieving secret: {e}")
        raise e

    # Parse secret string (JSON key-value pairs)
    secret_string = get_secret_value_response['SecretString']
    secrets = json.loads(secret_string)

    # Cache for subsequent invocations in same container
    _cached_secrets = {
        'CLIENT_ID': secrets['CLIENT_ID'],
        'CLIENT_SECRET': secrets['CLIENT_SECRET']
    }

    print("✓ Secrets retrieved successfully")
    return _cached_secrets

def lambda_handler(event, context):
    """
    Exchange OAuth authorization code for access token

    Expects POST with JSON body:
    {
        "code": "authorization_code",
        "redirect_uri": "callback_url"
    }
    """

    # Handle CORS preflight
    if event.get('requestContext', {}).get('http', {}).get('method') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'POST,OPTIONS'
            },
            'body': ''
        }

    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        code = body.get('code')
        redirect_uri = body.get('redirect_uri')

        if not code:
            return error_response(400, 'Missing authorization code')

        if not redirect_uri:
            return error_response(400, 'Missing redirect_uri')

        print(f"Exchanging code for token (redirect_uri: {redirect_uri})")

        # Get credentials from Secrets Manager
        secrets = get_secrets()

        # Exchange code for token
        token_data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': redirect_uri,
            'client_id': secrets['CLIENT_ID'],
            'client_secret': secrets['CLIENT_SECRET']
        }

        # Make request to CyberArk
        data = urllib.parse.urlencode(token_data).encode('utf-8')
        req = urllib.request.Request(
            TOKEN_ENDPOINT,
            data=data,
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )

        try:
            with urllib.request.urlopen(req) as response:
                response_data = json.loads(response.read().decode('utf-8'))

                print(f"✓ Token exchange successful")

                return {
                    'statusCode': 200,
                    'headers': {
                        'Access-Control-Allow-Origin': '*',
                        'Content-Type': 'application/json'
                    },
                    'body': json.dumps({
                        'access_token': response_data.get('access_token'),
                        'refresh_token': response_data.get('refresh_token'),
                        'expires_in': response_data.get('expires_in'),
                        'token_type': response_data.get('token_type')
                    })
                }

        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            print(f"CyberArk error: {e.code} - {error_body}")

            return error_response(
                e.code,
                f"Token exchange failed: {error_body}"
            )

    except Exception as e:
        print(f"Error: {str(e)}")
        return error_response(500, f"Internal error: {str(e)}")

def error_response(status_code, message):
    """Return error response with CORS headers"""
    return {
        'statusCode': status_code,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        },
        'body': json.dumps({'error': message})
    }
