from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

app = FastAPI()
connected_clients = []
message_history = []

@app.get("/")
def homepage():
    with open("index.html") as f:
        return HTMLResponse(f.read())

@app.websocket("/ws")
async def chat_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)

    for old_message in message_history:
        await websocket.send_text(old_message)

    try:
        while True:
            message = await websocket.receive_text()
            message_history.append(message)

            dead_clients = []
            for client in connected_clients:
                try:
                    await client.send_text(message)
                except Exception:
                    dead_clients.append(client)

            for dead in dead_clients:
                connected_clients.remove(dead)
    except WebSocketDisconnect:
        connected_clients.remove(websocket)
