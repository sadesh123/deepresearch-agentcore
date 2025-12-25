"""
FastAPI backend for Deep Research Agent.

Provides REST API endpoints for:
- LLM Council deliberation
- DxO sequential research
- Conversation management
"""

import sys
import os
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

from backend.config import BACKEND_PORT, CORS_ORIGINS, AWS_REGION, BEDROCK_MODEL_ID, COUNCIL_NUM_MEMBERS, ARXIV_MAX_RESULTS
from backend.models import (
    ResearchRequest, CouncilResponse, DxOResponse,
    ConversationCreate, ConversationList, HealthResponse
)
from backend.storage import storage
from agents.council_agent import create_council_agent
from agents.dxo_agent import create_dxo_agent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global agent instances
council_agent = None
dxo_agent = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize agents on startup."""
    global council_agent, dxo_agent

    logger.info("Initializing agents...")
    council_agent = create_council_agent(num_members=COUNCIL_NUM_MEMBERS)
    dxo_agent = create_dxo_agent(arxiv_max_results=ARXIV_MAX_RESULTS)
    logger.info("Agents initialized successfully")

    yield

    logger.info("Shutting down...")


# Create FastAPI app
app = FastAPI(
    title="Deep Research Agent API",
    description="REST API for LLM Council and DxO Decision Framework agents",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint - health check."""
    return HealthResponse(
        status="healthy",
        aws_region=AWS_REGION,
        bedrock_model=BEDROCK_MODEL_ID
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        aws_region=AWS_REGION,
        bedrock_model=BEDROCK_MODEL_ID
    )


@app.post("/api/council", response_model=CouncilResponse)
async def run_council(request: ResearchRequest):
    """
    Run LLM Council 3-stage deliberation.

    Args:
        request: Research question

    Returns:
        Council deliberation results with all stages
    """
    try:
        logger.info(f"Council request: {request.question[:100]}...")

        if not council_agent:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Council agent not initialized"
            )

        # Run council deliberation
        result = await council_agent.deliberate(request.question)

        response = CouncilResponse(
            question=result['question'],
            stage1=result['stage1'],
            stage2=result['stage2'],
            stage3=result['stage3'],
            metadata=result['metadata']
        )

        logger.info("Council deliberation completed successfully")
        return response

    except Exception as e:
        logger.error(f"Council error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Council deliberation failed: {str(e)}"
        )


@app.post("/api/dxo", response_model=DxOResponse)
async def run_dxo(request: ResearchRequest):
    """
    Run DxO sequential research workflow.

    Args:
        request: Research question

    Returns:
        DxO research workflow results with all steps
    """
    try:
        logger.info(f"DxO request: {request.question[:100]}...")

        if not dxo_agent:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="DxO agent not initialized"
            )

        # Run DxO research
        result = await dxo_agent.research(request.question)

        response = DxOResponse(
            question=result['question'],
            workflow=result['workflow'],
            metadata=result['metadata']
        )

        logger.info("DxO research completed successfully")
        return response

    except Exception as e:
        logger.error(f"DxO error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"DxO research failed: {str(e)}"
        )


@app.post("/api/conversations")
async def create_conversation(request: ConversationCreate):
    """Create a new conversation."""
    try:
        conversation = storage.create_conversation()

        if request.initial_message:
            storage.add_message(
                conversation_id=conversation.id,
                role="user",
                content=request.initial_message
            )

        return conversation

    except Exception as e:
        logger.error(f"Error creating conversation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/api/conversations", response_model=ConversationList)
async def list_conversations():
    """List all conversations."""
    try:
        conversations = storage.list_conversations()
        return ConversationList(conversations=conversations)

    except Exception as e:
        logger.error(f"Error listing conversations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/api/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get a specific conversation."""
    try:
        conversation = storage.get_conversation(conversation_id)

        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )

        return conversation

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post("/api/conversations/{conversation_id}/message")
async def add_message_to_conversation(conversation_id: str, request: ResearchRequest):
    """
    Add a message to a conversation and get agent response.

    Args:
        conversation_id: Conversation ID
        request: Research request with question and mode

    Returns:
        Updated conversation with agent response
    """
    try:
        # Add user message
        conversation = storage.add_message(
            conversation_id=conversation_id,
            role="user",
            content=request.question,
            mode=request.mode
        )

        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )

        # Run appropriate agent
        if request.mode == "council":
            result = await council_agent.deliberate(request.question)
            response_data = {
                'question': result['question'],
                'stage1': result['stage1'],
                'stage2': result['stage2'],
                'stage3': result['stage3'],
                'metadata': result['metadata']
            }
        elif request.mode == "dxo":
            result = await dxo_agent.research(request.question)
            response_data = {
                'question': result['question'],
                'workflow': result['workflow'],
                'metadata': result['metadata']
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid mode. Must be 'council' or 'dxo'"
            )

        # Add assistant message
        conversation = storage.add_message(
            conversation_id=conversation_id,
            role="assistant",
            mode=request.mode,
            data=response_data
        )

        return conversation

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding message: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation."""
    try:
        success = storage.delete_conversation(conversation_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )

        return {"message": "Conversation deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting conversation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# =============================================================================
# AgentCore Runtime Endpoints
# =============================================================================

class AgentCoreInput(BaseModel):
    """AgentCore invocation input format."""
    mode: str = "council"  # "council" or "dxo"
    prompt: str


class AgentCoreRequest(BaseModel):
    """AgentCore invocation request format."""
    input: AgentCoreInput


class AgentCoreMessage(BaseModel):
    """AgentCore message format."""
    role: str
    content: list[Dict[str, Any]]


class AgentCoreOutput(BaseModel):
    """AgentCore invocation output format."""
    message: AgentCoreMessage
    timestamp: str


class AgentCoreResponse(BaseModel):
    """AgentCore invocation response format."""
    output: AgentCoreOutput


@app.get("/ping")
async def ping():
    """
    Health check endpoint required by AgentCore Runtime.

    Returns:
        Simple health status
    """
    return {
        "status": "healthy",
        "service": "Deep Research Agent",
        "aws_region": AWS_REGION,
        "bedrock_model": BEDROCK_MODEL_ID
    }


@app.post("/invocations", response_model=AgentCoreResponse)
async def invocations(request: AgentCoreRequest):
    """
    Main AgentCore Runtime invocation endpoint.

    This endpoint receives requests from AWS Bedrock AgentCore Runtime
    and routes them to the appropriate agent (Council or DxO).

    Request format:
        {
            "input": {
                "mode": "council" | "dxo",
                "prompt": "user question"
            }
        }

    Response format:
        {
            "output": {
                "message": {
                    "role": "assistant",
                    "content": [{"text": "response"}]
                },
                "timestamp": "ISO timestamp"
            }
        }
    """
    try:
        mode = request.input.mode.lower()
        prompt = request.input.prompt

        logger.info(f"AgentCore invocation - Mode: {mode}, Prompt: {prompt[:100]}...")

        # Route to appropriate agent
        if mode == "council":
            if not council_agent:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Council agent not initialized"
                )

            result = await council_agent.deliberate(prompt)

            # Format council results as text
            response_text = f"""# LLM Council Deliberation Results

## Question
{result['question']}

## Stage 1: Independent Responses
"""
            for i, response in enumerate(result['stage1'], 1):
                response_text += f"\n### Member {response['member_id']}\n{response['content']}\n"

            response_text += f"""
## Stage 2: Peer Review & Rankings

### Aggregate Rankings
"""
            for rank in result['metadata']['aggregate_rankings']:
                response_text += f"- {rank}\n"

            response_text += f"""
## Stage 3: Chairman Synthesis

{result['stage3']['content']}
"""

        elif mode == "dxo":
            if not dxo_agent:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="DxO agent not initialized"
                )

            result = await dxo_agent.research(prompt)

            # Format DxO results as text
            response_text = f"""# DxO Decision Framework Results

## Question
{result['question']}

## Sequential Research Workflow
"""
            for step in result['workflow']:
                response_text += f"""
### {step['role']}

{step['output']}
"""

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid mode '{mode}'. Must be 'council' or 'dxo'"
            )

        # Format response in AgentCore format
        agentcore_response = AgentCoreResponse(
            output=AgentCoreOutput(
                message=AgentCoreMessage(
                    role="assistant",
                    content=[{"text": response_text}]
                ),
                timestamp=datetime.utcnow().isoformat()
            )
        )

        logger.info(f"AgentCore invocation completed successfully - Mode: {mode}")
        return agentcore_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"AgentCore invocation error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Invocation failed: {str(e)}"
        )


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred"}
    )


if __name__ == "__main__":
    logger.info(f"Starting backend on port {BACKEND_PORT}...")
    logger.info(f"AWS Region: {AWS_REGION}")
    logger.info(f"Bedrock Model: {BEDROCK_MODEL_ID}")
    logger.info(f"CORS Origins: {CORS_ORIGINS}")

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=BACKEND_PORT,
        reload=True,
        log_level="info"
    )
