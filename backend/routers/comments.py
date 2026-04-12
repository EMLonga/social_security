from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload
from sqlalchemy import or_, func
from typing import Optional
from database import get_db
from models import Comment, Event, User, SensitiveWord
from schemas import CommentCreate, CommentResponse, CommentListResponse
from security import get_current_user

router = APIRouter(prefix="/api/events", tags=["comments"])


def _sync_event_comment_count(db: Session, event: Event):
    visible_count = (
        db.query(func.count(Comment.id))
        .filter(
            Comment.event_id == event.id,
            or_(Comment.is_flagged.is_(False), Comment.is_flagged.is_(None)),
        )
        .scalar()
    )
    event.comment_count = visible_count or 0


@router.get("/{event_id}/comments", response_model=CommentListResponse)
async def list_comments(
    event_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = "recent",
    db: Session = Depends(get_db)
):
    """List comments for an event"""
    event = db.query(Event).filter(Event.id == event_id).first()
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    query = (
        db.query(Comment)
        .options(joinedload(Comment.user))
        .filter(
            Comment.event_id == event_id,
            or_(Comment.is_flagged.is_(False), Comment.is_flagged.is_(None))
        )
    )
    
    if sort_by == "popular":
        query = query.order_by(Comment.id.desc())  # Simplified, can add like_count later
    else:
        query = query.order_by(Comment.created_at.desc())
    
    total = query.count()
    skip = (page - 1) * page_size
    comments = query.offset(skip).limit(page_size).all()
    
    return {"total": total, "comments": comments}


@router.post("/{event_id}/comments", response_model=CommentResponse)
async def create_comment(
    event_id: int,
    comment_data: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new comment"""
    event = db.query(Event).filter(Event.id == event_id).first()
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Check for sensitive words (simplified)
    sensitive_words = db.query(SensitiveWord).all()
    content_lower = comment_data.content.lower()
    for word in sensitive_words:
        if word.word.lower() in content_lower:
            raise HTTPException(
                status_code=400,
                detail="Comment contains sensitive content"
            )
    
    db_comment = Comment(
        content=comment_data.content,
        user_id=current_user.id,
        event_id=event_id
    )
    db.add(db_comment)
    db.flush()
    _sync_event_comment_count(db, event)
    db.commit()
    db.refresh(db_comment)
    db_comment = db.query(Comment).options(joinedload(Comment.user)).filter(Comment.id == db_comment.id).first()
    return db_comment


@router.delete("/{event_id}/comments/{comment_id}")
async def delete_comment(
    event_id: int,
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a comment"""
    comment = db.query(Comment).filter(
        Comment.id == comment_id,
        Comment.event_id == event_id
    ).first()
    
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    if comment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this comment")
    
    event = db.query(Event).filter(Event.id == event_id).first()
    db.delete(comment)
    db.flush()
    _sync_event_comment_count(db, event)
    db.commit()
    
    return {"message": "Comment deleted"}
