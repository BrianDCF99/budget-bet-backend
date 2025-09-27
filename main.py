# main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request

from db import create_client, DB_NAME
from routers.users import router as users_router
from routers.groups import router as groups_router
from routers.bets import router as bets_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # connect once and store the client on app.state
    app.state.mongo = await create_client()
    db = app.state.mongo[DB_NAME]

    # create indexes
    await db["users"].create_index("email", unique=True)
    await db["users"].create_index("group_ids")

    await db["groups"].create_index("name", unique=True)
    await db["groups"].create_index("user_ids")
    await db["groups"].create_index("current_bet_id")
    await db["groups"].create_index("past_bet_ids")

    await db["bets"].create_index([("group_id", 1), ("status", 1), ("start_date", 1)])
    await db["bets"].create_index("user_progress.user_id")

    try:
        yield
    finally:
        app.state.mongo.close()

app = FastAPI(lifespan=lifespan, openapi_url="/openapi.json", docs_url="/docs", redoc_url="/redoc")

# plug routers back in
app.include_router(users_router, prefix="/users", tags=["users"])
app.include_router(groups_router, prefix="/groups", tags=["groups"])
app.include_router(bets_router, prefix="/bets", tags=["bets"])

@app.get("/health")
async def health(request: Request):
    await request.app.state.mongo.admin.command("ping")
    return {"status": "ok"}

@app.get("/ping")
async def ping():
    return {"ok": True}
