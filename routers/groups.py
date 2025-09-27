# routers/groups.py
from typing import List, Optional

from fastapi import APIRouter, Request, HTTPException, Query
from pymongo import ReturnDocument
from bson import ObjectId

from models import GroupCreate, GroupUpdate, GroupOut
from utils import to_oid  # your existing helper

router = APIRouter()

def groups_col(req: Request):
    return req.app.state.mongo["hackathon"]["groups"]

def users_col(req: Request):
    return req.app.state.mongo["hackathon"]["users"]

# helpers for this router
def to_oid_list(ids: list[str] | None) -> list[ObjectId]:
    if not ids:
        return []
    return [to_oid(x) for x in ids]

def oid_str(x):
    return str(x) if isinstance(x, ObjectId) else x

def normalize_group(doc: dict) -> dict:
    d = dict(doc)
    d["_id"] = oid_str(d["_id"])
    if "user_ids" in d and isinstance(d["user_ids"], list):
        d["user_ids"] = [oid_str(v) for v in d["user_ids"]]
    if "past_bet_ids" in d and isinstance(d["past_bet_ids"], list):
        d["past_bet_ids"] = [oid_str(v) for v in d["past_bet_ids"]]
    if "current_bet_id" in d:
        d["current_bet_id"] = oid_str(d["current_bet_id"])
    return d

@router.post("", response_model=GroupOut, status_code=201)
async def create_group(request: Request, payload: GroupCreate):
    c = groups_col(request)
    doc = payload.model_dump()
    # convert incoming string ids to ObjectId for storage
    doc["user_ids"] = to_oid_list(doc.get("user_ids"))
    doc["past_bet_ids"] = to_oid_list(doc.get("past_bet_ids"))
    if doc.get("current_bet_id") is not None:
        doc["current_bet_id"] = to_oid(doc["current_bet_id"])
    res = await c.insert_one(doc)
    saved = await c.find_one({"_id": res.inserted_id})
    return normalize_group(saved)

@router.get("", response_model=List[GroupOut])
async def list_groups(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    skip: int = 0,
    name: Optional[str] = None,
):
    c = groups_col(request)
    filt = {"name": name} if name else {}
    cur = c.find(filt).sort("_id", 1).skip(skip).limit(limit)
    docs = [normalize_group(d) async for d in cur]
    return docs

@router.get("/{id}", response_model=GroupOut)
async def get_group(request: Request, id: str):
    c = groups_col(request)
    doc = await c.find_one({"_id": to_oid(id)})
    if not doc:
        raise HTTPException(404, "Not found")
    return normalize_group(doc)

@router.patch("/{id}", response_model=GroupOut)
async def patch_group(request: Request, id: str, patch: GroupUpdate):
    c = groups_col(request)
    data = patch.model_dump(exclude_unset=True)
    # convert any id fields from strings to ObjectId
    if "user_ids" in data and data["user_ids"] is not None:
        data["user_ids"] = to_oid_list(data["user_ids"])
    if "past_bet_ids" in data and data["past_bet_ids"] is not None:
        data["past_bet_ids"] = to_oid_list(data["past_bet_ids"])
    if "current_bet_id" in data:
        data["current_bet_id"] = (
            None if data["current_bet_id"] is None else to_oid(data["current_bet_id"])
        )
    doc = await c.find_one_and_update(
        {"_id": to_oid(id)},
        {"$set": data} if data else {},
        return_document=ReturnDocument.AFTER,
    )
    if not doc:
        raise HTTPException(404, "Not found")
    return normalize_group(doc)

@router.delete("/{id}", status_code=204)
async def delete_group(request: Request, id: str):
    c = groups_col(request)
    res = await c.delete_one({"_id": to_oid(id)})
    if res.deleted_count == 0:
        raise HTTPException(404, "Not found")
    return

# membership

@router.post("/{group_id}/join/{user_id}", response_model=GroupOut)
async def join_group(request: Request, group_id: str, user_id: str):
    gc = groups_col(request)
    uc = users_col(request)
    gid = to_oid(group_id)
    uid = to_oid(user_id)
    await gc.update_one({"_id": gid}, {"$addToSet": {"user_ids": uid}})
    await uc.update_one({"_id": uid}, {"$addToSet": {"group_ids": gid}})
    doc = await gc.find_one({"_id": gid})
    if not doc:
        raise HTTPException(404, "Group not found")
    return normalize_group(doc)

@router.post("/{group_id}/leave/{user_id}", response_model=GroupOut)
async def leave_group(request: Request, group_id: str, user_id: str):
    gc = groups_col(request)
    uc = users_col(request)
    gid = to_oid(group_id)
    uid = to_oid(user_id)
    await gc.update_one({"_id": gid}, {"$pull": {"user_ids": uid}})
    await uc.update_one({"_id": uid}, {"$pull": {"group_ids": gid}})
    doc = await gc.find_one({"_id": gid})
    if not doc:
        raise HTTPException(404, "Group not found")
    return normalize_group(doc)
