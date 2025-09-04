import asyncio
import json
import logging
import os
import socket
import subprocess
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional

import psutil
import redis
from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("session_manager")

app = FastAPI(title="TigerVNC Session Manager")

# Redis (use docker service name)
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

# Resource and pool configuration
MAX_SESSIONS = int(os.getenv("MAX_SESSIONS", "100"))
SESSION_TTL_HOURS = int(os.getenv("SESSION_TTL_HOURS", "2"))
DEFAULT_TIMEOUT_MINUTES = int(os.getenv("SESSION_TIMEOUT", "30"))

DISPLAY_START = int(os.getenv("DISPLAY_START", "1"))
DISPLAY_END = int(os.getenv("DISPLAY_END", "100"))

VNC_PORT_START = int(os.getenv("VNC_PORT_START", "5901"))
VNC_PORT_END = int(os.getenv("VNC_PORT_END", "6000"))

WEB_PORT_START = int(os.getenv("WEB_PORT_START", "7901"))
WEB_PORT_END = int(os.getenv("WEB_PORT_END", "8000"))

# Host capacity estimates (for soft gating)
HOST_CPU_CORES = float(os.getenv("HOST_CPU_CORES", "64"))
HOST_MEMORY_MB = float(os.getenv("HOST_MEMORY_MB", "131072"))  # 128GB by default
HOST_BANDWIDTH_MBPS = float(os.getenv("HOST_BANDWIDTH_Mbps", "1000"))

# Per-session resource assumptions
RESOURCES_PER_SESSION = {
    "cpu": float(os.getenv("SESSION_CPU_CORES", "0.3")),   # cores
    "memory": float(os.getenv("SESSION_MEMORY_MB", "400")), # MB
    "bandwidth": float(os.getenv("SESSION_BANDWIDTH_Mbps", "5")) # Mbps
}

class SessionRequest(BaseModel):
    user_id: str
    task_id: Optional[int] = None
    timeout_minutes: int = DEFAULT_TIMEOUT_MINUTES

class Session:
    def __init__(self, session_id: str, display: int, vnc_port: int, web_port: int, user_id: str):
        self.session_id = session_id
        self.display = display
        self.vnc_port = vnc_port
        self.web_port = web_port
        self.user_id = user_id
        self.created_at = datetime.utcnow()
        self.last_accessed = datetime.utcnow()
        self.pid_novnc: Optional[int] = None
        self.status = "starting"
        self.password: Optional[str] = None
        self.passfile: Optional[str] = None

class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, Session] = {}
        self.display_pool = list(range(DISPLAY_START, DISPLAY_END + 1))
        self.vnc_port_pool = list(range(VNC_PORT_START, VNC_PORT_END + 1))
        self.web_port_pool = list(range(WEB_PORT_START, WEB_PORT_END + 1))

    def _generate_vnc_password(self) -> str:
        return str(uuid.uuid4())[:8]

    def _write_vnc_passfile(self, session_id: str, password: str) -> str:
        passfile = f"/tmp/vncpass_{session_id}"
        process = subprocess.run(
            ["vncpasswd", "-f"],
            input=password.encode(),
            stdout=subprocess.PIPE,
            check=True
        )
        with open(passfile, "wb") as f:
            f.write(process.stdout)
        os.chmod(passfile, 0o600)
        return passfile

    async def _wait_for_port(self, host: str, port: int, timeout: float = 10.0) -> bool:
        start = datetime.utcnow()
        while (datetime.utcnow() - start).total_seconds() < timeout:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(0.5)
                try:
                    sock.connect((host, port))
                    return True
                except Exception:
                    await asyncio.sleep(0.2)
        return False

    def _resource_ok(self) -> bool:
        active = len(self.sessions)
        next_count = active + 1
        cpu_need = next_count * RESOURCES_PER_SESSION["cpu"]
        mem_need = next_count * RESOURCES_PER_SESSION["memory"]
        bw_need = next_count * RESOURCES_PER_SESSION["bandwidth"]
        return (cpu_need <= HOST_CPU_CORES) and (mem_need <= HOST_MEMORY_MB) and (bw_need <= HOST_BANDWIDTH_MBPS)

    async def create_session(self, user_id: str, task_id: Optional[int] = None) -> Session:
        # Capacity and resource checks
        if len(self.sessions) >= MAX_SESSIONS or not self._resource_ok():
            raise HTTPException(status_code=503, detail="Maximum sessions reached or insufficient resources")

        if not self.display_pool or not self.vnc_port_pool or not self.web_port_pool:
            raise HTTPException(status_code=503, detail="No resources available")

        display = self.display_pool.pop(0)
        vnc_port = self.vnc_port_pool.pop(0)
        web_port = self.web_port_pool.pop(0)
        session_id = str(uuid.uuid4())

        session = Session(session_id, display, vnc_port, web_port, user_id)
        try:
            # Ensure xstartup exists (Dockerfile already creates it)
            xstartup_path = "/root/.vnc/xstartup"
            if not (os.path.exists(xstartup_path) and os.access(xstartup_path, os.X_OK)):
                try:
                    os.makedirs("/root/.vnc", exist_ok=True)
                    with open(xstartup_path, "w") as f:
                        f.write("#!/bin/sh\nunset SESSION_MANAGER\nunset DBUS_SESSION_BUS_ADDRESS\nexec startfluxbox\n")
                    os.chmod(xstartup_path, 0o755)
                except Exception as e:
                    logger.warning(f"Failed to ensure xstartup: {e}")

            # Generate VNC password and passfile
            vnc_password = self._generate_vnc_password()
            passfile = self._write_vnc_passfile(session_id, vnc_password)
            session.password = vnc_password
            session.passfile = passfile

            # Start TigerVNC server on :display
            vnc_cmd = [
                "vncserver",
                f":{display}",
                "-geometry", "1920x1080",
                "-depth", "24",
                "-rfbport", str(vnc_port),
                "-rfbauth", passfile,
                "-desktop", f"Session-{session_id}"
            ]
            logger.info(f"Starting vncserver: {' '.join(vnc_cmd)}")
            # vncserver daemonizes and spawns Xvnc; use -kill for teardown
            subprocess.run(vnc_cmd, check=True)

            # Wait for VNC port to be ready
            ok = await self._wait_for_port("127.0.0.1", vnc_port, timeout=10.0)
            if not ok:
                raise RuntimeError(f"VNC port {vnc_port} did not open")

            # Start noVNC/websockify for this session
            novnc_cmd = [
                "python3", "-m", "websockify",
                "--web", "/opt/noVNC",
                str(web_port),
                f"localhost:{vnc_port}"
            ]
            logger.info(f"Starting websockify: {' '.join(novnc_cmd)}")
            novnc_process = subprocess.Popen(
                novnc_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            session.pid_novnc = novnc_process.pid

            # Persist session to Redis
            session_data = {
                "session_id": session_id,
                "user_id": user_id,
                "display": display,
                "vnc_port": vnc_port,
                "web_port": web_port,
                "created_at": session.created_at.isoformat(),
                "task_id": task_id,
                "password": vnc_password,
                "status": "active"
            }
            redis_client.setex(
                f"session:{session_id}",
                timedelta(hours=SESSION_TTL_HOURS),
                json.dumps(session_data)
            )
            redis_client.setex(
                f"user_session:{user_id}",
                timedelta(hours=SESSION_TTL_HOURS),
                session_id
            )

            self.sessions[session_id] = session
            session.status = "active"
            logger.info(f"Created session {session_id} for user {user_id} on display :{display}")
            return session

        except Exception as e:
            # Return resources on failure
            logger.error(f"Failed to create session: {e}", exc_info=True)
            self.display_pool.insert(0, display)
            self.vnc_port_pool.insert(0, vnc_port)
            self.web_port_pool.insert(0, web_port)
            # Best-effort cleanup if partially started
            try:
                subprocess.run(["vncserver", "-kill", f":{display}"], check=False)
            except Exception:
                pass
            raise HTTPException(status_code=500, detail=str(e))

    async def destroy_session(self, session_id: str):
        session = self.sessions.get(session_id)
        if not session:
            # Attempt to fetch from Redis to free pools if present (best-effort)
            data = redis_client.get(f"session:{session_id}")
            if not data:
                return
            try:
                payload = json.loads(data)
                display = int(payload.get("display"))
                vnc_port = int(payload.get("vnc_port"))
                web_port = int(payload.get("web_port"))
            except Exception:
                return
            # Kill VNC
            subprocess.run(["vncserver", "-kill", f":{display}"], check=False)
            # Return pools
            self.display_pool.append(display)
            self.vnc_port_pool.append(vnc_port)
            self.web_port_pool.append(web_port)
            # Cleanup Redis
            redis_client.delete(f"session:{session_id}")
            if payload.get("user_id"):
                redis_client.delete(f"user_session:{payload['user_id']}")
            return

        # Kill VNC server
        try:
            subprocess.run(["vncserver", "-kill", f":{session.display}"], check=False)
        except Exception:
            pass

        # Kill noVNC
        if session.pid_novnc:
            try:
                os.kill(session.pid_novnc, 15)
            except Exception:
                pass

        # Return resources
        self.display_pool.append(session.display)
        self.vnc_port_pool.append(session.vnc_port)
        self.web_port_pool.append(session.web_port)

        # Cleanup Redis
        redis_client.delete(f"session:{session_id}")
        redis_client.delete(f"user_session:{session.user_id}")

        # Remove from memory
        del self.sessions[session_id]
        logger.info(f"Destroyed session {session_id}")

    async def cleanup_expired_sessions(self):
        # Idle-based cleanup: if last_accessed older than 1 hour
        now = datetime.utcnow()
        expired = []
        for sid, session in list(self.sessions.items()):
            idle = now - session.last_accessed
            if idle > timedelta(hours=1):
                expired.append(sid)
        for sid in expired:
            try:
                await self.destroy_session(sid)
            except Exception as e:
                logger.warning(f"Error cleaning up session {sid}: {e}")
        if expired:
            logger.info(f"Cleaned up {len(expired)} expired sessions")

session_manager = SessionManager()

def external_host() -> str:
    # For dev/local; in production put Nginx in front and use proper public host
    return os.getenv("VNC_PUBLIC_HOST", "localhost")

@app.post("/api/sessions/create")
async def create_session(request: SessionRequest, background_tasks: BackgroundTasks):
    # Reuse existing session for user if available
    existing_id = redis_client.get(f"user_session:{request.user_id}")
    if existing_id:
        payload = redis_client.get(f"session:{existing_id}")
        if payload:
            data = json.loads(payload)
            # Touch last_accessed
            s = session_manager.sessions.get(existing_id)
            if s:
                s.last_accessed = datetime.utcnow()
            host = external_host()
            data["vnc_url"] = f"ws://{host}:{data['web_port']}/websockify"
            data["web_url"] = f"http://{host}:{data['web_port']}/vnc.html"
            return data

    # Create new session
    session = await session_manager.create_session(request.user_id, request.task_id)
    # Schedule timeout cleanup
    timeout = max(1, int(request.timeout_minutes))
    background_tasks.add_task(cleanup_session_after_timeout, session.session_id, timeout)

    # Return connection info
    host = external_host()
    return {
        "session_id": session.session_id,
        "user_id": session.user_id,
        "display": session.display,
        "vnc_port": session.vnc_port,
        "web_port": session.web_port,
        "password": session.password,
        "vnc_url": f"ws://{host}:{session.web_port}/websockify",
        "web_url": f"http://{host}:{session.web_port}/vnc.html",
        "status": "active"
    }

@app.delete("/api/sessions/{session_id}")
async def destroy_session(session_id: str):
    await session_manager.destroy_session(session_id)
    return {"message": "Session destroyed"}

@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    payload = redis_client.get(f"session:{session_id}")
    if not payload:
        raise HTTPException(status_code=404, detail="Session not found")
    data = json.loads(payload)
    host = external_host()
    data["vnc_url"] = f"ws://{host}:{data['web_port']}/websockify"
    data["web_url"] = f"http://{host}:{data['web_port']}/vnc.html"
    return data

@app.get("/api/sessions")
async def list_sessions():
    return {
        "total": len(session_manager.sessions),
        "max": MAX_SESSIONS,
        "available": MAX_SESSIONS - len(session_manager.sessions),
        "sessions": [
            {
                "session_id": s.session_id,
                "user_id": s.user_id,
                "display": s.display,
                "status": s.status,
                "created_at": s.created_at.isoformat()
            }
            for s in session_manager.sessions.values()
        ]
    }

@app.get("/api/sessions/queue/status")
async def queue_status():
    # Stub for now (no queue implemented in Phase A)
    return {"position": 0, "total": 0}

@app.get("/api/sessions/stats")
async def stats():
    return {
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "memory_percent": psutil.virtual_memory().percent,
        "active_sessions": len(session_manager.sessions),
        "max_sessions": MAX_SESSIONS
    }

@app.get("/api/health")
async def health():
    return {
        "status": "healthy",
        "active_sessions": len(session_manager.sessions),
        "available_displays": len(session_manager.display_pool),
        "timestamp": datetime.utcnow().isoformat()
    }

async def cleanup_session_after_timeout(session_id: str, timeout_minutes: int):
    await asyncio.sleep(timeout_minutes * 60)
    try:
        await session_manager.destroy_session(session_id)
        logger.info(f"Session {session_id} timed out and was cleaned up")
    except Exception as e:
        logger.warning(f"Failed to cleanup session {session_id} after timeout: {e}")

async def periodic_cleanup():
    while True:
        try:
            await asyncio.sleep(300)  # 5 minutes
            await session_manager.cleanup_expired_sessions()
        except Exception as e:
            logger.warning(f"Periodic cleanup error: {e}")

@app.on_event("startup")
async def on_startup():
    # Kick off periodic cleanup
    asyncio.create_task(periodic_cleanup())
