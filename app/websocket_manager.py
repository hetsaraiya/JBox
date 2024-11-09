# app/websocket_manager.py
from typing import List
from fastapi import WebSocket, WebSocketDisconnect
import logging

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logging.info("WebSocket connection added. Total connections: %d", len(self.active_connections))

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logging.info("WebSocket connection removed. Total connections: %d", len(self.active_connections))

    async def send_message(self, message: str):
        logging.info("Sending message to %d connections: %s", len(self.active_connections), message)
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
                logging.info("Message sent successfully to a connection.")
            except Exception as e:
                logging.error("Failed to send message: %s", e)

manager = ConnectionManager()
