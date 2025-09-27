from typing import Optional, List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from typing import Optional
import asyncio

# MongoDB connection with error handling
try:
    client = AsyncIOMotorClient("mongodb://localhost:27017", serverSelectionTimeoutMS=5000)
    db = client["hackathon"]
    users_collection = db["test_groups"]
    print("✅ Connected to MongoDB successfully!")
except Exception as e:
    print(f"❌ Failed to connect to MongoDB: {e}")
    print("💡 Make sure MongoDB is running on localhost:27017")


# Pydantic model



class UserIn(BaseModel):
    username: str
    email: str
    # TODO: GROUPS

class BetIn(BaseModel):
    pass

class GroupIn(BaseModel):
    # todo: users in the group





# FastAPI app
app = FastAPI(title="Simple User API", version="1.0.0")


# Helper to convert MongoDB document to User
def user_helper(user) -> dict:
    return {
        "id": str(user["_id"]),
        "name": user["name"],
        "age": user["age"]
    }


# Check MongoDB connection at startup
@app.on_event("startup")
async def startup_event():
    try:
        # Test the connection
        await client.admin.command('ismaster')
        print("✅ MongoDB connection verified!")
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")


# Routes
@app.post("/users/", response_model=UserInDB)
async def create_user(user: User):
    try:
        user_dict = user.dict()
        result = await users_collection.insert_one(user_dict)
        new_user = await users_collection.find_one({"_id": result.inserted_id})
        return user_helper(new_user)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/users/", response_model=list[UserInDB])
async def get_all_users():
    try:
        users = []
        async for user in users_collection.find():
            users.append(user_helper(user))
        return users
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/users/{user_id}", response_model=UserInDB)
async def get_user(user_id: str):
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user ID")

    try:
        user = await users_collection.find_one({"_id": ObjectId(user_id)})
        if user:
            return user_helper(user)
        raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.put("/users/{user_id}", response_model=UserInDB)
async def update_user(user_id: str, user: User):
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user ID")

    try:
        user_dict = user.dict()
        result = await users_collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": user_dict}
        )

        if result.modified_count == 1:
            updated_user = await users_collection.find_one({"_id": ObjectId(user_id)})
            return user_helper(updated_user)

        raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.delete("/users/{user_id}")
async def delete_user(user_id: str):
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user ID")

    try:
        result = await users_collection.delete_one({"_id": ObjectId(user_id)})
        if result.deleted_count == 1:
            return {"message": "User deleted successfully"}

        raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/")
async def root():
    return {"message": "User API is running! Go to /docs for API documentation"}


@app.get("/health")
async def health_check():
    try:
        await client.admin.command('ismaster')
        return {"status": "healthy", "database": "connected"}
    except:
        return {"status": "unhealthy", "database": "disconnected"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)