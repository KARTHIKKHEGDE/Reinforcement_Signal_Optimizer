"""
WebSocket Manager for real-time data streaming
Broadcasts simulation metrics to connected clients
"""
from fastapi import WebSocket, WebSocketDisconnect, APIRouter
from typing import List, Dict
import asyncio
import json
from app.sumo.traci_handler import traci_handler
from app.config import settings


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.broadcasting = False
    
    async def connect(self, websocket: WebSocket):
        """Accept and store new WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"Client connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"Client disconnected. Total connections: {len(self.active_connections)}")
    
    async def broadcast(self, message: Dict):
        """Broadcast message to all connected clients"""
        disconnected = []
        
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"Error broadcasting to client: {e}")
                disconnected.append(connection)
        
        # Remove disconnected clients
        for connection in disconnected:
            self.disconnect(connection)
    
    async def start_broadcasting(self):
        """Start broadcasting simulation metrics"""
        self.broadcasting = True
        print("Started broadcasting simulation metrics")
        
        while self.broadcasting:
            try:
                # Get current metrics from SUMO
                metrics = traci_handler.get_metrics()
                
                # Broadcast to all connected clients
                if self.active_connections:
                    await self.broadcast(metrics)
                
                # Wait for configured interval
                await asyncio.sleep(settings.WS_UPDATE_INTERVAL)
                
            except Exception as e:
                print(f"Error in broadcast loop: {e}")
                await asyncio.sleep(1)
    
    def stop_broadcasting(self):
        """Stop broadcasting simulation metrics"""
        self.broadcasting = False
        print("Stopped broadcasting simulation metrics")


# Global connection manager
manager = ConnectionManager()

# WebSocket router
ws_router = APIRouter()


@ws_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time simulation data
    Clients connect here to receive live metrics
    """
    await manager.connect(websocket)
    
    try:
        # Keep connection alive and listen for client messages
        while True:
            # Receive any client messages (ping/pong, etc.)
            data = await websocket.receive_text()
            
            # Echo back for connection health check
            if data == "ping":
                await websocket.send_text("pong")
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)
