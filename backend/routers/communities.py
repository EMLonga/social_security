from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional
from database import get_db
from models import Community, CommunityReport, User
from schemas import CommunityResponse, CommunityListResponse, CommunityDetailResponse
from security import get_current_user, get_optional_user
from services.community_intelligence import build_community_report, upsert_community_report

router = APIRouter(prefix="/api/communities", tags=["communities"])


def _build_community_report(events):
    return build_community_report(events)


@router.get("", response_model=CommunityListResponse)
async def list_communities(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100, alias='page_size'),
    pageSize: Optional[int] = Query(None, ge=1, le=100, alias='pageSize'),
    limit: Optional[int] = Query(None, ge=1, le=100),
    state: Optional[str] = None,
    city: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = Query('safety_score', alias='sort_by'),
    sortOrder: str = Query('desc', alias='sortOrder'),
    db: Session = Depends(get_db)
):
    """List all communities"""
    query = db.query(Community)
    
    if state:
        query = query.filter(Community.state == state)

    if city:
        query = query.filter(Community.city == city)

    if search:
        query = query.filter(
            or_(
                Community.name.ilike(f"%{search}%"),
                Community.state.ilike(f"%{search}%"),
                Community.city.ilike(f"%{search}%"),
                Community.zipcode.ilike(f"%{search}%"),
            )
        )

    if pageSize is not None:
        page_size = pageSize
    if limit is not None:
        page_size = limit

    if sort_by == 'safety_score':
        query = query.order_by(Community.safety_score.desc() if sortOrder == 'desc' else Community.safety_score.asc())
    elif sort_by == 'created_at':
        query = query.order_by(Community.created_at.desc() if sortOrder == 'desc' else Community.created_at.asc())
    else:
        query = query.order_by(Community.id.asc())

    total = query.count()
    skip = (page - 1) * page_size
    communities = query.offset(skip).limit(page_size).all()

    payload = []
    for community in communities:
        report_row = db.query(CommunityReport).filter(CommunityReport.community_id == community.id).first()
        if report_row:
            report = {
                "highRiskPeriods": report_row.high_risk_periods,
                "highRiskLocations": report_row.high_risk_locations,
                "safetyTips": report_row.safety_tips,
                "yoyComparison": report_row.yoy_comparison,
            }
        else:
            report = upsert_community_report(db, community.id, commit=True)

        item = {c.name: getattr(community, c.name) for c in community.__table__.columns}
        item["report"] = report
        payload.append(item)

    return {"total": total, "communities": payload}


@router.get("/{community_id}", response_model=CommunityDetailResponse)
async def get_community(
    community_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """Get community details"""
    community = db.query(Community).filter(Community.id == community_id).first()
    
    if not community:
        raise HTTPException(status_code=404, detail="Community not found")
    
    # Get follower count
    followers_count = len(community.followers)
    
    # Check if current user is following
    is_following = bool(current_user and community in current_user.followed_communities)
    report_row = db.query(CommunityReport).filter(CommunityReport.community_id == community.id).first()
    if report_row:
        report = {
            "highRiskPeriods": report_row.high_risk_periods,
            "highRiskLocations": report_row.high_risk_locations,
            "safetyTips": report_row.safety_tips,
            "yoyComparison": report_row.yoy_comparison,
        }
    else:
        report = upsert_community_report(db, community.id, commit=True)
    
    community_data = {
        **{c.name: getattr(community, c.name) for c in community.__table__.columns},
        "events": community.events,
        "report": report,
        "followers_count": followers_count,
        "is_following": is_following,
    }
    
    return community_data


@router.post("/{community_id}/follow")
async def follow_community(
    community_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Follow a community"""
    community = db.query(Community).filter(Community.id == community_id).first()
    
    if not community:
        raise HTTPException(status_code=404, detail="Community not found")
    
    if community not in current_user.followed_communities:
        current_user.followed_communities.append(community)
        db.commit()
    
    return {"message": "Community followed"}


@router.delete("/{community_id}/follow")
async def unfollow_community(
    community_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Unfollow a community"""
    community = db.query(Community).filter(Community.id == community_id).first()
    
    if not community:
        raise HTTPException(status_code=404, detail="Community not found")
    
    if community in current_user.followed_communities:
        current_user.followed_communities.remove(community)
        db.commit()
    
    return {"message": "Community unfollowed"}
