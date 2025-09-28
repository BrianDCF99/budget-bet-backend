# models.py
from __future__ import annotations
from typing import Optional, List, Dict
from datetime import datetime, UTC
from enum import Enum
from pydantic import BaseModel, Field, EmailStr


class BetStatus(str, Enum):
    planned = "planned"
    active = "active"
    finished = "finished"
    cancelled = "cancelled"


class BetProgress(BaseModel):
    user_id: str
    progress: float = 0.0
    last_updated: datetime = Field(default_factory=lambda: datetime.now(UTC))


class BetBase(BaseModel):
    group_id: str
    title: str
    user_progress: List[BetProgress] = []
    start_date: datetime
    end_date: datetime
    status: BetStatus = BetStatus.planned
    meta: Dict[str, str] = {}


class BetCreate(BetBase):
    pass


class BetUpdate(BaseModel):
    title: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: Optional[BetStatus] = None
    meta: Optional[Dict[str, str]] = None
    user_progress: Optional[List[BetProgress]] = None


class BetOut(BetBase):
    id: str = Field(alias="_id")


class GroupBase(BaseModel):
    name: str
    description: Optional[str] = None
    user_ids: List[str] = []
    current_bet_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    is_active: bool = True


class GroupCreate(GroupBase):
    pass


class GroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    user_ids: Optional[List[str]] = None
    current_bet_id: Optional[str] = None
    is_active: Optional[bool] = None


class GroupOut(GroupBase):
    id: str = Field(alias="_id")


class UserBase(BaseModel):
    profile_url: str
    username: str
    email: EmailStr
    group_ids: List[str] = []
    average_spending: float


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    profile_url: Optional[str] = None
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    group_ids: Optional[List[str]] = None
    average_spending: Optional[float] = None


class UserOut(UserBase):
    id: str = Field(alias="_id")
