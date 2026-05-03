from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload
from database import get_db
from models import User, Comment
from schemas import UserDetailResponse, UserUpdate, EventListResponse, CommunityListResponse, CommentListResponse
from security import get_current_user, hash_password, verify_password

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/profile", response_model=UserDetailResponse)
async def get_profile(
    current_user: User = Depends(get_current_user)
):
    """Get current user profile"""
    return current_user


@router.put("/profile", response_model=UserDetailResponse)
async def update_profile(
    update_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update user profile"""
    # Check if password change is requested
    if update_data.new_password:
        if not update_data.current_password:
            raise HTTPException(status_code=400, detail="Current password required")
        
        if not verify_password(update_data.current_password, current_user.hashed_password):
            raise HTTPException(status_code=400, detail="Current password is incorrect")
        
        current_user.hashed_password = hash_password(update_data.new_password)
    
    # Update other fields
    if update_data.username:
        existing = db.query(User).filter(
            User.username == update_data.username,
            User.id != current_user.id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Username already taken")
        current_user.username = update_data.username
    
    if update_data.email:
        existing = db.query(User).filter(
            User.email == update_data.email,
            User.id != current_user.id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
        current_user.email = update_data.email
    
    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("/saved-events", response_model=EventListResponse)
async def get_saved_events(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's saved events"""
    events = current_user.saved_events
    total = len(events)
    return {"total": total, "events": events}


@router.get("/followed-communities", response_model=CommunityListResponse)
async def get_followed_communities(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's followed communities"""
    communities = current_user.followed_communities
    total = len(communities)
    return {"total": total, "communities": communities}


@router.get("/comments", response_model=CommentListResponse)
async def get_my_comments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's own comments"""
    comments = (
        db.query(Comment)
        .options(joinedload(Comment.event))
        .filter(Comment.user_id == current_user.id)
        .order_by(Comment.created_at.desc())
        .all()
    )
    total = len(comments)
    payload = [
        {
            "id": item.id,
            "content": item.content,
            "user_id": item.user_id,
            "event_id": item.event_id,
            "event_title": item.event.title if item.event else None,
            "created_at": item.created_at,
            "user": None,
        }
        for item in comments
    ]
    return {"total": total, "comments": payload}
