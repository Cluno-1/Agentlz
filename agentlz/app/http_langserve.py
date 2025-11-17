from __future__ import annotations
from typing import Dict
from fastapi import FastAPI, Depends
from agentlz.app.routers.users import router as users_router
from agentlz.app.routers.auth import router as auth_router
from agentlz.app.deps.auth_deps import require_auth


app = FastAPI()
app.include_router(auth_router)
app.include_router(users_router, dependencies=[Depends(require_auth)])





@app.get("/v1/health")
def health() -> Dict[str, str]:
    """健康检查：返回 OK"""
    return {"status": "ok"}