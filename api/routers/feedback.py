"""Feedback endpoint (👍/👎): a KPI signal on answer quality."""
from __future__ import annotations

from fastapi import APIRouter, Request

from api.models.feedback import FeedbackRequest, FeedbackResponse

router = APIRouter(tags=["feedback"])


@router.post("/feedback", response_model=FeedbackResponse)
def submit_feedback(req: FeedbackRequest, request: Request) -> FeedbackResponse:
    """Record a thumbs rating for one assistant answer; return running stats."""
    store = request.app.state.store
    store.record_feedback(
        session_id=req.session_id,
        message_index=req.message_index,
        rating=req.rating,
        question=req.question,
        answer=req.answer,
    )
    return FeedbackResponse(ok=True, stats=store.feedback_stats())


@router.get("/feedback/stats", response_model=FeedbackResponse)
def feedback_stats(request: Request) -> FeedbackResponse:
    """Aggregate thumbs counts (up/down/total)."""
    return FeedbackResponse(ok=True, stats=request.app.state.store.feedback_stats())
