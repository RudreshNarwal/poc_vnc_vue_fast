from fastapi import APIRouter, HTTPException, Request
from app.config import settings
import httpx

router = APIRouter()

BASE = settings.session_manager_url.rstrip("/")

async def forward(request: Request, method: str, path: str):
    url = f"{BASE}{path}"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if method == "GET":
                resp = await client.get(url)
            elif method == "POST":
                body = await request.json()
                resp = await client.post(url, json=body)
            elif method == "DELETE":
                resp = await client.delete(url)
            else:
                raise HTTPException(status_code=405, detail="Method not allowed")

        return resp.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/create")
async def create_session(request: Request):
    return await forward(request, "POST", "/api/sessions/create")

@router.delete("/{session_id}")
async def destroy_session(session_id: str, request: Request):
    return await forward(request, "DELETE", f"/api/sessions/{session_id}")

@router.get("/{session_id}")
async def get_session(session_id: str, request: Request):
    return await forward(request, "GET", f"/api/sessions/{session_id}")

@router.get("/")
async def list_sessions(request: Request):
    return await forward(request, "GET", "/api/sessions")

@router.get("/queue/status")
async def queue_status(request: Request):
    return await forward(request, "GET", "/api/sessions/queue/status")

@router.get("/stats")
async def stats(request: Request):
    return await forward(request, "GET", "/api/sessions/stats")
