from datetime import datetime, timedelta, timezone
from typing import Dict, List

from sqlalchemy.orm import Session

from models import Community, DangerLevel, Event, EventType, SafetyLevel


DANGER_WEIGHT = {
    DangerLevel.LOW: 1.0,
    DangerLevel.MEDIUM: 1.8,
    DangerLevel.HIGH: 2.8,
}

TYPE_WEIGHT = {
    EventType.THEFT: 1.6,  # Flood
    EventType.SHOOTING: 1.8,  # Earthquake
    EventType.FIRE: 1.7,  # Fire risk
    EventType.FRAUD: 1.5,  # Severe storm
    EventType.SECURITY: 1.2,  # General alert
    EventType.OTHER: 1.0,
}


def _to_utc(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _event_weight(event: Event, now_utc: datetime) -> float:
    event_time = _to_utc(event.event_time) or now_utc
    age_days = (now_utc - event_time).days

    # Future or imminent alerts should be treated as higher short-term risk.
    if age_days < 0:
        recency_weight = 2.2
    elif age_days <= 1:
        recency_weight = 1.9
    elif age_days <= 7:
        recency_weight = 1.6
    elif age_days <= 30:
        recency_weight = 1.2
    elif age_days <= 90:
        recency_weight = 0.8
    else:
        recency_weight = 0.4

    danger_weight = DANGER_WEIGHT.get(event.danger_level, 1.0)
    type_weight = TYPE_WEIGHT.get(event.event_type, 1.0)
    return danger_weight * type_weight * recency_weight


def _safety_level(score: float) -> SafetyLevel:
    # Higher score means safer community.
    if score >= 80:
        return SafetyLevel.HIGH
    if score >= 60:
        return SafetyLevel.MEDIUM
    return SafetyLevel.LOW


def _trend(events: List[Event], now_utc: datetime) -> str:
    recent_start = now_utc - timedelta(days=30)
    prev_start = now_utc - timedelta(days=60)

    recent_count = 0
    prev_count = 0
    for event in events:
        event_time = _to_utc(event.event_time)
        if not event_time:
            continue
        if event_time >= recent_start:
            recent_count += 1
        elif prev_start <= event_time < recent_start:
            prev_count += 1

    if prev_count == 0:
        return "stable"

    ratio = recent_count / prev_count
    if ratio <= 0.9:
        return "up"   # safer
    if ratio >= 1.1:
        return "down"  # less safe
    return "stable"


def recompute_all_community_scores(db: Session, commit: bool = True) -> Dict:
    communities = db.query(Community).all()
    now_utc = datetime.now(timezone.utc)
    updated = 0
    details = []

    for community in communities:
        events = db.query(Event).filter(Event.community_id == community.id).all()
        weighted_sum = sum(_event_weight(event, now_utc) for event in events)
        high_count = sum(1 for event in events if event.danger_level == DangerLevel.HIGH)
        medium_count = sum(1 for event in events if event.danger_level == DangerLevel.MEDIUM)
        future_count = sum(
            1
            for event in events
            if (_to_utc(event.event_time) or now_utc) > now_utc
        )
        recent_7_count = sum(
            1
            for event in events
            if (now_utc - (_to_utc(event.event_time) or now_utc)).days <= 7
        )

        population = community.population or 250000
        exposure = max(1.0, population / 100000.0)
        risk_index = weighted_sum / exposure

        if not events:
            # No incident evidence in window -> relatively safe baseline.
            score = 92.0
        else:
            # Convert risk index to safety score (inverse relation):
            # higher risk => lower score, lower risk => higher score.
            risk_penalty = min(72.0, risk_index * 3.6)
            structural_penalty = min(
                40.0,
                high_count * 6.0 + medium_count * 2.5 + future_count * 4.0 + recent_7_count * 0.8,
            )
            score = 100.0 - min(95.0, risk_penalty + structural_penalty)
            score = max(5.0, min(99.0, score))

        level = _safety_level(score)
        trend = _trend(events, now_utc)

        community.safety_score = round(score, 1)
        community.safety_level = level
        community.trend = trend
        updated += 1
        details.append(
            {
                "community_id": community.id,
                "community_name": community.name,
                "safety_score": community.safety_score,
                "safety_level": community.safety_level.value,
                "trend": community.trend,
                "event_count": len(events),
            }
        )

    if commit:
        db.commit()

    return {"updated": updated, "communities": details}
