from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional, List
from models import EventType, DangerLevel, SafetyLevel, UserRole


# ============ User Schemas ============
class UserCreate(BaseModel):
    username: str = Field(..., min_length=6, max_length=20)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=20)
    captcha_id: str = Field(..., min_length=8, max_length=64)
    captcha_code: str = Field(..., min_length=4, max_length=8)


class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=6, max_length=20)
    email: Optional[EmailStr] = None
    current_password: Optional[str] = None
    new_password: Optional[str] = Field(None, min_length=8, max_length=20)


class UserLogin(BaseModel):
    username: str
    password: str
    captcha_id: str = Field(..., min_length=8, max_length=64)
    captcha_code: str = Field(..., min_length=4, max_length=8)


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: UserRole
    created_at: datetime

    class Config:
        from_attributes = True


class UserDetailResponse(UserResponse):
    is_active: bool
    updated_at: datetime


# ============ Event Schemas ============
class EventCreate(BaseModel):
    title: str
    description: str
    event_type: EventType
    danger_level: DangerLevel
    community_id: Optional[int] = None
    address: str
    latitude: float
    longitude: float
    zipcode: Optional[str] = None
    event_time: datetime
    data_source: str
    source_url: Optional[str] = None


class EventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    event_type: Optional[EventType] = None
    danger_level: Optional[DangerLevel] = None
    address: Optional[str] = None


class EventResponse(BaseModel):
    id: int
    title: str
    description: str
    event_type: EventType
    danger_level: DangerLevel
    community_id: int
    address: str
    latitude: float
    longitude: float
    zipcode: Optional[str]
    event_time: datetime
    data_source: str
    source_url: Optional[str] = None
    community_name: Optional[str] = None
    like_count: int
    comment_count: int
    created_at: datetime
    liked: bool = False
    saved: bool = False

    class Config:
        from_attributes = True


class EventDetailResponse(EventResponse):
    community: Optional['CommunitySimpleResponse']
    comments: List['CommentResponse'] = []
    updated_at: datetime


# ============ Community Schemas ============
class CommunityCreate(BaseModel):
    name: str
    state: str
    city: str
    zipcode: Optional[str] = None
    latitude: float
    longitude: float
    area: Optional[float] = None
    population: Optional[int] = None
    safety_level: SafetyLevel = SafetyLevel.MEDIUM


class CommunityUpdate(BaseModel):
    name: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    zipcode: Optional[str] = None
    area: Optional[float] = None
    population: Optional[int] = None
    safety_level: Optional[SafetyLevel] = None


class CommunitySimpleResponse(BaseModel):
    id: int
    name: str
    state: str
    city: str
    zipcode: Optional[str]
    safety_score: float
    safety_level: SafetyLevel

    class Config:
        from_attributes = True


class CommunityResponse(CommunitySimpleResponse):
    latitude: float
    longitude: float
    area: Optional[float]
    population: Optional[int]
    trend: str
    created_at: datetime
    report: Optional["CommunityReport"] = None


class CommunityReport(BaseModel):
    highRiskPeriods: str
    highRiskLocations: str
    safetyTips: str
    yoyComparison: str


class CommunityDetailResponse(CommunityResponse):
    events: List[EventResponse] = []
    report: CommunityReport
    followers_count: int = 0
    is_following: bool = False
    updated_at: datetime


# ============ Comment Schemas ============
class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=200)


class CommentUpdate(BaseModel):
    content: str = Field(..., min_length=1, max_length=200)


class CommentResponse(BaseModel):
    id: int
    content: str
    user_id: int
    event_id: int
    created_at: datetime
    user: Optional[UserResponse] = None

    class Config:
        from_attributes = True


# ============ Token Schemas ============
class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


class TokenData(BaseModel):
    username: Optional[str] = None


class CaptchaResponse(BaseModel):
    captcha_id: str
    image_data: str
    expires_in: int


class PasswordResetSendCodeRequest(BaseModel):
    account: str = Field(..., min_length=3, max_length=100)
    captcha_id: str = Field(..., min_length=8, max_length=64)
    captcha_code: str = Field(..., min_length=4, max_length=8)


class PasswordResetSendCodeResponse(BaseModel):
    message: str
    debug_code: Optional[str] = None


class PasswordResetConfirmRequest(BaseModel):
    account: str = Field(..., min_length=3, max_length=100)
    code: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., min_length=8, max_length=20)


# ============ Admin Schemas ============
class DashboardStats(BaseModel):
    total_users: int
    total_communities: int
    total_events: int
    total_comments: int
    today_new_events: int
    today_new_users: int


class SpiderStatus(BaseModel):
    is_running: bool
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    success_count: int
    failure_count: int
    last_error: Optional[str] = None


# ============ Assistant Schemas ============
class AssistantChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    language: str = Field(default="zh", pattern="^(zh|en)$")
    page_name: Optional[str] = Field(default=None, max_length=100)
    page_path: Optional[str] = Field(default=None, max_length=255)
    role: Optional[str] = Field(default="guest", max_length=20)
    page_summary: Optional[str] = Field(default=None, max_length=1000)
    page_explain: Optional[List[str]] = None


class AssistantChatResponse(BaseModel):
    reply: str
    model: str
    provider: str = "openai-compatible"


# ============ List Responses ============
class PaginatedResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List


class EventListResponse(BaseModel):
    total: int
    events: List[EventResponse]


class CommunityListResponse(BaseModel):
    total: int
    communities: List[CommunityResponse]


class CommentListResponse(BaseModel):
    total: int
    comments: List[CommentResponse]


# Update forward references
EventDetailResponse.update_forward_refs()
CommunityResponse.update_forward_refs()
