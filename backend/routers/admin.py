from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models import (
    Comment,
    Community,
    DangerLevel,
    Event,
    EventType,
    SensitiveWord,
    SpiderTask,
    User,
    UserRole,
)
from security import get_current_admin
from services.community_intelligence import ensure_core_communities, infer_community, upsert_community_report
from spider.crawler import scheduler

router = APIRouter(prefix="/api/admin", tags=["admin"])

SITE_CONFIG_FILE = Path(__file__).resolve().parent.parent / "site_config.json"
DEFAULT_SITE_CONFIG = {
    "site_name": "Community Safety Alert",
    "logo": "",
    "bilingual_enabled": True,
    "disclaimer": "Data provided for reference only. Not legal or safety advice.",
    "data_sources": "CrimeReports, CityProtect, local police public feeds",
}


class EventUpdatePayload(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    event_type: Optional[EventType] = None
    danger_level: Optional[DangerLevel] = None
    address: Optional[str] = None


class EventCreatePayload(BaseModel):
    title: str
    description: str
    event_type: EventType
    danger_level: DangerLevel = DangerLevel.MEDIUM
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    zipcode: Optional[str] = None
    event_time: Optional[datetime] = None
    data_source: str = "Admin Manual Input"
    source_url: Optional[str] = None
    community_id: Optional[int] = None


class CommunityCreatePayload(BaseModel):
    name: str
    state: str
    city: str
    zipcode: Optional[str] = None
    latitude: float
    longitude: float
    area: Optional[float] = None
    population: Optional[int] = None


class CommunityUpdatePayload(BaseModel):
    name: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    zipcode: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    area: Optional[float] = None
    population: Optional[int] = None
    safety_score: Optional[float] = None


class UserRolePayload(BaseModel):
    role: UserRole


class UserStatusPayload(BaseModel):
    is_active: bool


class CommentFlagPayload(BaseModel):
    is_flagged: bool


class SiteConfigPayload(BaseModel):
    site_name: str
    logo: Optional[str] = ""
    bilingual_enabled: bool = True
    disclaimer: str
    data_sources: str


class SensitiveWordPayload(BaseModel):
    word: str


def _load_site_config():
    if not SITE_CONFIG_FILE.exists():
        return DEFAULT_SITE_CONFIG.copy()
    import json

    with SITE_CONFIG_FILE.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return {**DEFAULT_SITE_CONFIG, **data}


def _save_site_config(config: dict):
    import json

    with SITE_CONFIG_FILE.open("w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


@router.get("/dashboard")
async def get_dashboard(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    total_users = db.query(User).count()
    total_communities = db.query(Community).count()
    total_events = db.query(Event).count()
    total_comments = db.query(Comment).count()

    now = datetime.now(timezone.utc)
    today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    today_new_events = db.query(Event).filter(Event.created_at >= today_start).count()
    today_new_users = db.query(User).filter(User.created_at >= today_start).count()

    stats = {
        "total_users": total_users,
        "total_communities": total_communities,
        "total_events": total_events,
        "total_comments": total_comments,
        "today_new_events": today_new_events,
        "today_new_users": today_new_users,
    }
    return {"stats": stats}


@router.get("/events")
async def list_admin_events(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    event_type: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    query = db.query(Event).options(joinedload(Event.community))
    if event_type:
        try:
            query = query.filter(Event.event_type == EventType(event_type))
        except Exception:
            pass

    total = query.count()
    skip = (page - 1) * page_size
    events = query.order_by(Event.created_at.desc()).offset(skip).limit(page_size).all()
    return {"total": total, "page": page, "events": events}


@router.post("/events")
async def create_admin_event(
    payload: EventCreatePayload,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    ensure_core_communities(db, commit=True)

    inferred = infer_community(
        db,
        latitude=payload.latitude,
        longitude=payload.longitude,
        address=payload.address,
        zipcode=payload.zipcode,
        max_distance_km=180.0,
        allow_dynamic_core=True,
    )
    if not inferred:
        raise HTTPException(status_code=400, detail="Unable to infer community from location fields")

    event = Event(
        title=payload.title,
        description=payload.description,
        event_type=payload.event_type,
        danger_level=payload.danger_level,
        community_id=inferred.id,
        address=payload.address or inferred.city,
        latitude=payload.latitude if payload.latitude is not None else inferred.latitude,
        longitude=payload.longitude if payload.longitude is not None else inferred.longitude,
        zipcode=payload.zipcode or inferred.zipcode,
        event_time=payload.event_time or datetime.now(timezone.utc),
        data_source=payload.data_source,
        source_url=payload.source_url,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    upsert_community_report(db, inferred.id, commit=True)
    return {"event": event, "inferred_community": inferred.name}


@router.put("/events/{event_id}")
async def update_admin_event(
    event_id: int,
    payload: EventUpdatePayload,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(event, key, value)
    db.commit()
    db.refresh(event)
    return event


@router.delete("/events/{event_id}")
async def delete_admin_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    db.delete(event)
    db.commit()
    return {"message": "Event deleted"}


@router.get("/communities")
async def list_admin_communities(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    state: Optional[str] = None,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    query = db.query(Community)
    if state:
        query = query.filter(Community.state == state)
    total = query.count()
    skip = (page - 1) * page_size
    communities = query.order_by(Community.safety_score.desc()).offset(skip).limit(page_size).all()
    return {"total": total, "page": page, "communities": communities}


@router.post("/communities")
async def create_admin_community(
    payload: CommunityCreatePayload,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    existing = db.query(Community).filter(Community.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Community name already exists")
    community = Community(**payload.model_dump())
    db.add(community)
    db.commit()
    db.refresh(community)
    return community


@router.put("/communities/{community_id}")
async def update_admin_community(
    community_id: int,
    payload: CommunityUpdatePayload,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    community = db.query(Community).filter(Community.id == community_id).first()
    if not community:
        raise HTTPException(status_code=404, detail="Community not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(community, key, value)
    db.commit()
    db.refresh(community)
    return community


@router.delete("/communities/{community_id}")
async def delete_admin_community(
    community_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    community = db.query(Community).filter(Community.id == community_id).first()
    if not community:
        raise HTTPException(status_code=404, detail="Community not found")
    db.delete(community)
    db.commit()
    return {"message": "Community deleted"}


@router.get("/comments")
async def list_admin_comments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    query = db.query(Comment).options(joinedload(Comment.user), joinedload(Comment.event))
    if status == "flagged":
        query = query.filter(Comment.is_flagged.is_(True))
    total = query.count()
    skip = (page - 1) * page_size
    comments = query.order_by(Comment.created_at.desc()).offset(skip).limit(page_size).all()
    return {"total": total, "page": page, "comments": comments}


@router.post("/comments/{comment_id}/flag")
async def flag_admin_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    comment.is_flagged = True
    db.commit()
    return {"message": "Comment flagged"}


@router.post("/comments/{comment_id}/unflag")
async def unflag_admin_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    comment.is_flagged = False
    db.commit()
    return {"message": "Comment unflagged"}


@router.put("/comments/{comment_id}/status")
async def update_comment_flag_status(
    comment_id: int,
    payload: CommentFlagPayload,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    comment.is_flagged = bool(payload.is_flagged)
    db.commit()
    db.refresh(comment)
    return {"message": "Comment status updated", "comment": comment}


@router.delete("/comments/{comment_id}")
async def delete_admin_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    event = db.query(Event).filter(Event.id == comment.event_id).first()
    if event:
        event.comment_count = max(0, (event.comment_count or 0) - 1)

    db.delete(comment)
    db.commit()
    return {"message": "Comment deleted"}


@router.get("/users")
async def list_admin_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    query = db.query(User).order_by(User.created_at.desc())
    total = query.count()
    skip = (page - 1) * page_size
    users = query.offset(skip).limit(page_size).all()
    return {"total": total, "page": page, "users": users}


@router.put("/users/{user_id}/role")
async def update_admin_user_role(
    user_id: int,
    payload: UserRolePayload,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.role = payload.role
    db.commit()
    db.refresh(user)
    return user


@router.put("/users/{user_id}/status")
async def update_admin_user_status(
    user_id: int,
    payload: UserStatusPayload,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = payload.is_active
    db.commit()
    db.refresh(user)
    return user


@router.delete("/users/{user_id}")
async def delete_admin_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete current admin")
    db.delete(user)
    db.commit()
    return {"message": "User deleted"}


@router.get("/spider")
async def get_spider_status(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    tasks = db.query(SpiderTask).all()
    status_info = {
        "is_running": False,
        "last_run": None,
        "next_run": None,
        "success_count": 0,
        "failure_count": 0,
        "last_error": None,
    }
    if tasks:
        task = tasks[0]
        status_info["last_run"] = task.last_run
        status_info["next_run"] = task.next_run
        status_info["success_count"] = task.success_count
        status_info["failure_count"] = task.failure_count
        status_info["last_error"] = task.last_error
    if scheduler.last_run:
        status_info["last_run"] = scheduler.last_run
    status_info["is_running"] = scheduler.running
    status_info["success_count"] = max(status_info["success_count"], scheduler.success_count)
    status_info["failure_count"] = max(status_info["failure_count"], scheduler.failure_count)
    status_info["last_error"] = scheduler.last_error or status_info["last_error"]
    if scheduler.score_scheduler.running:
        job = scheduler.score_scheduler.get_job("community-score-recompute")
        if job and job.next_run_time:
            status_info["next_run"] = job.next_run_time
    return {"spider_status": status_info}


@router.post("/spider/trigger")
async def trigger_spider(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    summary = await scheduler.run_once(limit_per_source=80)

    task = db.query(SpiderTask).first()
    if not task:
        task = SpiderTask(name="public-open-data", url="multi-source-public-api", enabled=True)
        db.add(task)

    task.last_run = datetime.now(timezone.utc)
    task.success_count = scheduler.success_count
    task.failure_count = scheduler.failure_count
    task.last_error = scheduler.last_error
    db.commit()

    return {"message": "Spider task triggered", "summary": summary}


@router.post("/spider/stop")
async def stop_spider(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    return {"message": "Spider stopped"}


@router.get("/config")
async def get_site_config(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    config = _load_site_config()
    words = db.query(SensitiveWord).order_by(SensitiveWord.word.asc()).all()
    return {"config": config, "sensitive_words": words}


@router.put("/config")
async def update_site_config(
    payload: SiteConfigPayload,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    _save_site_config(payload.model_dump())
    return {"message": "Config updated", "config": payload.model_dump()}


@router.post("/sensitive-words")
async def create_sensitive_word(
    payload: SensitiveWordPayload,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    word = payload.word.strip()
    if not word:
        raise HTTPException(status_code=400, detail="Word cannot be empty")
    exists = db.query(SensitiveWord).filter(SensitiveWord.word == word).first()
    if exists:
        raise HTTPException(status_code=400, detail="Word already exists")
    db_word = SensitiveWord(word=word)
    db.add(db_word)
    db.commit()
    db.refresh(db_word)
    return db_word


@router.delete("/sensitive-words/{word_id}")
async def delete_sensitive_word(
    word_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    word = db.query(SensitiveWord).filter(SensitiveWord.id == word_id).first()
    if not word:
        raise HTTPException(status_code=404, detail="Sensitive word not found")
    db.delete(word)
    db.commit()
    return {"message": "Sensitive word deleted"}
