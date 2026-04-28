from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import Optional, List
from database import get_db
from models import User, UserRole, Event, EventType, DangerLevel, Community, Comment
from schemas import EventResponse, EventCreate, EventUpdate, EventListResponse, EventDetailResponse
from security import get_current_user, get_optional_user
from services.community_intelligence import infer_community, upsert_community_report

router = APIRouter(prefix="/api/events", tags=["events"])


@router.post("", response_model=EventResponse)
async def create_event(
    payload: EventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create event and auto-infer its core community from geo fields."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    inferred = infer_community(
        db,
        latitude=payload.latitude,
        longitude=payload.longitude,
        address=payload.address,
        zipcode=payload.zipcode,
        max_distance_km=180.0,
        allow_dynamic_core=False,
        enforce_existing=True,
    )
    if not inferred:
        raise HTTPException(status_code=400, detail="Unable to infer community from location fields")

    db_event = Event(
        title=payload.title,
        description=payload.description,
        event_type=payload.event_type,
        danger_level=payload.danger_level,
        community_id=inferred.id,
        address=payload.address,
        latitude=payload.latitude,
        longitude=payload.longitude,
        zipcode=payload.zipcode or inferred.zipcode,
        event_time=payload.event_time,
        data_source=payload.data_source,
        source_url=payload.source_url,
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    upsert_community_report(db, inferred.id, commit=True)

    return {
        **{c.name: getattr(db_event, c.name) for c in db_event.__table__.columns},
        "community_name": inferred.name,
        "comment_count": 0,
        "liked": False,
        "saved": False,
    }


@router.get("", response_model=EventListResponse)
async def list_events(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100, alias='page_size'),
    pageSize: Optional[int] = Query(None, ge=1, le=100, alias='pageSize'),
    limit: Optional[int] = Query(None, ge=1, le=100),
    event_type: Optional[str] = Query(None, alias='event_type'),
    eventTypes: Optional[List[str]] = Query(None, alias='event_types'),
    eventType: Optional[str] = Query(None, alias='eventType'),
    community: Optional[int] = None,
    time_range: Optional[int] = Query(None, alias='time_range'),
    timeRange: Optional[int] = Query(None, alias='timeRange'),
    danger_level: Optional[str] = Query(None, alias='danger_level'),
    dangerLevel: Optional[str] = Query(None, alias='dangerLevel'),
    sort_by: str = Query('publishTime', alias='sort_by'),
    sortBy: Optional[str] = Query(None, alias='sortBy'),
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """List all events with filtering and sorting"""
    query = db.query(Event)
    
    # Normalize incoming filter aliases
    if pageSize is not None:
        page_size = pageSize
    if limit is not None:
        page_size = limit
    if eventType is not None:
        eventTypes = eventTypes or [eventType]
    if timeRange is not None:
        time_range = timeRange
    if dangerLevel is not None:
        danger_level = dangerLevel
    if sortBy is not None:
        sort_by = sortBy

    # Apply filters
    if eventTypes:
        normalized_types = []
        for item in eventTypes:
            try:
                normalized_types.append(EventType(item))
            except Exception:
                continue
        if normalized_types:
            query = query.filter(Event.event_type.in_(normalized_types))
    elif event_type:
        try:
            normalized_type = EventType(event_type)
            query = query.filter(Event.event_type == normalized_type)
        except Exception:
            pass

    if community:
        query = query.filter(Event.community_id == community)

    if danger_level:
        query = query.filter(Event.danger_level == danger_level)

    if time_range is not None and int(time_range) > 0:
        cutoff = datetime.now(timezone.utc) - timedelta(days=int(time_range))
        query = query.filter(
            or_(
                Event.event_time >= cutoff,
                and_(Event.event_time.is_(None), Event.created_at >= cutoff),
            )
        )

    if search:
        query = query.join(Community)
        query = query.filter(
            or_(
                Event.title.ilike(f"%{search}%"),
                Event.address.ilike(f"%{search}%"),
                Event.zipcode.ilike(f"%{search}%"),
                Community.name.ilike(f"%{search}%"),
            )
        )
    
    # Apply sorting
    if sort_by == "likes":
        query = query.order_by(Event.like_count.desc())
    elif sort_by == "comments":
        query = query.order_by(Event.comment_count.desc())
    else:
        query = query.order_by(Event.created_at.desc())
    
    # Get total count
    total = query.count()
    
    # Paginate
    skip = (page - 1) * page_size
    events = query.offset(skip).limit(page_size).all()
    event_ids = [item.id for item in events]
    community_ids = list({item.community_id for item in events if item.community_id is not None})

    visible_comment_count_map = {}
    if event_ids:
        rows = (
            db.query(Comment.event_id, func.count(Comment.id))
            .filter(
                Comment.event_id.in_(event_ids),
                or_(Comment.is_flagged.is_(False), Comment.is_flagged.is_(None)),
            )
            .group_by(Comment.event_id)
            .all()
        )
        visible_comment_count_map = {event_id: count for event_id, count in rows}

    community_name_map = {}
    if community_ids:
        community_rows = (
            db.query(Community.id, Community.name)
            .filter(Community.id.in_(community_ids))
            .all()
        )
        community_name_map = {community_id: community_name for community_id, community_name in community_rows}
    
    # Add user-specific fields
    event_list = []
    for event in events:
        event_dict = {
            **{c.name: getattr(event, c.name) for c in event.__table__.columns},
            "comment_count": visible_comment_count_map.get(event.id, 0),
            "community_name": community_name_map.get(event.community_id),
            "community": community_name_map.get(event.community_id),
            "liked": bool(current_user and event in current_user.liked_events) if current_user else False,
            "saved": bool(current_user and event in current_user.saved_events) if current_user else False,
        }
        event_list.append(event_dict)
    
    return {"total": total, "events": event_list}


@router.get("/{event_id}", response_model=EventDetailResponse)
async def get_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """Get event details"""
    event = db.query(Event).filter(Event.id == event_id).first()
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    visible_comment_count = (
        db.query(func.count(Comment.id))
        .filter(
            Comment.event_id == event.id,
            or_(Comment.is_flagged.is_(False), Comment.is_flagged.is_(None)),
        )
        .scalar()
    )
    
    event_data = {
        **{c.name: getattr(event, c.name) for c in event.__table__.columns},
        "comment_count": visible_comment_count or 0,
        "community": event.community,
        "comments": event.comments,
        "liked": bool(current_user and event in current_user.liked_events) if current_user else False,
        "saved": bool(current_user and event in current_user.saved_events) if current_user else False,
    }
    
    return event_data


@router.post("/{event_id}/like")
async def like_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Like an event"""
    event = db.query(Event).filter(Event.id == event_id).first()
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    if event not in current_user.liked_events:
        current_user.liked_events.append(event)
        event.like_count += 1
        db.commit()
    
    return {"message": "Event liked"}


@router.delete("/{event_id}/like")
async def unlike_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Unlike an event"""
    event = db.query(Event).filter(Event.id == event_id).first()
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    if event in current_user.liked_events:
        current_user.liked_events.remove(event)
        event.like_count = max(0, event.like_count - 1)
        db.commit()
    
    return {"message": "Event unliked"}


@router.post("/{event_id}/save")
async def save_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Save an event"""
    event = db.query(Event).filter(Event.id == event_id).first()
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    if event not in current_user.saved_events:
        current_user.saved_events.append(event)
        db.commit()
    
    return {"message": "Event saved"}


@router.delete("/{event_id}/save")
async def unsave_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Unsave an event"""
    event = db.query(Event).filter(Event.id == event_id).first()
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    if event in current_user.saved_events:
        current_user.saved_events.remove(event)
        db.commit()
    
    return {"message": "Event unsaved"}
