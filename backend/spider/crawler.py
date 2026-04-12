import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

from config import settings
from database import SessionLocal
from models import Community, DangerLevel, Event, EventType
from services.community_intelligence import (
    ensure_core_communities,
    infer_community,
    merge_auto_zone_communities,
    rename_auto_zone_communities,
    upsert_community_report,
)
from services.data_integrity import cleanup_orphan_relations
from services.scoring import recompute_all_community_scores

logger = logging.getLogger(__name__)
SOCRATA_APP_TOKEN = settings.SOCRATA_APP_TOKEN


@dataclass
class PublicSourceConfig:
    name: str
    url: str
    community_name: str
    params: Dict[str, str]
    datetime_field: Optional[str]
    date_field: Optional[str]
    time_field: Optional[str]
    type_fields: List[str]
    description_fields: List[str]
    address_fields: List[str]
    latitude_fields: List[str]
    longitude_fields: List[str]
    id_fields: List[str]


PUBLIC_SOURCES: List[PublicSourceConfig] = [
    PublicSourceConfig(
        name="NYC Open Data (NYPD Complaints)",
        url="https://data.cityofnewyork.us/resource/qgea-i56i.json",
        community_name="New York Manhattan",
        params={
            "$limit": "80",
            "$order": "cmplnt_fr_dt DESC",
            "$where": "latitude IS NOT NULL AND longitude IS NOT NULL",
        },
        datetime_field=None,
        date_field="cmplnt_fr_dt",
        time_field="cmplnt_fr_tm",
        type_fields=["ofns_desc", "pd_desc", "law_cat_cd"],
        description_fields=["pd_desc", "ofns_desc", "law_cat_cd"],
        address_fields=["prem_typ_desc", "boro_nm"],
        latitude_fields=["latitude", "lat"],
        longitude_fields=["longitude", "lon", "lng"],
        id_fields=["cmplnt_num"],
    ),
    PublicSourceConfig(
        name="SF Open Data (Police Incidents)",
        url="https://data.sfgov.org/resource/wg3w-h783.json",
        community_name="San Francisco Bay",
        params={
            "$limit": "80",
            "$order": "incident_datetime DESC",
            "$where": "latitude IS NOT NULL AND longitude IS NOT NULL",
        },
        datetime_field="incident_datetime",
        date_field=None,
        time_field=None,
        type_fields=["incident_category", "incident_subcategory"],
        description_fields=["incident_description", "incident_subcategory", "incident_category"],
        address_fields=["intersection", "analysis_neighborhood"],
        latitude_fields=["latitude"],
        longitude_fields=["longitude"],
        id_fields=["incident_number", "incident_id"],
    ),
    PublicSourceConfig(
        name="Los Angeles Open Data (Crime Data from 2020 to Present)",
        url="https://data.lacity.org/resource/2nrs-mtv8.json",
        community_name="Los Angeles Downtown",
        params={
            "$limit": "80",
            "$order": "date_occ DESC",
            "$where": "lat IS NOT NULL AND lon IS NOT NULL",
        },
        datetime_field=None,
        date_field="date_occ",
        time_field="time_occ",
        type_fields=["crm_cd_desc", "premis_desc"],
        description_fields=["crm_cd_desc", "status_desc", "premis_desc"],
        address_fields=["location", "area_name", "cross_street"],
        latitude_fields=["lat", "latitude"],
        longitude_fields=["lon", "longitude"],
        id_fields=["dr_no"],
    ),
    PublicSourceConfig(
        name="NYC Open Data (NYPD Arrests)",
        url="https://data.cityofnewyork.us/resource/uip8-fykc.json",
        community_name="New York Manhattan",
        params={
            "$limit": "80",
            "$order": "arrest_date DESC",
            "$where": "latitude IS NOT NULL AND longitude IS NOT NULL",
        },
        datetime_field=None,
        date_field="arrest_date",
        time_field=None,
        type_fields=["ofns_desc", "pd_desc", "law_cat_cd"],
        description_fields=["pd_desc", "ofns_desc", "law_cat_cd", "arrest_boro"],
        address_fields=["arrest_boro", "jurisdiction_code"],
        latitude_fields=["latitude"],
        longitude_fields=["longitude"],
        id_fields=["arrest_key"],
    ),
    PublicSourceConfig(
        name="Chicago Data Portal (Crimes)",
        url="https://data.cityofchicago.org/resource/ijzp-q8t2.json",
        community_name="Chicago Downtown",
        params={
            "$limit": "80",
            "$order": "date DESC",
            "$where": "latitude IS NOT NULL AND longitude IS NOT NULL",
        },
        datetime_field="date",
        date_field=None,
        time_field=None,
        type_fields=["primary_type"],
        description_fields=["description", "primary_type", "location_description"],
        address_fields=["block", "location_description", "ward"],
        latitude_fields=["latitude"],
        longitude_fields=["longitude"],
        id_fields=["id", "case_number"],
    ),
]


class PublicDataIngestor:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.db: Optional[Session] = None

    async def start(self):
        headers = {
            "Accept": "application/json",
            "User-Agent": "CommunitySafetyAlert/1.0 (public-data-ingestor)",
        }
        if SOCRATA_APP_TOKEN:
            headers["X-App-Token"] = SOCRATA_APP_TOKEN
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=20),
            headers=headers,
        )
        self.db = SessionLocal()
        ensure_core_communities(self.db, commit=True)

    async def stop(self):
        if self.session:
            await self.session.close()
        if self.db:
            self.db.close()

    @staticmethod
    def _pick_value(row: Dict[str, Any], keys: List[str]) -> Optional[str]:
        for key in keys:
            value = row.get(key)
            if value is None:
                continue
            text = str(value).strip()
            if text:
                return text
        return None

    @staticmethod
    def _parse_datetime(raw: Optional[str]) -> datetime:
        if not raw:
            return datetime.now(timezone.utc)
        text = raw.strip().replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(text)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError:
            pass
        for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%m/%d/%Y %H:%M:%S", "%m/%d/%Y"):
            try:
                dt = datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                continue
        return datetime.now(timezone.utc)

    @staticmethod
    def _combine_date_time(date_part: str, time_part: str) -> str:
        date_text = date_part.strip()
        time_text = time_part.strip()
        if not date_text:
            return ""
        if not time_text:
            return date_text

        if time_text.isdigit() and len(time_text) in (3, 4):
            padded = time_text.zfill(4)
            hh = padded[:2]
            mm = padded[2:]
            return f"{date_text} {hh}:{mm}:00"
        return f"{date_text} {time_text}"

    @staticmethod
    def _safe_float(raw: Optional[str]) -> Optional[float]:
        if raw is None:
            return None
        try:
            return float(raw)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _normalize_event_type(text: str) -> EventType:
        val = text.lower()
        if any(k in val for k in ["flood", "inundation", "water rise", "flash flood"]):
            return EventType.THEFT
        if any(k in val for k in ["earthquake", "seismic", "magnitude", "tremor", "quake"]):
            return EventType.SHOOTING
        if any(k in val for k in ["fire", "wildfire", "red flag", "arson"]):
            return EventType.FIRE
        if any(k in val for k in ["storm", "tornado", "hurricane", "blizzard", "thunderstorm", "hail", "wind"]):
            return EventType.FRAUD
        if any(k in val for k in ["warning", "watch", "advisory", "alert", "security", "disturbance"]):
            return EventType.SECURITY
        return EventType.OTHER

    @staticmethod
    def _normalize_danger_level(type_text: str, details_text: str) -> DangerLevel:
        text = f"{type_text} {details_text}".lower()
        if any(k in text for k in ["homicide", "shoot", "armed", "weapon", "aggravated", "felony"]):
            return DangerLevel.HIGH
        if any(k in text for k in ["robbery", "burglary", "assault", "battery", "arson"]):
            return DangerLevel.MEDIUM
        return DangerLevel.LOW

    async def _fetch_rows(self, source: PublicSourceConfig, limit_per_source: int) -> List[Dict[str, Any]]:
        if not self.session:
            return []
        params = dict(source.params)
        params["$limit"] = str(limit_per_source)
        if SOCRATA_APP_TOKEN:
            params["$$app_token"] = SOCRATA_APP_TOKEN
        try:
            async with self.session.get(source.url, params=params) as resp:
                if resp.status != 200:
                    logger.error("Source %s returned status %s", source.name, resp.status)
                    return []
                payload = await resp.json()
                if isinstance(payload, list):
                    return payload
                return []
        except Exception as exc:
            logger.error("Failed fetching %s: %s", source.name, exc)
            return []

    def _resolve_community(self, community_name: str) -> Optional[Community]:
        if not self.db:
            return None
        community = self.db.query(Community).filter(Community.name == community_name).first()
        if community:
            return community
        return (
            self.db.query(Community)
            .filter(Community.name.ilike(f"%{community_name.split()[0]}%"))
            .order_by(Community.id.asc())
            .first()
        )

    def _all_communities(self) -> List[Community]:
        if not self.db:
            return []
        return self.db.query(Community).order_by(Community.id.asc()).all()

    @staticmethod
    def _distance_sq(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        return (lat1 - lat2) ** 2 + (lng1 - lng2) ** 2

    def _nearest_community(self, lat: float, lng: float, max_distance_sq: float = 36.0) -> Optional[Community]:
        candidates = self._all_communities()
        if not candidates:
            return None

        nearest = None
        nearest_dist = None
        for community in candidates:
            c_lat = getattr(community, "latitude", None)
            c_lng = getattr(community, "longitude", None)
            if c_lat is None or c_lng is None:
                continue
            dist = self._distance_sq(lat, lng, float(c_lat), float(c_lng))
            if nearest is None or dist < nearest_dist:
                nearest = community
                nearest_dist = dist

        if nearest is None:
            return None
        if nearest_dist is not None and nearest_dist > max_distance_sq:
            return None
        return nearest

    def _normalize_row(
        self,
        source: PublicSourceConfig,
        row: Dict[str, Any],
        default_community: Optional[Community],
    ) -> Optional[Dict[str, Any]]:
        type_text = self._pick_value(row, source.type_fields) or "other"
        details_text = self._pick_value(row, source.description_fields) or type_text
        address_text = self._pick_value(row, source.address_fields) or (default_community.city if default_community else "")
        latitude = self._safe_float(self._pick_value(row, source.latitude_fields))
        longitude = self._safe_float(self._pick_value(row, source.longitude_fields))
        if latitude is None or longitude is None:
            return None
        zip_text = (self._pick_value(row, ["zipcode", "zip", "zip_code"]) or "").strip()

        community = infer_community(
            self.db,
            latitude=latitude,
            longitude=longitude,
            address=address_text,
            zipcode=zip_text,
            max_distance_km=180.0,
            allow_dynamic_core=True,
        )
        if not community:
            return None

        if source.datetime_field:
            dt_raw = row.get(source.datetime_field)
            event_time = self._parse_datetime(str(dt_raw) if dt_raw is not None else None)
        else:
            date_part = str(row.get(source.date_field, "")).strip() if source.date_field else ""
            time_part = str(row.get(source.time_field, "")).strip() if source.time_field else ""
            dt_text = self._combine_date_time(date_part, time_part)
            event_time = self._parse_datetime(dt_text)

        record_id = self._pick_value(row, source.id_fields) or f"{community.id}-{abs(hash(str(row))) % 1000000}"
        title = f"{type_text.title()} reported - {community.name}"
        description = f"{details_text}. Source: {source.name}"
        source_url = f"{source.url}?record_id={record_id}"

        event_type = self._normalize_event_type(type_text)
        danger_level = self._normalize_danger_level(type_text, details_text)

        return {
            "title": title[:200],
            "description": description[:1200],
            "event_type": event_type,
            "danger_level": danger_level,
            "community_id": community.id,
            "address": address_text[:255],
            "latitude": latitude,
            "longitude": longitude,
            "zipcode": zip_text or community.zipcode,
            "event_time": event_time,
            "data_source": source.name,
            "source_url": source_url[:500],
        }

    def _save_events(self, events: List[Dict[str, Any]]) -> Tuple[int, int]:
        if not self.db:
            return 0, 0
        inserted = 0
        skipped = 0
        touched_communities = set()

        for payload in events:
            existing = (
                self.db.query(Event)
                .filter(
                    Event.community_id == payload["community_id"],
                    Event.source_url == payload["source_url"],
                )
                .first()
            )
            if existing:
                skipped += 1
                continue

            self.db.add(Event(**payload))
            inserted += 1
            touched_communities.add(payload["community_id"])

        try:
            self.db.commit()
            for community_id in touched_communities:
                upsert_community_report(self.db, community_id, commit=False)
            if touched_communities:
                self.db.commit()
        except Exception as exc:
            logger.error("Commit failed while saving public events: %s", exc)
            self.db.rollback()
            return 0, len(events)

        return inserted, skipped

    async def run_source(self, source: PublicSourceConfig, limit_per_source: int) -> Dict[str, Any]:
        community = self._resolve_community(source.community_name)

        rows = await self._fetch_rows(source, limit_per_source)
        normalized_events: List[Dict[str, Any]] = []
        for row in rows:
            payload = self._normalize_row(source, row, community)
            if payload:
                normalized_events.append(payload)

        inserted, skipped = self._save_events(normalized_events)
        return {
            "source": source.name,
            "community": community.name if community else "auto-inferred",
            "fetched": len(rows),
            "normalized": len(normalized_events),
            "inserted": inserted,
            "skipped": skipped,
        }

    async def _fetch_geojson(self, url: str) -> Dict[str, Any]:
        if not self.session:
            return {}
        try:
            async with self.session.get(url) as resp:
                if resp.status != 200:
                    logger.error("GeoJSON source %s returned status %s", url, resp.status)
                    return {}
                payload = await resp.json()
                if isinstance(payload, dict):
                    return payload
        except Exception as exc:
            logger.error("Failed fetching geojson %s: %s", url, exc)
        return {}

    def _normalize_usgs_features(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        features = payload.get("features") or []
        normalized = []
        for feature in features:
            geometry = feature.get("geometry") or {}
            coords = geometry.get("coordinates") or []
            if len(coords) < 2:
                continue
            lng = self._safe_float(coords[0])
            lat = self._safe_float(coords[1])
            if lat is None or lng is None:
                continue

            community = infer_community(
                self.db,
                latitude=lat,
                longitude=lng,
                address=None,
                zipcode=None,
                max_distance_km=220.0,
                allow_dynamic_core=True,
            )
            if not community:
                continue

            props = feature.get("properties") or {}
            mag = props.get("mag")
            place = props.get("place") or community.name
            title = props.get("title") or f"Earthquake detected near {community.name}"
            details_url = props.get("url") or "https://earthquake.usgs.gov/"
            ts = props.get("time")
            event_time = datetime.now(timezone.utc)
            if ts is not None:
                try:
                    event_time = datetime.fromtimestamp(float(ts) / 1000.0, tz=timezone.utc)
                except Exception:
                    pass

            danger = DangerLevel.LOW
            if mag is not None:
                try:
                    m = float(mag)
                    if m >= 5.0:
                        danger = DangerLevel.HIGH
                    elif m >= 3.5:
                        danger = DangerLevel.MEDIUM
                except Exception:
                    pass

            normalized.append(
                {
                    "title": str(title)[:200],
                    "description": f"USGS seismic event near {place}. Magnitude: {mag}.",
                    "event_type": EventType.SHOOTING,
                    "danger_level": danger,
                    "community_id": community.id,
                    "address": str(place)[:255],
                    "latitude": lat,
                    "longitude": lng,
                    "zipcode": community.zipcode,
                    "event_time": event_time,
                    "data_source": "USGS Earthquake Feed",
                    "source_url": str(details_url)[:500],
                }
            )
        return normalized

    @staticmethod
    def _extract_first_point(geometry: Dict[str, Any]) -> Tuple[Optional[float], Optional[float]]:
        g_type = geometry.get("type")
        coords = geometry.get("coordinates")
        if not coords:
            return None, None
        if g_type == "Point" and isinstance(coords, list) and len(coords) >= 2:
            return coords[1], coords[0]
        if g_type == "Polygon" and isinstance(coords, list) and coords and coords[0]:
            first = coords[0][0]
            if isinstance(first, list) and len(first) >= 2:
                return first[1], first[0]
        if g_type == "MultiPolygon" and isinstance(coords, list) and coords and coords[0] and coords[0][0]:
            first = coords[0][0][0]
            if isinstance(first, list) and len(first) >= 2:
                return first[1], first[0]
        return None, None

    def _normalize_nws_features(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        features = payload.get("features") or []
        normalized = []
        for feature in features:
            props = feature.get("properties") or {}
            geometry = feature.get("geometry") or {}
            lat, lng = self._extract_first_point(geometry)
            if lat is None or lng is None:
                continue

            community = infer_community(
                self.db,
                latitude=float(lat),
                longitude=float(lng),
                address=None,
                zipcode=None,
                max_distance_km=220.0,
                allow_dynamic_core=True,
            )
            if not community:
                continue

            event_name = str(props.get("event") or "Weather Alert")
            severity_text = str(props.get("severity") or "").lower()
            if "extreme" in severity_text or "severe" in severity_text:
                danger = DangerLevel.HIGH
            elif "moderate" in severity_text:
                danger = DangerLevel.MEDIUM
            else:
                danger = DangerLevel.LOW

            lower_name = event_name.lower()
            if any(k in lower_name for k in ["flood", "inundation", "flash flood"]):
                event_type = EventType.THEFT
            elif any(k in lower_name for k in ["fire", "red flag"]):
                event_type = EventType.FIRE
            elif any(k in lower_name for k in ["storm", "tornado", "hurricane", "blizzard", "thunderstorm", "hail", "wind"]):
                event_type = EventType.FRAUD
            else:
                event_type = EventType.SECURITY

            headline = props.get("headline") or event_name
            desc = props.get("description") or props.get("instruction") or "NWS public safety alert."
            source_url = props.get("@id") or props.get("id") or "https://api.weather.gov/alerts/active"
            sent = props.get("sent") or props.get("effective")
            event_time = self._parse_datetime(str(sent) if sent else None)
            area = props.get("areaDesc") or community.name

            normalized.append(
                {
                    "title": f"{event_name} - {community.name}"[:200],
                    "description": f"{headline}. {str(desc)[:900]}",
                    "event_type": event_type,
                    "danger_level": danger,
                    "community_id": community.id,
                    "address": str(area)[:255],
                    "latitude": float(lat),
                    "longitude": float(lng),
                    "zipcode": community.zipcode,
                    "event_time": event_time,
                    "data_source": "NWS Alerts API",
                    "source_url": str(source_url)[:500],
                }
            )
        return normalized

    async def run_live_feeds(self) -> List[Dict[str, Any]]:
        results = []

        usgs_payload = await self._fetch_geojson(
            "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson"
        )
        usgs_events = self._normalize_usgs_features(usgs_payload) if usgs_payload else []
        usgs_inserted, usgs_skipped = self._save_events(usgs_events)
        results.append(
            {
                "source": "USGS Earthquake Feed",
                "fetched": len(usgs_payload.get("features") or []) if usgs_payload else 0,
                "normalized": len(usgs_events),
                "inserted": usgs_inserted,
                "skipped": usgs_skipped,
            }
        )

        nws_payload = await self._fetch_geojson(
            "https://api.weather.gov/alerts/active?status=actual&message_type=alert"
        )
        nws_events = self._normalize_nws_features(nws_payload) if nws_payload else []
        nws_inserted, nws_skipped = self._save_events(nws_events)
        results.append(
            {
                "source": "NWS Alerts API",
                "fetched": len(nws_payload.get("features") or []) if nws_payload else 0,
                "normalized": len(nws_events),
                "inserted": nws_inserted,
                "skipped": nws_skipped,
            }
        )

        return results

    async def run_all(self, limit_per_source: int = 80) -> Dict[str, Any]:
        results = []
        for source in PUBLIC_SOURCES:
            result = await self.run_source(source, limit_per_source=limit_per_source)
            results.append(result)
            await asyncio.sleep(0.2)

        live_results = await self.run_live_feeds()
        results.extend(live_results)

        total_inserted = sum(item.get("inserted", 0) for item in results)
        total_skipped = sum(item.get("skipped", 0) for item in results)
        total_fetched = sum(item.get("fetched", 0) for item in results)
        return {
            "sources": results,
            "total_fetched": total_fetched,
            "total_inserted": total_inserted,
            "total_skipped": total_skipped,
        }


class SpiderScheduler:
    def __init__(self):
        self.running = False
        self.last_run: Optional[datetime] = None
        self.last_error: Optional[str] = None
        self.success_count = 0
        self.failure_count = 0
        self.last_summary: Dict[str, Any] = {}
        self.score_scheduler = BackgroundScheduler(timezone="UTC")

    async def run_once(self, limit_per_source: int = 80) -> Dict[str, Any]:
        if self.running:
            return {"message": "Spider is already running", "running": True}

        self.running = True
        self.last_run = datetime.now(timezone.utc)
        self.last_error = None
        ingestor = PublicDataIngestor()

        try:
            await ingestor.start()
            summary = await ingestor.run_all(limit_per_source=limit_per_source)
            if ingestor.db:
                merge_summary = merge_auto_zone_communities(ingestor.db, distance_km=120.0, commit=True)
                summary["auto_core_merge"] = merge_summary
                rename_summary = rename_auto_zone_communities(ingestor.db, commit=True)
                summary["auto_core_rename"] = rename_summary
                score_summary = recompute_all_community_scores(ingestor.db, commit=True)
                summary["score_recompute"] = score_summary
            self.success_count += summary.get("total_inserted", 0)
            self.last_summary = summary
            return {"running": False, **summary}
        except Exception as exc:
            self.failure_count += 1
            self.last_error = str(exc)
            logger.exception("Spider run failed: %s", exc)
            return {"running": False, "error": self.last_error}
        finally:
            await ingestor.stop()
            self.running = False


scheduler = SpiderScheduler()


def recalculate_scores_once() -> Dict[str, Any]:
    db = SessionLocal()
    try:
        return recompute_all_community_scores(db, commit=True)
    finally:
        db.close()


def cleanup_orphans_once() -> Dict[str, Any]:
    db = SessionLocal()
    try:
        return cleanup_orphan_relations(db, commit=True)
    finally:
        db.close()


def _periodic_score_job():
    try:
        summary = recalculate_scores_once()
        logger.info("Periodic community score recompute complete: updated=%s", summary.get("updated"))
    except Exception as exc:
        logger.exception("Periodic community score recompute failed: %s", exc)


def _periodic_integrity_job():
    try:
        summary = cleanup_orphans_once()
        logger.info("Periodic orphan cleanup complete: removed=%s", summary.get("total_removed"))
    except Exception as exc:
        logger.exception("Periodic orphan cleanup failed: %s", exc)


def init_scheduler():
    """Initialize scheduler and periodic score recalculation."""
    logger.info("Public data spider scheduler initialized with %d sources", len(PUBLIC_SOURCES))
    recalculate_scores_once()
    cleanup_summary = cleanup_orphans_once()
    logger.info("Startup orphan cleanup complete: removed=%s", cleanup_summary.get("total_removed"))

    if not settings.SPIDER_ENABLED:
        logger.info("SPIDER_ENABLED is false; periodic score recalculation is disabled.")
        return

    if not scheduler.score_scheduler.running:
        interval_seconds = max(int(settings.SPIDER_INTERVAL), 300)
        scheduler.score_scheduler.add_job(
            _periodic_score_job,
            trigger="interval",
            seconds=interval_seconds,
            id="community-score-recompute",
            replace_existing=True,
            coalesce=True,
            max_instances=1,
        )
        scheduler.score_scheduler.add_job(
            _periodic_integrity_job,
            trigger="interval",
            seconds=interval_seconds,
            id="orphan-cleanup",
            replace_existing=True,
            coalesce=True,
            max_instances=1,
        )
        scheduler.score_scheduler.start()
        logger.info("Periodic score recompute and orphan cleanup scheduled every %s seconds", interval_seconds)


def shutdown_scheduler():
    if scheduler.score_scheduler.running:
        scheduler.score_scheduler.shutdown(wait=False)
        logger.info("Score scheduler shutdown complete")
