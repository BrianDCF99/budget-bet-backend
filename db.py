from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "hackathon"

async def create_client() -> AsyncIOMotorClient:
    client = AsyncIOMotorClient(
        MONGO_URI,
        serverSelectionTimeoutMS=2000,
        connectTimeoutMS=2000,
        socketTimeoutMS=5000,
        retryWrites=True,
    )
    await client.admin.command("ping")
    return client
