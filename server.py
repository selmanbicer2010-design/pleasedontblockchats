from fastapi import FastAPI, WebSocket
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

    while True:
        message = await websocket.receive_text()
        message_history.append(message)
        for client in connected_clients:
            await client.send_text(message)
