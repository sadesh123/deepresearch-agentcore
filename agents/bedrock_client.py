"""
AWS Bedrock client for Claude model interactions.
"""

import json
import boto3
import logging
from typing import Dict, List, Optional, Any
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class BedrockClient:
    """Client for interacting with AWS Bedrock Claude models."""

    def __init__(
        self,
        model_id: str = "us.anthropic.claude-3-5-haiku-20241022-v1:0",
        region: str = "us-east-1"
    ):
        """
        Initialize Bedrock client.

        Args:
            model_id: Bedrock model identifier
            region: AWS region
        """
        self.model_id = model_id
        self.region = region
        self.client = boto3.client(
            service_name='bedrock-runtime',
            region_name=region
        )
        logger.info(f"Initialized Bedrock client with model: {model_id}")

    def invoke(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        top_p: float = 0.9
    ) -> Dict[str, Any]:
        """
        Invoke Claude model with a single user message.

        Args:
            system_prompt: System prompt defining role/behavior
            user_message: User's message/question
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0-1)
            top_p: Nucleus sampling parameter

        Returns:
            Dict with 'content' (response text) and 'usage' (token counts)
        """
        try:
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "top_p": top_p,
                "system": system_prompt,
                "messages": [
                    {
                        "role": "user",
                        "content": user_message
                    }
                ]
            }

            response = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body)
            )

            response_body = json.loads(response['body'].read())

            # Extract text content from response
            content = ""
            if 'content' in response_body and len(response_body['content']) > 0:
                content = response_body['content'][0].get('text', '')

            return {
                'content': content,
                'usage': response_body.get('usage', {}),
                'stop_reason': response_body.get('stop_reason', '')
            }

        except ClientError as e:
            logger.error(f"Bedrock API error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error invoking model: {str(e)}")
            raise

    def invoke_multi_turn(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 4096,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        Invoke Claude model with multi-turn conversation.

        Args:
            system_prompt: System prompt
            messages: List of {"role": "user"|"assistant", "content": "text"}
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature

        Returns:
            Dict with 'content' and 'usage'
        """
        try:
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "system": system_prompt,
                "messages": messages
            }

            response = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body)
            )

            response_body = json.loads(response['body'].read())

            content = ""
            if 'content' in response_body and len(response_body['content']) > 0:
                content = response_body['content'][0].get('text', '')

            return {
                'content': content,
                'usage': response_body.get('usage', {}),
                'stop_reason': response_body.get('stop_reason', '')
            }

        except Exception as e:
            logger.error(f"Error in multi-turn invocation: {str(e)}")
            raise

    async def invoke_async(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: int = 4096,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        Async version of invoke (uses sync client in executor).

        Args:
            system_prompt: System prompt
            user_message: User message
            max_tokens: Maximum tokens
            temperature: Sampling temperature

        Returns:
            Dict with 'content' and 'usage'
        """
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.invoke(system_prompt, user_message, max_tokens, temperature)
        )


def create_bedrock_client(
    model_id: Optional[str] = None,
    region: Optional[str] = None
) -> BedrockClient:
    """
    Factory function to create a Bedrock client.

    Args:
        model_id: Optional model ID override
        region: Optional region override

    Returns:
        BedrockClient instance
    """
    import os

    model = model_id or os.getenv('BEDROCK_MODEL_ID', 'us.anthropic.claude-3-5-haiku-20241022-v1:0')
    aws_region = region or os.getenv('AWS_REGION', 'us-east-1')

    return BedrockClient(model_id=model, region=aws_region)


if __name__ == "__main__":
    # Test the client
    client = create_bedrock_client()

    response = client.invoke(
        system_prompt="You are a helpful AI assistant.",
        user_message="What is quantum computing in one sentence?"
    )

    print(f"Response: {response['content']}")
    print(f"Tokens used: {response['usage']}")
