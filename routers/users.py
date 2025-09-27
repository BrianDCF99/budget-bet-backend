# routers/users.py
from typing import List, Optional

from fastapi import APIRouter, Request, HTTPException, Query
from pymongo import ReturnDocument
from bson import ObjectId

from models import UserCreate, UserUpdate, UserOut
from utils import to_oid, hash_password  # keep your existing helpers

router = APIRouter()

def users_col(req: Request):
    return req.app.state.mongo["hackathon"]["users"]

# helpers for this router
def to_oid_list(ids: list[str] | None) -> list[ObjectId]:
    if not ids:
        return []
    return [to_oid(x) for x in ids]

def normalize_user(doc: dict) -> dict:
    d = dict(doc)
    # convert ObjectIds to strings for the API model
    d["_id"] = str(d["_id"])
    if "group_ids" in d and isinstance(d["group_ids"], list):
        d["group_ids"] = [str(x) if isinstance(x, ObjectId) else x for x in d["group_ids"]]
    # never return the hash
    d.pop("password_hash", None)
    return d

@router.post("/", response_model=UserOut, status_code=201)
async def create_user(request: Request, payload: UserCreate):
    c = users_col(request)
    if await c.find_one({"email": payload.email}):
        raise HTTPException(409, "Email already exists")
    doc = payload.model_dump()
    # store group ids as ObjectId in Mongo
    doc["group_ids"] = to_oid_list(doc.get("group_ids"))
    pw = doc.pop("password")
    doc["password_hash"] = hash_password(pw)
    res = await c.insert_one(doc)
    saved = await c.find_one({"_id": res.inserted_id}, {"password_hash": 0})
    return normalize_user(saved)

@router.get("/", response_model=List[UserOut])
async def list_users(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
    email: Optional[str] = None,
):
    c = users_col(request)
    filt = {"email": email} if email else {}
    cur = c.find(filt, {"password_hash": 0}).sort("_id", 1).skip(skip).limit(limit)
    docs = [normalize_user(d) async for d in cur]
    return docs

@router.get("/{id}", response_model=UserOut)
async def get_user(request: Request, id: str):
    c = users_col(request)
    doc = await c.find_one({"_id": to_oid(id)}, {"password_hash": 0})
    if not doc:
        raise HTTPException(404, "Not found")
    return normalize_user(doc)

@router.patch("/{id}", response_model=UserOut)
async def patch_user(request: Request, id: str, patch: UserUpdate):
    c = users_col(request)
    data = patch.model_dump(exclude_unset=True)
    if "password" in data and data["password"] is not None:
        data["password_hash"] = hash_password(data.pop("password"))
    if "group_ids" in data and data["group_ids"] is not None:
        data["group_ids"] = to_oid_list(data["group_ids"])
    doc = await c.find_one_and_update(
        {"_id": to_oid(id)},
        {"$set": data} if data else {},
        return_document=ReturnDocument.AFTER,
        projection={"password_hash": 0},
    )
    if not doc:
        raise HTTPException(404, "Not found")
    return normalize_user(doc)

@router.delete("/{id}", status_code=204)
async def delete_user(request: Request, id: str):
    c = users_col(request)
    res = await c.delete_one({"_id": to_oid(id)})
    if res.deleted_count == 0:
        raise HTTPException(404, "Not found")
    return
