from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, Table, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum

Base = declarative_base()

# Association tables for many-to-many relationships
user_event_likes = Table(
    'user_event_likes',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('event_id', Integer, ForeignKey('events.id'), primary_key=True)
)

user_event_saves = Table(
    'user_event_saves',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('event_id', Integer, ForeignKey('events.id'), primary_key=True)
)

user_community_follows = Table(
    'user_community_follows',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('community_id', Integer, ForeignKey('communities.id'), primary_key=True)
)


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    USER = "user"


class EventType(str, enum.Enum):
    THEFT = "theft"
    SHOOTING = "shooting"
    FIRE = "fire"
    SECURITY = "security"
    FRAUD = "fraud"
    OTHER = "other"


class DangerLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class SafetyLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.USER)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    comments = relationship("Comment", back_populates="user", cascade="all, delete-orphan")
    liked_events = relationship("Event", secondary=user_event_likes, back_populates="liked_by")
    saved_events = relationship("Event", secondary=user_event_saves, back_populates="saved_by")
    followed_communities = relationship("Community", secondary=user_community_follows, back_populates="followers")


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    description = Column(Text)
    event_type = Column(Enum(EventType), nullable=False)
    danger_level = Column(Enum(DangerLevel), default=DangerLevel.MEDIUM)
    
    # Location
    community_id = Column(Integer, ForeignKey("communities.id"), nullable=False)
    address = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    zipcode = Column(String)
    
    # Event details
    event_time = Column(DateTime)
    data_source = Column(String)
    source_url = Column(String)
    
    # Meta
    like_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    community = relationship("Community", back_populates="events")
    comments = relationship("Comment", back_populates="event", cascade="all, delete-orphan")
    liked_by = relationship("User", secondary=user_event_likes, back_populates="liked_events")
    saved_by = relationship("User", secondary=user_event_saves, back_populates="saved_events")


class Community(Base):
    __tablename__ = "communities"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, unique=True, nullable=False)
    state = Column(String, nullable=False)
    city = Column(String, nullable=False)
    zipcode = Column(String)
    
    # Geography
    latitude = Column(Float)
    longitude = Column(Float)
    area = Column(Float)  # square miles
    population = Column(Integer)
    
    # Safety metrics
    safety_score = Column(Float, default=50.0)  # 0-100
    safety_level = Column(Enum(SafetyLevel), default=SafetyLevel.MEDIUM)
    trend = Column(String, default="stable")  # up, down, stable
    
    # Metadata
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    events = relationship("Event", back_populates="community", cascade="all, delete-orphan")
    followers = relationship("User", secondary=user_community_follows, back_populates="followed_communities")
    report_item = relationship("CommunityReport", back_populates="community", uselist=False, cascade="all, delete-orphan")


class CommunityReport(Base):
    __tablename__ = "community_reports"

    id = Column(Integer, primary_key=True, index=True)
    community_id = Column(Integer, ForeignKey("communities.id"), nullable=False, unique=True, index=True)
    high_risk_periods = Column(Text, default="")
    high_risk_locations = Column(Text, default="")
    safety_tips = Column(Text, default="")
    yoy_comparison = Column(Text, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    community = relationship("Community", back_populates="report_item")


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    
    # Metadata
    is_flagged = Column(Boolean, default=False)  # For moderating
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="comments")
    event = relationship("Event", back_populates="comments")


class SpiderTask(Base):
    __tablename__ = "spider_tasks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    url = Column(String, nullable=False)
    
    # Configuration
    enabled = Column(Boolean, default=True)
    last_run = Column(DateTime)
    next_run = Column(DateTime)
    
    # Statistics
    success_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)
    last_error = Column(Text)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class SensitiveWord(Base):
    __tablename__ = "sensitive_words"

    id = Column(Integer, primary_key=True, index=True)
    word = Column(String, unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class AuthCodePurpose(str, enum.Enum):
    PASSWORD_RESET = "password_reset"


class AuthVerificationCode(Base):
    __tablename__ = "auth_verification_codes"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, index=True, nullable=False)
    code_hash = Column(String, nullable=False)
    purpose = Column(Enum(AuthCodePurpose), nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    used = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
