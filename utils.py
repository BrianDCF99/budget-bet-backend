# utils.py
import hashlib
from fastapi import HTTPException
from bson import ObjectId

def to_oid(s: str) -> ObjectId:
    if not ObjectId.is_valid(s):
        raise HTTPException(400, "Invalid id")
    return ObjectId(s)

def hash_password(pw: str) -> str:
    # Simple placeholder. Use passlib[bcrypt] in production.
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()
