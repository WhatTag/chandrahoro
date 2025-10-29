"""
AI Interpretation API endpoints for Vedic astrology charts.
Provides chart interpretation and Q&A functionality.
"""

import logging
import os
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai_service import AIService
from app.services.llm_service import LlmService
from app.core.database import get_db
from app.core.rbac import get_current_user
from app.models import User

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize services
llm_service = LlmService()


class ChartInterpretationRequest(BaseModel):
    """Request model for chart interpretation."""
    chart_data: Dict[str, Any]
    include_sections: Optional[List[str]] = None


class ChatMessage(BaseModel):
    """Chat message model."""
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    chart_data: Dict[str, Any]
    question: str
    conversation_history: Optional[List[ChatMessage]] = None


class FeedbackRequest(BaseModel):
    """Request model for feedback."""
    interpretation_id: str
    feedback: str  # "positive" or "negative"
    comments: Optional[str] = None


class PartnerDetails(BaseModel):
    """Partner birth details for compatibility analysis."""
    name: str
    birth_date: str  # YYYY-MM-DD format
    birth_time: str  # HH:MM format
    birth_location: str
    latitude: float
    longitude: float
    timezone: str


class CompatibilityRequest(BaseModel):
    """Request model for compatibility analysis."""
    primary_chart_data: Dict[str, Any]
    partner_details: PartnerDetails
    analysis_focus: Optional[List[str]] = None  # e.g., ["emotional", "intellectual", "physical", "spiritual"]


class MatchHoroscopeRequest(BaseModel):
    """Request model for traditional Vedic matchmaking analysis."""
    primary_chart_data: Dict[str, Any]
    partner_details: PartnerDetails


@router.post("/interpret")
async def interpret_chart(
    request: ChartInterpretationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate comprehensive AI interpretation of a Vedic astrology chart.

    Args:
        request: Chart data and interpretation preferences
        current_user: Current authenticated user
        db: Database session

    Returns:
        AI-generated interpretation with sections and metadata
    """
    try:
        print(f"DEBUG: Starting interpretation for user {current_user.id}")
        logger.info(f"Generating chart interpretation for user {current_user.id}")

        # Get user's LLM configuration
        llm_config = await llm_service.get_config(db, current_user.id)
        if not llm_config:
            raise HTTPException(
                status_code=400,
                detail="No LLM configuration found. Please configure your AI settings first."
            )

        if not llm_config.is_active:
            raise HTTPException(
                status_code=400,
                detail="LLM configuration is inactive. Please check your AI settings."
            )

        # Generate interpretation using user's LLM configuration
        result = await llm_service.generate_interpretation(
            db, current_user.id, request.chart_data, request.include_sections
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate interpretation: {result.get('error')}"
            )

        return {
            "success": True,
            "content": result.get("content"),
            "model": result.get("model"),
            "tokens": result.get("tokens"),
            "timestamp": result.get("timestamp")
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating interpretation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.post("/chat")
async def chat_about_chart(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Answer questions about a Vedic astrology chart.

    Args:
        request: Chart data, question, and conversation history
        current_user: Current authenticated user
        db: Database session

    Returns:
        AI-generated answer with context
    """
    try:
        logger.info(f"Processing chart question for user {current_user.id}: {request.question[:50]}...")

        # Get user's LLM configuration
        llm_config = await llm_service.get_config(db, current_user.id)
        if not llm_config:
            raise HTTPException(
                status_code=400,
                detail="No LLM configuration found. Please configure your AI settings first."
            )

        if not llm_config.is_active:
            raise HTTPException(
                status_code=400,
                detail="LLM configuration is inactive. Please check your AI settings."
            )
        
        # Convert ChatMessage objects to dicts
        history = []
        if request.conversation_history:
            history = [{"role": msg.role, "content": msg.content}
                      for msg in request.conversation_history]

        # Generate response using user's LLM configuration
        result = await llm_service.generate_chat_response(
            db, current_user.id, request.chart_data, request.question, history
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate response: {result.get('error')}"
            )
        
        return {
            "success": True,
            "answer": result.get("content"),
            "model": result.get("model"),
            "tokens": result.get("tokens"),
            "timestamp": result.get("timestamp")
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing chat: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.post("/feedback")
async def submit_feedback(request: FeedbackRequest):
    """
    Submit feedback on AI interpretation quality.
    
    Args:
        request: Feedback data
        
    Returns:
        Confirmation of feedback submission
    """
    try:
        logger.info(f"Feedback received: {request.feedback}")
        
        # In a real implementation, this would save to a database
        # For now, just log it
        feedback_data = {
            "interpretation_id": request.interpretation_id,
            "feedback": request.feedback,
            "comments": request.comments,
            "timestamp": __import__('datetime').datetime.utcnow().isoformat()
        }
        
        logger.info(f"Feedback data: {feedback_data}")
        
        return {
            "success": True,
            "message": "Feedback submitted successfully",
            "data": feedback_data
        }
    
    except Exception as e:
        logger.error(f"Error submitting feedback: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.get("/usage")
async def get_usage_stats(user_id: Optional[str] = Query(None)):
    """
    Get AI usage statistics for a user.
    
    Args:
        user_id: Optional user ID for tracking
        
    Returns:
        Usage statistics including tokens and costs
    """
    try:
        # In a real implementation, this would query a database
        # For now, return placeholder data
        return {
            "success": True,
            "data": {
                "user_id": user_id or "anonymous",
                "total_interpretations": 0,
                "total_questions": 0,
                "total_tokens_used": 0,
                "estimated_cost": 0.0,
                "daily_limit": 10,
                "daily_used": 0,
                "monthly_limit": 100,
                "monthly_used": 0
            },
            "message": "Usage statistics retrieved successfully"
        }
    
    except Exception as e:
        logger.error(f"Error retrieving usage stats: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.post("/regenerate")
async def regenerate_interpretation(request: ChartInterpretationRequest):
    """
    Regenerate chart interpretation (alternative version).
    
    Args:
        request: Chart data for regeneration
        
    Returns:
        New AI-generated interpretation
    """
    try:
        logger.info("Regenerating chart interpretation")
        
        # Check if AI is enabled
        if not os.getenv("ANTHROPIC_API_KEY") and not os.getenv("OPENAI_API_KEY"):
            raise HTTPException(
                status_code=503,
                detail="AI features are not configured"
            )
        
        # Generate new interpretation
        result = await ai_service.interpret_chart(request.chart_data)
        
        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=f"Failed to regenerate interpretation: {result.get('error')}"
            )
        
        return {
            "success": True,
            "data": {
                "interpretation": result.get("content"),
                "model": result.get("model"),
                "tokens": result.get("tokens"),
                "timestamp": result.get("timestamp")
            },
            "message": "Chart interpretation regenerated successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error regenerating interpretation: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.post("/compatibility")
async def analyze_compatibility(
    request: CompatibilityRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate compatibility analysis between two Vedic astrology charts.

    Args:
        request: Primary chart data and partner details
        current_user: Current authenticated user
        db: Database session

    Returns:
        AI-generated compatibility analysis
    """
    try:
        logger.info(f"Generating compatibility analysis for user {current_user.id}")

        # Get user's LLM configuration
        llm_config = await llm_service.get_config(db, current_user.id)
        if not llm_config:
            raise HTTPException(
                status_code=400,
                detail="No LLM configuration found. Please configure your AI settings first."
            )

        if not llm_config.is_active:
            raise HTTPException(
                status_code=400,
                detail="LLM configuration is inactive. Please check your AI settings."
            )

        # Generate partner's chart data (this would typically involve calling the chart calculation service)
        # For now, we'll pass the partner details to the LLM service
        partner_chart_data = {
            "birth_info": {
                "name": request.partner_details.name,
                "date": request.partner_details.birth_date,
                "time": request.partner_details.birth_time,
                "location": request.partner_details.birth_location,
                "latitude": request.partner_details.latitude,
                "longitude": request.partner_details.longitude,
                "timezone": request.partner_details.timezone
            }
        }

        # Generate compatibility analysis using user's LLM configuration
        result = await llm_service.generate_compatibility_analysis(
            db,
            current_user.id,
            request.primary_chart_data,
            partner_chart_data,
            request.analysis_focus
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate compatibility analysis: {result.get('error')}"
            )

        return {
            "success": True,
            "content": result.get("content"),
            "model": result.get("model"),
            "tokens": result.get("tokens"),
            "timestamp": result.get("timestamp"),
            "compatibility_score": result.get("compatibility_score"),
            "key_insights": result.get("key_insights")
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating compatibility analysis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.post("/match-horoscope")
async def analyze_match_horoscope(
    request: MatchHoroscopeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate traditional Vedic astrology matchmaking analysis with Ashtakoot scoring.

    Args:
        request: Primary chart data and partner details
        current_user: Current authenticated user
        db: Database session

    Returns:
        Traditional matchmaking analysis with detailed Ashtakoot scores
    """
    try:
        logger.info(f"Generating match horoscope analysis for user {current_user.id}")

        # Get user's LLM configuration
        llm_config = await llm_service.get_config(db, current_user.id)
        if not llm_config:
            raise HTTPException(
                status_code=400,
                detail="Please configure your AI settings first"
            )

        # Calculate partner's chart data (simplified for now)
        partner_chart_data = {
            "birth_details": {
                "name": request.partner_details.name,
                "birth_date": request.partner_details.birth_date,
                "birth_time": request.partner_details.birth_time,
                "birth_location": request.partner_details.birth_location,
                "latitude": request.partner_details.latitude,
                "longitude": request.partner_details.longitude,
                "timezone": request.partner_details.timezone
            }
        }

        # Generate match horoscope analysis using user's LLM configuration
        result = await llm_service.generate_match_horoscope_analysis(
            db,
            current_user.id,
            request.primary_chart_data,
            partner_chart_data
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate match horoscope analysis: {result.get('error')}"
            )

        # Return the complete result from LLM service (includes new PDF-style format)
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating match horoscope analysis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.post("/match-horoscope/export")
async def export_match_horoscope_pdf(
    request: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Export match horoscope analysis as PDF.

    Args:
        request: Analysis data and user details
        current_user: Current authenticated user
        db: Database session

    Returns:
        PDF file download
    """
    try:
        logger.info(f"Exporting match horoscope PDF for user {current_user.id}")

        # Generate PDF using the analysis data
        pdf_result = await llm_service.generate_match_horoscope_pdf(
            request.get("analysis_data"),
            request.get("user_name"),
            request.get("partner_name")
        )

        if not pdf_result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate PDF: {pdf_result.get('error')}"
            )

        # Return PDF as response
        from fastapi.responses import Response
        return Response(
            content=pdf_result.get("pdf_content"),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=match-horoscope-{request.get('partner_name', 'partner').replace(' ', '-')}.pdf"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting match horoscope PDF: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.get("/test")
async def test_ai_api():
    """Test endpoint to verify AI API is working."""
    return {
        "status": "healthy",
        "message": "AI API is operational",
        "provider": ai_provider,
        "endpoints": [
            "POST /api/v1/ai/interpret - Generate chart interpretation",
            "POST /api/v1/ai/chat - Ask questions about chart",
            "POST /api/v1/ai/feedback - Submit feedback",
            "GET /api/v1/ai/usage - Get usage statistics",
            "POST /api/v1/ai/regenerate - Regenerate interpretation"
        ]
    }

