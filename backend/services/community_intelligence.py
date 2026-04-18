from __future__ import annotations

from datetime import datetime, timezone
from math import cos, pi, sqrt
import re
from typing import Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from models import Community, CommunityReport, DangerLevel, Event


CORE_COMMUNITIES = [
    {
        "name": "Los Angeles Downtown",
        "state": "CA",
        "city": "Los Angeles",
        "zipcode": "90001",
        "latitude": 34.0522,
        "longitude": -118.2437,
        "population": 500000,
        "area": 50.0,
    },
    {
        "name": "San Francisco Bay",
        "state": "CA",
        "city": "San Francisco",
        "zipcode": "94102",
        "latitude": 37.7749,
        "longitude": -122.4194,
        "population": 300000,
        "area": 30.0,
    },
    {
        "name": "New York Manhattan",
        "state": "NY",
        "city": "New York",
        "zipcode": "10001",
        "latitude": 40.7128,
        "longitude": -74.0060,
        "population": 1000000,
        "area": 60.0,
    },
    {
        "name": "Chicago Downtown",
        "state": "IL",
        "city": "Chicago",
        "zipcode": "60601",
        "latitude": 41.8781,
        "longitude": -87.6298,
        "population": 400000,
        "area": 45.0,
    },
]

US_REGION_BOUNDS = [
    # Continental US
    {"lat_min": 24.0, "lat_max": 49.8, "lng_min": -125.0, "lng_max": -66.5},
    # Alaska
    {"lat_min": 51.0, "lat_max": 72.0, "lng_min": -170.0, "lng_max": -129.0},
    # Hawaii
    {"lat_min": 18.5, "lat_max": 22.6, "lng_min": -160.6, "lng_max": -154.5},
    # Puerto Rico
    {"lat_min": 17.7, "lat_max": 18.7, "lng_min": -67.4, "lng_max": -65.1},
]

US_STATE_CODES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC", "PR",
}

PLACE_STOPWORDS = {
    "unknown", "area", "block", "street", "st", "road", "rd", "avenue", "ave",
    "highway", "hwy", "intersection", "district", "ward", "zone", "core",
    "north", "south", "east", "west", "county", "city", "state",
}

DIRECTION_CODES = {
    "N", "S", "E", "W", "NE", "NW", "SE", "SW",
    "NNE", "NNW", "ENE", "ESE", "SSE", "SSW", "WNW", "WSW",
}

US_STATE_NAME_TO_CODE = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR", "california": "CA",
    "colorado": "CO", "connecticut": "CT", "delaware": "DE", "florida": "FL", "georgia": "GA",
    "hawaii": "HI", "idaho": "ID", "illinois": "IL", "indiana": "IN", "iowa": "IA",
    "kansas": "KS", "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN", "mississippi": "MS", "missouri": "MO",
    "montana": "MT", "nebraska": "NE", "nevada": "NV", "new hampshire": "NH", "new jersey": "NJ",
    "new mexico": "NM", "new york": "NY", "north carolina": "NC", "north dakota": "ND", "ohio": "OH",
    "oklahoma": "OK", "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC",
    "south dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT", "vermont": "VT",
    "virginia": "VA", "washington": "WA", "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY",
    "district of columbia": "DC", "puerto rico": "PR",
}


def ensure_core_communities(db: Session, commit: bool = True) -> Dict:
    existing = {item.name for item in db.query(Community).all()}
    created = 0
    for item in CORE_COMMUNITIES:
        if item["name"] in existing:
            continue
        db.add(Community(**item))
        created += 1
    if commit and created:
        db.commit()
    return {"created": created, "total": db.query(Community).count()}


def _distance_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    # Fast local approximation for intra-country ranking.
    dy = (lat1 - lat2) * 111.0
    avg_lat = (lat1 + lat2) / 2
    dx = (lng1 - lng2) * max(cos(avg_lat * pi / 180.0), 0.2) * 111.0
    return sqrt(dx * dx + dy * dy)


def is_us_coordinate(latitude: Optional[float], longitude: Optional[float]) -> bool:
    if latitude is None or longitude is None:
        return False
    lat = float(latitude)
    lng = float(longitude)
    for box in US_REGION_BOUNDS:
        if box["lat_min"] <= lat <= box["lat_max"] and box["lng_min"] <= lng <= box["lng_max"]:
            return True
    return False


def infer_community(
    db: Session,
    latitude: Optional[float],
    longitude: Optional[float],
    address: Optional[str] = None,
    zipcode: Optional[str] = None,
    max_distance_km: float = 180.0,
    allow_dynamic_core: bool = False,
    enforce_existing: bool = True,
) -> Optional[Community]:
    communities = db.query(Community).all()
    if not communities:
        ensure_core_communities(db, commit=True)
        communities = db.query(Community).all()
    if not communities:
        return None

    text = (address or "").lower()
    zip_text = (zipcode or "").strip()

    if latitude is not None and longitude is not None and not is_us_coordinate(latitude, longitude):
        return None

    best = None
    best_score = 10**9
    best_raw_distance = 10**9
    for community in communities:
        score = 1000.0
        raw_distance = 10**9
        if latitude is not None and longitude is not None and community.latitude is not None and community.longitude is not None:
            raw_distance = _distance_km(float(latitude), float(longitude), float(community.latitude), float(community.longitude))
            score = raw_distance

        if zip_text and community.zipcode and str(community.zipcode).strip() == zip_text:
            score -= 60.0

        city_hit = community.city and community.city.lower() in text
        state_hit = community.state and community.state.lower() in text
        name_hit = community.name and community.name.lower() in text
        if city_hit:
            score -= 20.0
        if state_hit:
            score -= 8.0
        if name_hit:
            score -= 12.0

        if score < best_score:
            best = community
            best_score = score
            best_raw_distance = raw_distance

    if latitude is not None and longitude is not None and best_raw_distance > max_distance_km:
        if allow_dynamic_core and not enforce_existing:
            return get_or_create_dynamic_core_community(
                db,
                latitude=float(latitude),
                longitude=float(longitude),
                address=address,
                zipcode=zipcode,
            )
        # Enforce assigning events only to existing communities.
        return best if enforce_existing else None

    return best


def build_community_report(events: List[Event]) -> Dict[str, str]:
    if not events:
        return {
            "highRiskPeriods": "No recent event time pattern available",
            "highRiskLocations": "No event hotspot location available",
            "safetyTips": "Keep monitoring official alerts and maintain emergency contacts.",
            "yoyComparison": "Insufficient data for trend comparison",
        }

    address_counter: Dict[str, int] = {}
    hour_counter: Dict[str, int] = {}
    now = datetime.now(timezone.utc)
    recent_30 = 0
    previous_30 = 0
    high_risk = 0

    for event in events:
        addr = (event.address or "").strip()
        if addr:
            address_counter[addr] = address_counter.get(addr, 0) + 1
        if event.danger_level == DangerLevel.HIGH:
            high_risk += 1

        if event.event_time:
            dt = event.event_time
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            hour_key = f"{dt.hour:02d}:00-{(dt.hour + 1) % 24:02d}:00"
            hour_counter[hour_key] = hour_counter.get(hour_key, 0) + 1

            age_days = (now - dt).days
            if 0 <= age_days < 30:
                recent_30 += 1
            elif 30 <= age_days < 60:
                previous_30 += 1

    top_locations = sorted(address_counter.items(), key=lambda x: x[1], reverse=True)[:3]
    top_periods = sorted(hour_counter.items(), key=lambda x: x[1], reverse=True)[:2]

    high_ratio = high_risk / max(len(events), 1)
    if high_ratio >= 0.35:
        tips = "High-severity incidents are relatively frequent. Avoid hotspot blocks at peak hours and follow alerts."
    elif high_ratio >= 0.15:
        tips = "Medium-to-high severity incidents exist. Keep routine precautions and check local warning updates."
    else:
        tips = "Current severity is mostly low/medium. Keep basic awareness and monitor local notifications."

    if previous_30 == 0:
        trend_text = f"Last 30 days: {recent_30} events (no baseline in previous 30 days)"
    else:
        change_pct = ((recent_30 - previous_30) / previous_30) * 100
        trend_text = f"Last 30 days: {recent_30} vs previous 30 days: {previous_30} ({change_pct:+.1f}%)"

    return {
        "highRiskPeriods": ", ".join([period for period, _ in top_periods]) if top_periods else "No clear peak period",
        "highRiskLocations": "; ".join([loc for loc, _ in top_locations]) if top_locations else "No clear hotspot",
        "safetyTips": tips,
        "yoyComparison": trend_text,
    }


def upsert_community_report(db: Session, community_id: int, commit: bool = True) -> Dict[str, str]:
    events = db.query(Event).filter(Event.community_id == community_id).all()
    report = build_community_report(events)
    item = db.query(CommunityReport).filter(CommunityReport.community_id == community_id).first()
    if not item:
        item = CommunityReport(community_id=community_id)
        db.add(item)
    item.high_risk_periods = report["highRiskPeriods"]
    item.high_risk_locations = report["highRiskLocations"]
    item.safety_tips = report["safetyTips"]
    item.yoy_comparison = report["yoyComparison"]
    if commit:
        db.commit()
    return report


def cleanup_events_outside_core_scope(db: Session, max_distance_km: float = 180.0, commit: bool = True) -> Dict[str, int]:
    events = db.query(Event).all()
    removed = 0
    scanned = 0
    for event in events:
        scanned += 1
        inferred = infer_community(
            db,
            latitude=event.latitude,
            longitude=event.longitude,
            address=event.address,
            zipcode=event.zipcode,
            max_distance_km=max_distance_km,
        )
        if not inferred:
            db.delete(event)
            removed += 1
            continue
        if event.community_id != inferred.id:
            event.community_id = inferred.id

    if commit:
        db.commit()
    return {"scanned": scanned, "removed": removed}


def _extract_city_state(address: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    text = (address or "").strip()
    if not text:
        return None, None

    parts = [p.strip() for p in text.split(",") if p.strip()]
    city = parts[-2] if len(parts) >= 2 else None
    state = None
    if parts:
        # Try "CA 94102" or "California 94102"
        m = re.search(r"\b([A-Z]{2})\b", parts[-1].upper())
        if m:
            state = m.group(1)
        elif len(parts) >= 2:
            m2 = re.search(r"\b([A-Z]{2})\b", parts[-2].upper())
            if m2:
                state = m2.group(1)
    return city, state


def _normalize_zip(zipcode: Optional[str]) -> Optional[str]:
    if not zipcode:
        return None
    digits = re.sub(r"[^0-9]", "", str(zipcode))
    return digits[:5] if len(digits) >= 5 else None


def _unique_community_name(db: Session, base: str, exclude_id: Optional[int] = None) -> str:
    name = base[:80]
    existing = db.query(Community).filter(Community.name == name).first()
    if not existing or (exclude_id is not None and existing.id == exclude_id):
        return name
    idx = 2
    while True:
        candidate = f"{base[:70]} #{idx}"
        existing_candidate = db.query(Community).filter(Community.name == candidate).first()
        if not existing_candidate or (exclude_id is not None and existing_candidate.id == exclude_id):
            return candidate
        idx += 1


def get_or_create_dynamic_core_community(
    db: Session,
    latitude: float,
    longitude: float,
    address: Optional[str],
    zipcode: Optional[str],
) -> Optional[Community]:
    if not is_us_coordinate(latitude, longitude):
        return None

    zip5 = _normalize_zip(zipcode)
    city, state = _extract_city_state(address)

    if zip5:
        existing_by_zip = db.query(Community).filter(Community.zipcode == zip5).first()
        if existing_by_zip:
            return existing_by_zip

    if city:
        existing_by_city = (
            db.query(Community)
            .filter(Community.city.ilike(city))
            .order_by(Community.id.asc())
            .first()
        )
        if existing_by_city:
            return existing_by_city

    # Reuse nearby auto core to avoid fragmentation.
    nearby_auto = []
    for c in db.query(Community).filter(Community.name.ilike("Auto Zone Core%")).all():
        if c.latitude is None or c.longitude is None:
            continue
        d = _distance_km(latitude, longitude, float(c.latitude), float(c.longitude))
        if d <= 140.0:
            nearby_auto.append((d, c))
    if nearby_auto:
        nearby_auto.sort(key=lambda x: x[0])
        return nearby_auto[0][1]

    state_final = state or "US"
    city_final = city or "Auto Zone"

    # Reuse deterministic geo-bucket auto community (prevents creating many sparse zones).
    if not city and not zip5:
        lat_bucket = _geo_bucket(latitude, 2.0)
        lng_bucket = _geo_bucket(longitude, 2.0)
        bucket_name = f"Auto Zone Core [{lat_bucket:.1f},{lng_bucket:.1f}]"
        bucket_existing = db.query(Community).filter(Community.name == bucket_name).first()
        if bucket_existing:
            return bucket_existing
        name_base = bucket_name
    else:
        name_base = f"{city_final} Core {zip5}" if zip5 else f"{city_final} Core"

    name = _unique_community_name(db, name_base)

    community = Community(
        name=name,
        state=state_final,
        city=city_final,
        zipcode=zip5,
        latitude=float(latitude),
        longitude=float(longitude),
        area=25.0,
        population=200000,
        trend="stable",
    )
    db.add(community)
    db.commit()
    db.refresh(community)
    return community


def merge_auto_zone_communities(db: Session, distance_km: float = 120.0, commit: bool = True) -> Dict[str, int]:
    autos = db.query(Community).filter(Community.name.ilike("Auto Zone Core%")).order_by(Community.id.asc()).all()
    if len(autos) <= 1:
        return {"clusters": len(autos), "merged_communities": 0, "reassigned_events": 0}

    centroids = {}
    event_counts = {}
    for c in autos:
        events = db.query(Event).filter(Event.community_id == c.id).all()
        event_counts[c.id] = len(events)
        if events:
            lat = sum(float(e.latitude) for e in events if e.latitude is not None) / max(
                1, len([e for e in events if e.latitude is not None])
            )
            lng = sum(float(e.longitude) for e in events if e.longitude is not None) / max(
                1, len([e for e in events if e.longitude is not None])
            )
            centroids[c.id] = (lat, lng)
        else:
            centroids[c.id] = (float(c.latitude or 0.0), float(c.longitude or 0.0))

    parent = {c.id: c.id for c in autos}

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    auto_ids = [c.id for c in autos]
    for i, a in enumerate(auto_ids):
        for b in auto_ids[i + 1 :]:
            lat1, lng1 = centroids[a]
            lat2, lng2 = centroids[b]
            if _distance_km(lat1, lng1, lat2, lng2) <= distance_km:
                union(a, b)

    clusters = {}
    for cid in auto_ids:
        root = find(cid)
        clusters.setdefault(root, []).append(cid)

    merged_communities = 0
    reassigned_events = 0

    for _, members in clusters.items():
        if len(members) <= 1:
            continue
        # Choose representative: highest event count, then smaller id.
        members_sorted = sorted(members, key=lambda x: (-event_counts.get(x, 0), x))
        rep = members_sorted[0]
        to_merge = members_sorted[1:]

        for old in to_merge:
            reassigned_events += (
                db.query(Event)
                .filter(Event.community_id == old)
                .update({Event.community_id: rep}, synchronize_session=False)
            )
            # Move follows to rep, then cleanup duplicate follows.
            db.execute(
                text(
                    """
                    INSERT INTO user_community_follows (user_id, community_id)
                    SELECT user_id, :rep
                    FROM user_community_follows
                    WHERE community_id = :old
                    ON CONFLICT DO NOTHING
                    """
                ),
                {"rep": rep, "old": old},
            )
            db.execute(text("DELETE FROM user_community_follows WHERE community_id = :old"), {"old": old})
            db.execute(text("DELETE FROM community_reports WHERE community_id = :old"), {"old": old})
            db.query(Community).filter(Community.id == old).delete(synchronize_session=False)
            merged_communities += 1

        upsert_community_report(db, rep, commit=False)

    if commit:
        db.commit()
    return {
        "clusters": len(clusters),
        "merged_communities": merged_communities,
        "reassigned_events": reassigned_events,
    }


def _geo_bucket(value: float, step: float = 2.0) -> float:
    return round(value / step) * step


def _normalize_place_token(value: str) -> str:
    token = re.sub(r"\s+", " ", (value or "").strip())
    token = re.sub(r"[^\w\s\-]", "", token)
    if not token:
        return ""
    words = [w for w in token.split(" ") if w]
    if not words:
        return ""
    return " ".join(w.capitalize() for w in words)[:80]


def _is_valid_place_token(token: str) -> bool:
    if not token:
        return False
    lowered = token.lower()
    if lowered in PLACE_STOPWORDS:
        return False
    if len(token) < 3:
        return False
    if re.search(r"\d", token) and not re.search(r"[A-Za-z]{3,}", token):
        return False
    if token.upper() in US_STATE_CODES:
        return False
    return True


def _extract_place_candidates_from_address(address: Optional[str]) -> List[str]:
    text = (address or "").strip()
    if not text:
        return []

    candidates: List[str] = []
    parts = [p.strip() for p in text.split(",") if p.strip()]
    for part in parts:
        # e.g. "22 km WNW of Volcano" -> "Volcano"
        part = re.sub(r"^\s*\d+(?:\.\d+)?\s*km\s+[A-Z]{1,4}\s+of\s+", "", part, flags=re.IGNORECASE).strip()
        # Remove trailing zip and isolated state code for cleaner place label candidates.
        cleaned = re.sub(r"\b\d{5}(?:-\d{4})?\b", "", part).strip()
        cleaned = re.sub(r"\b(" + "|".join(sorted(US_STATE_CODES)) + r")\b$", "", cleaned, flags=re.IGNORECASE).strip()
        token = _normalize_place_token(cleaned)
        if _is_valid_place_token(token):
            candidates.append(token)

    # Pattern fallback: "near X", "in X", "at X".
    for m in re.finditer(r"\b(?:near|in|at|around)\s+([A-Za-z][A-Za-z\-\s]{2,60})", text, flags=re.IGNORECASE):
        token = _normalize_place_token(m.group(1))
        if _is_valid_place_token(token):
            candidates.append(token)

    return candidates


def _extract_state_from_address(address: Optional[str]) -> Optional[str]:
    text = (address or "").strip()
    if not text:
        return None

    _, state_from_city = _extract_city_state(text)
    if state_from_city and state_from_city in US_STATE_CODES:
        return state_from_city

    upper_text = text.upper()
    # Prefer explicit ", CA" or ", CA 94102" patterns.
    m = re.search(r",\s*([A-Z]{2})(?:\s+\d{5}(?:-\d{4})?)?\s*$", upper_text)
    if m:
        code = m.group(1)
        if code in US_STATE_CODES and code not in DIRECTION_CODES:
            return code

    lowered = text.lower()
    for state_name, code in sorted(US_STATE_NAME_TO_CODE.items(), key=lambda x: -len(x[0])):
        if re.search(rf"\b{re.escape(state_name)}\b", lowered):
            return code

    return None


def rename_auto_zone_communities(db: Session, commit: bool = True) -> Dict[str, int]:
    core_names = {item["name"] for item in CORE_COMMUNITIES}
    candidates = (
        db.query(Community)
        .filter(Community.name.ilike("%Core%"))
        .order_by(Community.id.asc())
        .all()
    )
    autos = [c for c in candidates if c.name not in core_names]
    if not autos:
        return {"checked": 0, "renamed": 0}

    renamed = 0
    for community in autos:
        events = db.query(Event).filter(Event.community_id == community.id).all()
        if not events:
            continue

        place_counter: Dict[str, int] = {}
        state_counter: Dict[str, int] = {}
        for event in events:
            for token in _extract_place_candidates_from_address(event.address):
                place_counter[token] = place_counter.get(token, 0) + 1
            state = _extract_state_from_address(event.address)
            if state:
                state_counter[state] = state_counter.get(state, 0) + 1

        if not place_counter:
            continue

        # Prefer most frequent non-generic location token from event addresses.
        top_place = sorted(place_counter.items(), key=lambda x: (-x[1], len(x[0]), x[0]))[0][0]
        top_state = None
        if state_counter:
            top_state = sorted(state_counter.items(), key=lambda x: (-x[1], x[0]))[0][0]

        existing_state = (community.state or "").upper().strip()
        preferred_state = None
        if existing_state and existing_state in US_STATE_CODES and existing_state not in DIRECTION_CODES and existing_state != "US":
            preferred_state = existing_state
        elif top_state:
            preferred_state = top_state

        if preferred_state and preferred_state not in top_place.upper().split():
            target_base = f"{top_place} {preferred_state} Core"
        else:
            target_base = f"{top_place} Core"

        # Avoid collisions while preserving readable real-place naming.
        target_name = _unique_community_name(db, target_base, exclude_id=community.id)
        if community.name == target_name:
            continue

        community.name = target_name
        community.city = top_place[:80]
        if preferred_state and (community.state in ("US", "", None) or existing_state in DIRECTION_CODES):
            community.state = preferred_state
        renamed += 1

    if commit and renamed:
        db.commit()
    return {"checked": len(autos), "renamed": renamed}
