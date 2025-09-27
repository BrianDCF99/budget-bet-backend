# models.py
from __future__ import annotations
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum
from bson import ObjectId


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if isinstance(v, ObjectId):
            return v
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)


class BetStatus(str, Enum):
    planned = "planned"
    active = "active"
    finished = "finished"
    cancelled = "cancelled"


class BetProgress(BaseModel):
    user_id: PyObjectId
    progress: float = 0.0
    last_updated: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        json_encoders={ObjectId: str},
        populate_by_name=True
    )


class BetBase(BaseModel):
    group_id: PyObjectId
    title: str
    total_budget: float
    user_progress: List[BetProgress] = []
    start_date: datetime
    end_date: datetime
    status: BetStatus = BetStatus.planned
    # optional freeform metadata, small only
    meta: Dict[str, str] = {}

    model_config = ConfigDict(
        json_encoders={ObjectId: str},
        populate_by_name=True
    )


class BetCreate(BetBase):
    pass


class BetUpdate(BaseModel):
    title: Optional[str] = None
    total_budget: Optional[float] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: Optional[BetStatus] = None
    meta: Optional[Dict[str, str]] = None
    # full replacement of progress list if supplied
    user_progress: Optional[List[BetProgress]] = None

    model_config = ConfigDict(
        json_encoders={ObjectId: str},
        populate_by_name=True
    )


class BetOut(BetBase):
    id: PyObjectId = Field(alias="_id")


class GroupBase(BaseModel):
    name: str
    description: Optional[str] = None
    # store member user ids
    user_ids: List[PyObjectId] = []
    # current bet id for convenience
    current_bet_id: Optional[PyObjectId] = None
    # history of past bet ids
    past_bet_ids: List[PyObjectId] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True

    model_config = ConfigDict(
        json_encoders={ObjectId: str},
        populate_by_name=True
    )


class GroupCreate(GroupBase):
    pass


class GroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    # membership changes handled via endpoints but allowed here too
    user_ids: Optional[List[PyObjectId]] = None
    current_bet_id: Optional[PyObjectId] = None
    past_bet_ids: Optional[List[PyObjectId]] = None
    is_active: Optional[bool] = None

    model_config = ConfigDict(
        json_encoders={ObjectId: str},
        populate_by_name=True
    )


class GroupOut(GroupBase):
    id: PyObjectId = Field(alias="_id")


# ---------- User ----------
class UserBase(BaseModel):
    username: str
    email: EmailStr
    # store group references on the user too if you want fast reverse lookups
    group_ids: List[PyObjectId] = []

    model_config = ConfigDict(
        json_encoders={ObjectId: str},
        populate_by_name=True
    )


# For API create. Contains plaintext password input.
class UserCreate(UserBase):
    password: str


# For API patch. Only optional fields.
class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    group_ids: Optional[List[PyObjectId]] = None

    model_config = ConfigDict(
        json_encoders={ObjectId: str},
        populate_by_name=True
    )


# What you return to clients. Never include raw password here.
class UserOut(UserBase):
    id: PyObjectId = Field(alias="_id")


# ---------- Optional: DB-only model ----------
# If you want a model that represents how you actually store users in Mongo
# where password is already hashed and you never expose it
class UserDB(UserBase):
    _id: PyObjectId = Field(default_factory=PyObjectId)
    password_hash: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        json_encoders={ObjectId: str},
        populate_by_name=True
    )
