import json
from sqlite3.dbapi2 import connect as sqconnect

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

class Server:
    def __init__(self):
        self.app = FastAPI()
        self.messagehistory = []
        self.connectedclients = {}
        self.deadclients = []

    def connect(self, client):
        self.connectedclients[client.websocket] = client

    def disconnect(self, client):
        del self.connectedclients[client.websocket]

    def killclient(self, client):
        self.deadclients.append(client)

    def cleanclients(self):
        for dead in self.deadclients:
            self.disconnect(dead)
        self.deadclients.clear()

server = Server()
app = server.app

class Client:
    def __init__(self, websocket, uuid, username):
        self.websocket = websocket
        self.uuid = uuid
        self.username = username

    async def sendtext(self, message):
        await self.websocket.send_text(message)

    async def receivedtext(self):
        return await self.websocket.receive_text()

class ServerSideClientTextInfo:
    def __init__(self, msgtype, datadict):
        data = dict(datadict)
        data["type"] = msgtype
        self.msgtype = msgtype
        self.dict_ = data
        self.data_ = json.dumps(data)

    def jsonstr(self):
        return self.data_

    def dict(self):
        return self.dict_

server.app.mount("/images", StaticFiles(directory="images"), name="images")

@server.app.get("/")
def homepage():
    with open("index.html") as f:
        return HTMLResponse(f.read())

@server.app.websocket("/ws")
async def chat_endpoint(websocket: WebSocket):
    await websocket.accept()
    client = Client(websocket, 0, "")
    server.connect(client)

    for oldmessage in server.messagehistory:
        await client.sendtext(oldmessage.jsonstr())

    try:
        while True:
            strdata = await client.receivedtext()
            parsed = json.loads(strdata)

            if parsed["type"] == "identify":
                client.uuid = parsed["userId"]
            if parsed["type"] == "nameset":
                client.username = parsed["newname"]
            if parsed["type"] == "chat":
                message = ServerSideClientTextInfo("chat", {"sender": client.username, "body": parsed["body"]})
                server.messagehistory.append(message)
                for connectedclient in server.connectedclients.values():
                    try:
                        await connectedclient.sendtext(message.jsonstr())
                    except Exception:
                        server.killclient(connectedclient)

            server.cleanclients()
    except WebSocketDisconnect:
        server.disconnect(client)
