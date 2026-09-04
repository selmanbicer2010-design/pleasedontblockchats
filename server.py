from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse

app = FastAPI()
connected_clients = []

@app.get("/")
def homepage():
    with open("index.html") as f:
        return HTMLResponse(f.read())

@app.websocket("/ws")
async def chat_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)

    while True:
        message = await websocket.receive_text()
        for client in connected_clients:
            await client.send_text(message)
