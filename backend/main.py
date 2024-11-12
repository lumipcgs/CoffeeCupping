# main.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.options: List[dict] = []
        self.votes: Dict[str, int] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        await self.broadcast_status()

    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]

    async def broadcast_status(self):
        message = {
            "type": "STATUS_UPDATE",
            "data": {
                "options": self.options,
                "totalVotes": len(self.votes),
                "activeUsers": len(self.active_connections)
            }
        }
        await self.broadcast(message)

    async def broadcast(self, message: dict):
        for connection in self.active_connections.values():
            await connection.send_text(json.dumps(message))

manager = ConnectionManager()

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await manager.connect(websocket, user_id)
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message["type"] == "ADD_OPTION":
                manager.options.append(message["option"])
                await manager.broadcast_status()
                
            elif message["type"] == "VOTE":
                if user_id not in manager.votes:
                    manager.votes[user_id] = message["optionId"]
                    await manager.broadcast_status()
                    
            elif message["type"] == "REORDER":
                manager.options = message["options"]
                await manager.broadcast_status()
                
    except WebSocketDisconnect:
        manager.disconnect(user_id)
        await manager.broadcast_status()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)