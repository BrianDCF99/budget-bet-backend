# routers/bets.py
from typing import List, Optional
from datetime import datetime, UTC

from fastapi import APIRouter, Request, HTTPException, Query
from pymongo import ReturnDocument
from bson import ObjectId

from models import BetCreate, BetUpdate, BetOut, BetStatus
from utils import to_oid

router = APIRouter()

def bets_col(req: Request):
    return req.app.state.mongo["hackathon"]["bets"]

def groups_col(req: Request):
    return req.app.state.mongo["hackathon"]["groups"]

# helpers
def oid_str(x):
    return str(x) if isinstance(x, ObjectId) else x

def normalize_bet(doc: dict) -> dict:
    d = dict(doc)
    d["_id"] = oid_str(d["_id"])
    d["group_id"] = oid_str(d["group_id"])
    up = d.get("user_progress") or []
    for p in up:
        p["user_id"] = oid_str(p.get("user_id"))
    return d

def to_oid_progress_list(items: list[dict] | None) -> list[dict]:
    if not items:
        return []
    out = []
    for p in items:
        q = dict(p)
        if "user_id" in q and q["user_id"] is not None:
            q["user_id"] = to_oid(q["user_id"])
        out.append(q)
    return out

@router.post("", response_model=BetOut, status_code=201)
async def create_bet(request: Request, payload: BetCreate):
    c = bets_col(request)
    doc = payload.model_dump()
    # convert ids to ObjectId for storage
    doc["group_id"] = to_oid(doc["group_id"])
    doc["user_progress"] = to_oid_progress_list(doc.get("user_progress"))
    res = await c.insert_one(doc)
    saved = await c.find_one({"_id": res.inserted_id})
    return normalize_bet(saved)

@router.get("", response_model=List[BetOut])
async def list_bets(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    skip: int = 0,
    group_id: Optional[str] = None,
    status: Optional[BetStatus] = None,
):
    c = bets_col(request)
    filt = {}
    if group_id:
        filt["group_id"] = to_oid(group_id)
    if status:
        filt["status"] = status
    cur = c.find(filt).sort("_id", 1).skip(skip).limit(limit)
    docs = [normalize_bet(d) async for d in cur]
    return docs

@router.get("/{id}", response_model=BetOut)
async def get_bet(request: Request, id: str):
    c = bets_col(request)
    doc = await c.find_one({"_id": to_oid(id)})
    if not doc:
        raise HTTPException(404, "Not found")
    return normalize_bet(doc)

@router.patch("/{id}", response_model=BetOut)
async def patch_bet(request: Request, id: str, patch: BetUpdate):
    c = bets_col(request)
    data = patch.model_dump(exclude_unset=True)

    # convert any ids in the patch payload
    if "group_id" in data and data["group_id"] is not None:
        data["group_id"] = to_oid(data["group_id"])
    if "user_progress" in data and data["user_progress"] is not None:
        data["user_progress"] = to_oid_progress_list(data["user_progress"])

    doc = await c.find_one_and_update(
        {"_id": to_oid(id)},
        {"$set": data} if data else {},
        return_document=ReturnDocument.AFTER,
    )
    if not doc:
        raise HTTPException(404, "Not found")
    return normalize_bet(doc)

@router.delete("/{id}", status_code=204)
async def delete_bet(request: Request, id: str):
    c = bets_col(request)
    res = await c.delete_one({"_id": to_oid(id)})
    if res.deleted_count == 0:
        raise HTTPException(404, "Not found")
    return

# lifecycle

@router.post("/{bet_id}/activate", response_model=BetOut)
async def activate_bet(request: Request, bet_id: str):
    bc = bets_col(request)
    gc = groups_col(request)
    bid = to_oid(bet_id)

    bet = await bc.find_one_and_update(
        {"_id": bid},
        {"$set": {"status": "active"}},
        return_document=ReturnDocument.AFTER,
    )
    if not bet:
        raise HTTPException(404, "Bet not found")

    gid = bet["group_id"]
    await gc.update_one({"_id": gid}, {"$set": {"current_bet_id": bid}})
    return normalize_bet(bet)

@router.post("/{bet_id}/finish", response_model=BetOut)
async def finish_bet(request: Request, bet_id: str):
    bc = bets_col(request)
    gc = groups_col(request)
    bid = to_oid(bet_id)

    bet = await bc.find_one_and_update(
        {"_id": bid},
        {"$set": {"status": "finished"}},
        return_document=ReturnDocument.AFTER,
    )
    if not bet:
        raise HTTPException(404, "Bet not found")

    gid = bet["group_id"]
    # only unset current if it matches this bet
    await gc.update_one(
        {"_id": gid},
        {"$addToSet": {"past_bet_ids": bid}}
    )
    await gc.update_one(
        {"_id": gid, "current_bet_id": bid},
        {"$unset": {"current_bet_id": ""}}
    )
    return normalize_bet(bet)

@router.post("/{bet_id}/progress/{user_id}", response_model=BetOut)
async def set_user_progress(request: Request, bet_id: str, user_id: str, progress: float):
    bc = bets_col(request)
    bid = to_oid(bet_id)
    uid = to_oid(user_id)
    now = datetime.now(UTC)

    # try update existing progress entry
    res = await bc.update_one(
        {"_id": bid, "user_progress.user_id": uid},
        {"$set": {"user_progress.$.progress": progress, "user_progress.$.last_updated": now}},
    )
    if res.matched_count == 0:
        # insert new entry, build dict directly with ObjectId
        entry = {"user_id": uid, "progress": progress, "last_updated": now}
        await bc.update_one({"_id": bid}, {"$addToSet": {"user_progress": entry}})

    doc = await bc.find_one({"_id": bid})
    if not doc:
        raise HTTPException(404, "Bet not found after update")
    return normalize_bet(doc)
