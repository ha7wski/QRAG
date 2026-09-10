"""Feedback endpoint (👍/👎): a KPI signal on answer quality.

Write-only over the store. The `GET /feedback/stats` read-back was removed — no page
read it — but the running totals it served still travel back on every `POST /feedback`
response, so the writer that cares sees them without a second endpoint. The store and
its `feedback_stats()` are unchanged.
"""
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
