from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import logging
import json

from app.services.automation import websocket_manager

logger = logging.getLogger(__name__)
router = APIRouter()

@router.websocket("/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time automation updates"""
    try:
        await websocket_manager.connect(websocket, session_id)
        logger.info(f"WebSocket connected for session: {session_id}")
        
        # Send initial connection message
        await websocket.send_json({
            "type": "connection",
            "status": "connected",
            "session_id": session_id,
            "message": "WebSocket connected successfully"
        })
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle different message types
                message_type = message.get("type")
                
                if message_type == "ping":
                    # Respond to ping with pong
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": message.get("timestamp")
                    })
                
                elif message_type == "heartbeat":
                    # Respond to heartbeat
                    await websocket.send_json({
                        "type": "heartbeat_ack",
                        "session_id": session_id
                    })
                
                else:
                    logger.warning(f"Unknown message type: {message_type}")
                
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON received from {session_id}")
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON format"
                })
            
            except Exception as e:
                logger.error(f"Error handling message from {session_id}: {str(e)}")
                break
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {str(e)}")
    finally:
        websocket_manager.disconnect(session_id)
