import asyncio
import logging
import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

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
    latitude_fields: List[str]       #经度
    longitude_fields: List[str]      #纬度
    id_fields: List[str]


PUBLIC_SOURCES: List[PublicSourceConfig] = [
    PublicSourceConfig(
        name="NYC Open Data (NYPD Complaints)",                         #纽约警方案件投诉数据
        url="https://data.cityofnewyork.us/resource/qgea-i56i.json",
        community_name="New York Manhattan",
        params={
            "$limit": "80",                                             #拉取数据条数
            "$order": "cmplnt_fr_dt DESC",                              #投诉日期倒序排序
            "$where": "latitude IS NOT NULL AND longitude IS NOT NULL", #只获取有经纬度的数据
        },
        datetime_field=None,
        date_field="cmplnt_fr_dt",
        time_field="cmplnt_fr_tm",
        type_fields=["ofns_desc", "pd_desc", "law_cat_cd"],             #事件类型字段优先从这几个字段中获取
        description_fields=["pd_desc", "ofns_desc", "law_cat_cd"],
        address_fields=["prem_typ_desc", "boro_nm"],                    #地址字段优先从这几个字段中获取         
        latitude_fields=["latitude", "lat"],
        longitude_fields=["longitude", "lon", "lng"],
        id_fields=["cmplnt_num"],
    ),
    PublicSourceConfig(
        name="SF Open Data (Police Incidents)",                         #旧金山警情数据
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
        name="Los Angeles Open Data (Crime Data from 2020 to Present)", #洛杉矶犯罪数据
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
        name="NYC Open Data (NYPD Arrests)",                        #纽约警方案件逮捕数据
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
        name="Chicago Data Portal (Crimes)",                    #芝加哥犯罪数据
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
    PublicSourceConfig(
        name="Seattle Open Data (Real-Time 911 Calls)",       #西雅图911警情数据
        url="https://data.seattle.gov/resource/kzjm-xkqj.json",
        community_name="Seattle",
        params={
            "$limit": "80",
            "$order": "datetime DESC",
            "$where": "latitude IS NOT NULL AND longitude IS NOT NULL",
        },
        datetime_field="datetime",
        date_field=None,
        time_field=None,
        type_fields=["event_clearance_description", "initial_type_group", "initial_type_description"],
        description_fields=["initial_type_description", "event_clearance_description", "type"],
        address_fields=["hundred_block_location", "zip_code"],
        latitude_fields=["latitude"],
        longitude_fields=["longitude"],
        id_fields=["cad_event_number", "id"],
    ),
    PublicSourceConfig(
        name="Austin Open Data (Crime Reports)",            #奥斯汀犯罪报告数据
        url="https://data.austintexas.gov/resource/fdj4-gpfu.json",
        community_name="Austin",
        params={
            "$limit": "80",
            "$order": "occ_date_time DESC",
            "$where": "latitude IS NOT NULL AND longitude IS NOT NULL",
        },
        datetime_field="occ_date_time",
        date_field=None,
        time_field=None,
        type_fields=["highest_offense_description", "ucr_category"],
        description_fields=["highest_offense_description", "offense_location_description", "ucr_category"],
        address_fields=["address", "zip_code"],
        latitude_fields=["latitude"],
        longitude_fields=["longitude"],
        id_fields=["incident_report_number", "go_primary_key"],
    ),
]

# 公共数据采集模块的核心
'''
    创建 HTTP 请求会话；
    请求各个公开数据源；
    对原始数据进行字段提取和格式标准化；
    判断事件类型和危险等级；
    识别事件所属社区；
    保存事件到数据库；
    处理地震、天气、火灾、自然灾害等实时数据源
'''
class PublicDataIngestor:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None   #异步HTTP请求会话
        self.db: Optional[Session] = None                      #数据库连接会话
        self._request_sem = asyncio.Semaphore(2)               #限制同时进行的HTTP请求数量，避免过度并发导致目标服务器拒绝服务
        self._domain_last_hit: Dict[str, float] = {}           #记录每个域名最后请求的时间，用于实现域名级别的请求间隔控制
        self._domain_min_interval_sec = 0.9                    #同一域名的最小请求间隔，单位为秒，设置为0.9秒可以在每秒钟内最多发送1-2个请求，降低被封禁的风险
        self._user_agents = [                                  #定义多个User-Agent,在请求头中随机选择一个，模拟不同的浏览器或爬虫身份，增加请求的多样性，减少被目标服务器识别为爬虫的风险
            "CommunitySafetyAlert/1.0 (+public-data-ingestor)",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) CommunitySafetyAlertBot/1.0",
            "Mozilla/5.0 (X11; Linux x86_64) CommunitySafetyAlertBot/1.0",
        ]

    async def start(self):
        headers = {
            "Accept": "application/json",
            "User-Agent": random.choice(self._user_agents),
        }
        if SOCRATA_APP_TOKEN:
            headers["X-App-Token"] = SOCRATA_APP_TOKEN
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=20),   # 设置请求超时事件为20秒
            headers=headers,
        )
        self.db = SessionLocal()                       # 创建数据库会话
        ensure_core_communities(self.db, commit=True)  # 确保数据库里存在核心社区数据

    async def stop(self):
        if self.session:
            await self.session.close()
        if self.db:
            self.db.close()

    @staticmethod
    def _pick_value(row: Dict[str, Any], keys: List[str]) -> Optional[str]:   #从数据行中按照优先级顺序提取第一个非空文本值
        for key in keys:
            value = row.get(key)
            if value is None:
                continue
            text = str(value).strip()
            if text:
                return text
        return None

    @staticmethod
    def _collect_values(row: Dict[str, Any], keys: List[str]) -> List[str]:  #从数据行中提取所有非空文本值
        values: List[str] = []
        seen = set()
        for key in keys:
            value = row.get(key)
            if value is None:
                continue
            text = str(value).strip()
            if not text:
                continue
            norm = " ".join(text.split()).lower()
            if norm in seen:
                continue
            seen.add(norm)
            values.append(text)
        return values

    def _build_incident_narrative(self, row: Dict[str, Any], source: PublicSourceConfig) -> str:      #生成事件叙述文本
        narrative_keys = [
            "incident_description", "description", "narrative", "summary", "details",
            "event_clearance_description", "initial_type_description", "offense_location_description",
            "location_description", "status_desc", "premis_desc", "primary_type",
            "highest_offense_description", "text_general_code", "offense", "offense_text",
        ]
        merged_keys = source.description_fields + narrative_keys
        fragments = self._collect_values(row, merged_keys)
        if not fragments:
            return ""
        # Keep first few high-signal snippets; avoid overlong repeated text.
        return " | ".join(fragments[:4])[:900]

    @staticmethod
    def _parse_datetime(raw: Optional[str]) -> datetime:      #时间和数值处理函数
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
        val = (text or "").lower()

        # Earthquake / seismic events
        if any(
            k in val
            for k in [
                "earthquake",
                "seismic",
                "tremor",
                "aftershock",
                "foreshock",
                "magnitude",
                "richter",
                "quake",
            ]
        ):
            return EventType.EARTHQUAKE

        # Property crime
        if any(
            k in val
            for k in [
                "theft",
                "stolen",
                "larceny",
                "burglary",
                "robbery",
                "shoplift",
                "motor vehicle theft",
                "auto theft",
                "breaking and entering",
                "b&e",
                "grand theft",
                "petit theft",
                "property crime",
                "stolen vehicle",
                "vehicle stolen",
                "trespass of vehicle",
            ]
        ):
            return EventType.THEFT

        # Violent crime
        if any(
            k in val
            for k in [
                "shoot",
                "gun",
                "weapon",
                "homicide",
                "murder",
                "manslaughter",
                "assault",
                "battery",
                "rape",
                "kidnapping",
                "carjacking",
                "domestic violence",
                "domestic assault",
                "home invasion",
                "homicide investigation",
                "shots fired",
            ]
        ):
            return EventType.SHOOTING

        # Fire and arson
        if any(
            k in val
            for k in [
                "fire",
                "wildfire",
                "arson",
                "explosion",
                "red flag",
                "smoke",
                "brush fire",
                "structure fire",
                "alarm fire",
                "burn",
            ]
        ):
            return EventType.FIRE

        # Fraud and white-collar offense
        if any(
            k in val
            for k in [
                "fraud",
                "forgery",
                "counterfeit",
                "scam",
                "identity theft",
                "embezzle",
                "money laundering",
                "wire fraud",
                "credit card fraud",
                "phishing",
                "imposter",
                "fake check",
                "forged",
            ]
        ):
            return EventType.FRAUD

        # Public safety / disorder alerts
        if any(
            k in val
            for k in [
                "warning",
                "watch",
                "advisory",
                "alert",
                "security",
                "disturbance",
                "suspicious",
                "trespass",
                "vandalism",
                "public safety",
                "evacuation",
                "missing person",
                "traffic hazard",
                "road closure",
                "hazmat",
                "civil unrest",
                "disturbing the peace",
                "noise complaint",
            ]
        ):
            return EventType.SECURITY
        return EventType.OTHER

    @staticmethod
    def _normalize_danger_level(type_text: str, details_text: str) -> DangerLevel:
        text = f"{type_text or ''} {details_text or ''}".lower()
        if any(
            k in text
            for k in [
                "homicide",
                "murder",
                "shoot",
                "armed",
                "weapon",
                "aggravated",
                "carjacking",
                "kidnapping",
                "rape",
            ]
        ):
            return DangerLevel.HIGH
        if any(
            k in text
            for k in [
                "robbery",
                "burglary",
                "assault",
                "battery",
                "arson",
                "fire",
                "fraud",
                "larceny",
                "vehicle theft",
            ]
        ):
            return DangerLevel.MEDIUM
        return DangerLevel.LOW

    async def _fetch_rows(self, source: PublicSourceConfig, limit_per_source: int) -> List[Dict[str, Any]]:
        params = dict(source.params)
        params["$limit"] = str(limit_per_source)
        if SOCRATA_APP_TOKEN:
            params["$$app_token"] = SOCRATA_APP_TOKEN
        payload = await self._fetch_json(source.url, params=params, source_name=source.name)
        if isinstance(payload, list):
            return payload
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
        narrative_text = self._build_incident_narrative(row, source)
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
            enforce_existing=True,
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

        classification_text = " ".join([type_text or "", details_text or "", address_text or ""])
        event_type = self._normalize_event_type(classification_text)
        danger_level = self._normalize_danger_level(type_text, details_text)
        record_id = self._pick_value(row, source.id_fields) or f"{community.id}-{abs(hash(str(row))) % 1000000}"
        title = f"{type_text.title()} reported"
        when_text = event_time.isoformat() if event_time else "unknown"
        if narrative_text:
            description = (
                f"Incident narrative: {narrative_text}. "
                f"Type: {type_text or 'unknown'}. "
                f"Danger: {danger_level.value if hasattr(danger_level, 'value') else danger_level}. "
                f"Location: {address_text or community.name}. "
                f"Time: {when_text}. "
                f"Source: {source.name}."
            )
        else:
            description = (
                f"Type: {type_text or 'unknown'}. "
                f"Danger: {danger_level.value if hasattr(danger_level, 'value') else danger_level}. "
                f"Location: {address_text or community.name}. "
                f"Time: {when_text}. "
                f"Details: {details_text or 'No additional details provided.'}. "
                f"Source: {source.name}."
            )
        source_url = f"{source.url}?record_id={record_id}"

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

    def reclassify_existing_events(self) -> Dict[str, int]:
        if not self.db:
            return {"checked": 0, "updated": 0}

        checked = 0
        updated = 0
        events = self.db.query(Event).all()
        for item in events:
            checked += 1
            text = " ".join(
                [
                    str(item.title or ""),
                    str(item.description or ""),
                    str(item.data_source or ""),
                ]
            )
            new_type = self._normalize_event_type(text)
            new_danger = self._normalize_danger_level(str(item.title or ""), str(item.description or ""))
            if item.event_type != new_type or item.danger_level != new_danger:
                item.event_type = new_type
                item.danger_level = new_danger
                updated += 1

        if updated:
            self.db.commit()
        return {"checked": checked, "updated": updated}

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
        payload = await self._fetch_json(url, source_name=url)
        if isinstance(payload, dict):
            return payload
        return {}

    async def _respect_domain_rate(self, url: str) -> None:
        netloc = urlparse(url).netloc.lower()
        if not netloc:
            return
        last = self._domain_last_hit.get(netloc)
        now = time.monotonic()
        if last is not None:
            wait_for = self._domain_min_interval_sec - (now - last)
            if wait_for > 0:
                await asyncio.sleep(wait_for + random.uniform(0.05, 0.18))
        self._domain_last_hit[netloc] = time.monotonic()

    async def _fetch_json(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        source_name: Optional[str] = None,
    ) -> Any:
        if not self.session:
            return {}
        name = source_name or url
        max_attempts = 4
        base_delay = 0.6

        for attempt in range(1, max_attempts + 1):
            await self._respect_domain_rate(url)
            try:
                async with self._request_sem:
                    async with self.session.get(
                        url,
                        params=params,
                        headers={"User-Agent": random.choice(self._user_agents)},
                    ) as resp:
                        if resp.status == 200:
                            return await resp.json()
                        if resp.status in (403, 404):
                            logger.error("Source %s returned status %s", name, resp.status)
                            return {}
                        if resp.status in (429, 500, 502, 503, 504):
                            if attempt < max_attempts:
                                delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0.15, 0.5)
                                await asyncio.sleep(delay)
                                continue
                        logger.error("Source %s returned status %s", name, resp.status)
                        return {}
            except Exception as exc:
                if attempt < max_attempts:
                    delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0.15, 0.5)
                    await asyncio.sleep(delay)
                    continue
                logger.error("Failed fetching %s: %s", name, exc)
                return {}
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
                enforce_existing=True,
            )
            if not community:
                continue

            props = feature.get("properties") or {}
            mag = props.get("mag")
            place = props.get("place") or community.name
            title = props.get("title") or "Earthquake detected"
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
                    "description": (
                        f"USGS seismic event. Location: {place}. "
                        f"Magnitude: {mag}. "
                        f"Danger: {danger.value}. "
                        f"Time: {event_time.isoformat()}. "
                        "Source: USGS Earthquake Feed."
                    ),
                    "event_type": EventType.EARTHQUAKE,
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
                enforce_existing=True,
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
                    "title": f"{event_name}"[:200],
                    "description": (
                        f"Headline: {headline}. "
                        f"Danger: {danger.value}. "
                        f"Area: {area}. "
                        f"Details: {str(desc)[:800]}. "
                        "Source: NWS Alerts API."
                    ),
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

    def _normalize_calfire_incidents(self, payload: Any) -> List[Dict[str, Any]]:
        if isinstance(payload, dict):
            rows = payload.get("incidents") or payload.get("Incidents") or []
        elif isinstance(payload, list):
            rows = payload
        else:
            rows = []

        normalized = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            lat = self._safe_float(row.get("Latitude") or row.get("latitude"))
            lng = self._safe_float(row.get("Longitude") or row.get("longitude"))
            if lat is None or lng is None:
                continue

            title = str(row.get("Name") or row.get("name") or row.get("Title") or "Wildfire Incident")
            location = str(row.get("Location") or row.get("location") or row.get("County") or "California")
            details = str(
                row.get("SearchDescription")
                or row.get("description")
                or row.get("Type")
                or "CAL FIRE incident"
            )
            started = row.get("Started") or row.get("StartedDate") or row.get("Updated")
            event_time = self._parse_datetime(str(started) if started else None)
            incident_url = (
                row.get("Url")
                or row.get("url")
                or row.get("Link")
                or "https://www.fire.ca.gov/incidents/"
            )

            contained = self._safe_float(row.get("PercentContained") or row.get("percentContained"))
            if contained is None:
                danger = DangerLevel.HIGH
            elif contained < 25:
                danger = DangerLevel.HIGH
            elif contained < 70:
                danger = DangerLevel.MEDIUM
            else:
                danger = DangerLevel.LOW

            community = infer_community(
                self.db,
                latitude=lat,
                longitude=lng,
                address=location,
                zipcode=None,
                max_distance_km=220.0,
                allow_dynamic_core=True,
                enforce_existing=True,
            )
            if not community:
                continue

            normalized.append(
                {
                    "title": f"{title}"[:200],
                    "description": (
                        f"Incident: {title}. "
                        f"Danger: {danger.value}. "
                        f"Location: {location}. "
                        f"Details: {details}. "
                        "Source: CAL FIRE incidents feed."
                    ),
                    "event_type": EventType.FIRE,
                    "danger_level": danger,
                    "community_id": community.id,
                    "address": location[:255],
                    "latitude": float(lat),
                    "longitude": float(lng),
                    "zipcode": community.zipcode,
                    "event_time": event_time,
                    "data_source": "CAL FIRE Incidents",
                    "source_url": str(incident_url)[:500],
                }
            )
        return normalized

    def _normalize_eonet_events(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        events = payload.get("events") or []
        normalized = []
        for item in events:
            geometry = item.get("geometry") or []
            if not geometry:
                continue
            latest = geometry[-1]
            coords = latest.get("coordinates") or []
            gtype = latest.get("type")
            lat = None
            lng = None
            if gtype == "Point" and isinstance(coords, list) and len(coords) >= 2:
                lng = self._safe_float(coords[0])
                lat = self._safe_float(coords[1])
            if lat is None or lng is None:
                continue

            title = str(item.get("title") or "Natural hazard event")
            categories = item.get("categories") or []
            category_name = str(categories[0].get("title") if categories else "Hazard").lower()
            source_url = "https://eonet.gsfc.nasa.gov/"
            sources = item.get("sources") or []
            if sources and isinstance(sources[0], dict):
                source_url = str(sources[0].get("url") or source_url)

            event_type = EventType.OTHER
            danger = DangerLevel.MEDIUM
            if "wildfire" in category_name or "fire" in category_name:
                event_type = EventType.FIRE
                danger = DangerLevel.HIGH
            elif "volcano" in category_name or "earthquake" in category_name:
                event_type = EventType.EARTHQUAKE
                danger = DangerLevel.HIGH
            elif "storm" in category_name or "flood" in category_name:
                event_type = EventType.FRAUD
                danger = DangerLevel.MEDIUM
            elif "drought" in category_name:
                event_type = EventType.SECURITY
                danger = DangerLevel.MEDIUM

            event_time = self._parse_datetime(str(latest.get("date") or ""))
            community = infer_community(
                self.db,
                latitude=lat,
                longitude=lng,
                address=title,
                zipcode=None,
                max_distance_km=220.0,
                allow_dynamic_core=True,
                enforce_existing=True,
            )
            if not community:
                continue

            normalized.append(
                {
                    "title": f"{title}"[:200],
                    "description": (
                        f"Event: {title}. "
                        f"Category: {category_name}. "
                        f"Danger: {danger.value}. "
                        f"Approx location: {community.city}, {community.state}. "
                        "Source: NASA EONET."
                    ),
                    "event_type": event_type,
                    "danger_level": danger,
                    "community_id": community.id,
                    "address": title[:255],
                    "latitude": float(lat),
                    "longitude": float(lng),
                    "zipcode": community.zipcode,
                    "event_time": event_time,
                    "data_source": "NASA EONET",
                    "source_url": source_url[:500],
                }
            )
        return normalized

    def _normalize_philly_incidents(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        rows = payload.get("rows") or []
        normalized = []
        for row in rows:
            if not isinstance(row, dict):
                continue

            lat = self._safe_float(row.get("point_y") or row.get("lat") or row.get("latitude"))
            lng = self._safe_float(row.get("point_x") or row.get("lon") or row.get("longitude") or row.get("lng"))
            if lat is None or lng is None:
                continue

            offense = str(row.get("text_general_code") or row.get("ucr_general") or "Police incident").strip()
            block = str(row.get("location_block") or row.get("block") or "Philadelphia").strip()
            occurred = row.get("dispatch_date_time") or row.get("date") or row.get("reported_date")
            event_time = self._parse_datetime(str(occurred) if occurred else None)

            community = infer_community(
                self.db,
                latitude=lat,
                longitude=lng,
                address=block,
                zipcode=None,
                max_distance_km=220.0,
                allow_dynamic_core=True,
                enforce_existing=True,
            )
            if not community:
                continue

            details = (
                f"Offense: {offense}. "
                f"Block: {block}. "
                f"Record ID: {row.get('dc_key') or row.get('objectid') or 'n/a'}. "
                "Source: OpenDataPhilly (Carto)."
            )
            record_id = str(row.get("dc_key") or row.get("objectid") or f"phl-{abs(hash(str(row))) % 1000000}")
            source_url = f"https://phl.carto.com/tables/incidents_part1_part2/public?dc_key={record_id}"

            normalized.append(
                {
                    "title": f"{offense.title()} reported"[:200],
                    "description": details[:1200],
                    "event_type": self._normalize_event_type(offense),
                    "danger_level": self._normalize_danger_level(offense, details),
                    "community_id": community.id,
                    "address": block[:255],
                    "latitude": float(lat),
                    "longitude": float(lng),
                    "zipcode": community.zipcode,
                    "event_time": event_time,
                    "data_source": "OpenDataPhilly Crime Incidents",
                    "source_url": source_url[:500],
                }
            )
        return normalized

    def _normalize_dc_mpd_incidents(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        features = payload.get("features") or []
        normalized = []
        for feature in features:
            if not isinstance(feature, dict):
                continue

            attrs = feature.get("attributes") or {}
            geom = feature.get("geometry") or {}
            lat = self._safe_float(
                attrs.get("LATITUDE")
                or attrs.get("latitude")
                or attrs.get("Y")
                or geom.get("y")
            )
            lng = self._safe_float(
                attrs.get("LONGITUDE")
                or attrs.get("longitude")
                or attrs.get("X")
                or geom.get("x")
            )
            if lat is None or lng is None:
                continue

            offense = str(attrs.get("OFFENSE") or attrs.get("offense") or "Police incident").strip()
            method = str(attrs.get("METHOD") or attrs.get("method") or "").strip()
            block = str(attrs.get("BLOCK") or attrs.get("XBLOCK") or attrs.get("block") or "Washington, DC").strip()
            reported = attrs.get("REPORT_DAT") or attrs.get("START_DATE") or attrs.get("report_date")
            event_time = self._parse_datetime(str(reported) if reported else None)

            community = infer_community(
                self.db,
                latitude=lat,
                longitude=lng,
                address=block,
                zipcode=None,
                max_distance_km=220.0,
                allow_dynamic_core=True,
                enforce_existing=True,
            )
            if not community:
                continue

            method_text = f" Method: {method}." if method else ""
            details = (
                f"Offense: {offense}.{method_text} "
                f"Block: {block}. "
                f"Record ID: {attrs.get('CCN') or attrs.get('OBJECTID') or 'n/a'}. "
                "Source: DC MPD incidents feed."
            )
            record_id = str(attrs.get("CCN") or attrs.get("OBJECTID") or f"dc-{abs(hash(str(feature))) % 1000000}")
            source_url = f"https://opendata.dc.gov/datasets/crime-incidents-in-2025/about?ccn={record_id}"

            normalized.append(
                {
                    "title": f"{offense.title()} reported - {community.name}"[:200],
                    "description": details[:1200],
                    "event_type": self._normalize_event_type(offense),
                    "danger_level": self._normalize_danger_level(offense, details),
                    "community_id": community.id,
                    "address": block[:255],
                    "latitude": float(lat),
                    "longitude": float(lng),
                    "zipcode": community.zipcode,
                    "event_time": event_time,
                    "data_source": "DC MPD Crime Incidents",
                    "source_url": source_url[:500],
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

        calfire_payload = await self._fetch_json(
            "https://www.fire.ca.gov/umbraco/api/IncidentApi/List",
            params={"inactive": "false"},
            source_name="CAL FIRE Incidents",
        )
        calfire_events = self._normalize_calfire_incidents(calfire_payload) if calfire_payload else []
        calfire_inserted, calfire_skipped = self._save_events(calfire_events)
        results.append(
            {
                "source": "CAL FIRE Incidents",
                "fetched": len(calfire_payload) if isinstance(calfire_payload, list) else len(calfire_payload.get("incidents") or calfire_payload.get("Incidents") or []) if isinstance(calfire_payload, dict) else 0,
                "normalized": len(calfire_events),
                "inserted": calfire_inserted,
                "skipped": calfire_skipped,
            }
        )

        eonet_payload = await self._fetch_json(
            "https://eonet.gsfc.nasa.gov/api/v3/events",
            params={"status": "open", "limit": "120"},
            source_name="NASA EONET",
        )
        eonet_events = self._normalize_eonet_events(eonet_payload) if isinstance(eonet_payload, dict) else []
        eonet_inserted, eonet_skipped = self._save_events(eonet_events)
        results.append(
            {
                "source": "NASA EONET",
                "fetched": len((eonet_payload or {}).get("events") or []) if isinstance(eonet_payload, dict) else 0,
                "normalized": len(eonet_events),
                "inserted": eonet_inserted,
                "skipped": eonet_skipped,
            }
        )

        philly_payload = await self._fetch_json(
            "https://phl.carto.com/api/v2/sql",
            params={
                "q": (
                    "SELECT dc_key, dispatch_date_time, text_general_code, location_block, point_x, point_y "
                    "FROM incidents_part1_part2 "
                    "WHERE point_x IS NOT NULL AND point_y IS NOT NULL "
                    "ORDER BY dispatch_date_time DESC LIMIT 160"
                )
            },
            source_name="OpenDataPhilly Crime Incidents",
        )
        philly_events = self._normalize_philly_incidents(philly_payload) if isinstance(philly_payload, dict) else []
        philly_inserted, philly_skipped = self._save_events(philly_events)
        results.append(
            {
                "source": "OpenDataPhilly Crime Incidents",
                "fetched": len((philly_payload or {}).get("rows") or []) if isinstance(philly_payload, dict) else 0,
                "normalized": len(philly_events),
                "inserted": philly_inserted,
                "skipped": philly_skipped,
            }
        )

        dc_payload = await self._fetch_json(
            "https://maps2.dcgis.dc.gov/dcgis/rest/services/FEEDS/MPD/MapServer/0/query",
            params={
                "where": "1=1",
                "outFields": "CCN,OFFENSE,METHOD,BLOCK,XBLOCK,LATITUDE,LONGITUDE,REPORT_DAT,START_DATE,OBJECTID",
                "orderByFields": "REPORT_DAT DESC",
                "returnGeometry": "true",
                "resultRecordCount": "160",
                "outSR": "4326",
                "f": "json",
            },
            source_name="DC MPD Crime Incidents",
        )
        dc_events = self._normalize_dc_mpd_incidents(dc_payload) if isinstance(dc_payload, dict) else []
        dc_inserted, dc_skipped = self._save_events(dc_events)
        results.append(
            {
                "source": "DC MPD Crime Incidents",
                "fetched": len((dc_payload or {}).get("features") or []) if isinstance(dc_payload, dict) else 0,
                "normalized": len(dc_events),
                "inserted": dc_inserted,
                "skipped": dc_skipped,
            }
        )

        return results

    async def run_all(self, limit_per_source: int = 80) -> Dict[str, Any]:
        results = []
        for source in PUBLIC_SOURCES:
            result = await self.run_source(source, limit_per_source=limit_per_source)
            results.append(result)
            await asyncio.sleep(random.uniform(0.35, 1.1))

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
                summary["event_reclassification"] = ingestor.reclassify_existing_events()
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
