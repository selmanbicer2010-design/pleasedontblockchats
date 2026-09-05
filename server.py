import json
#from sqlite3.dbapi2 import connect as sqconnect

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

class Event:
    def __init__(self):
        self.callbacks = {}
        self.currentid_ = 0

    def connect(self, callback):
        self.currentid_ += 1
        id = self.currentid_
        self.callbacks[id] = callback
        return id

    def disconnect(self, id):
        if id in self.callbacks:
            del self.callbacks[id]

    async def fire(self, *args):
        callbacks = dict(self.callbacks)
        for callback in list(callbacks.values()):
            await callback(*args)

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

class ServerApplication:
    def __init__(self):
        self.messagehistory = []
        self.userlist = []

class Server:
    def __init__(self):
        self.fastapi = FastAPI()
        self.connectedclients = {}
        self.deadclients = []

        self.clientadded = Event()
        self.clientremoved = Event()

        self.application = ServerApplication()

    async def connectclient(self, client):
        self.connectedclients[client.websocket] = client
        await self.clientadded.fire(client)

    async def disconnectclient(self, client):
        if client.websocket in self.connectedclients:
            del self.connectedclients[client.websocket]
            await self.clientremoved.fire(client)

    async def sendtexteachclient(self, message : ServerSideClientTextInfo):
        for client in list(self.connectedclients.values()):
            try:
                await client.sendtext(message)
            except Exception:
                self.killclient(client)

        await self.cleanclients()

    def killclient(self, client):
        self.deadclients.append(client)

    async def cleanclients(self):
        for dead in self.deadclients:
            await self.disconnectclient(dead)
        self.deadclients.clear()

server = Server()
app = server.fastapi

class Client:
    def __init__(self, websocket, uuid, username):
        self.websocket = websocket
        self.uuid = uuid
        self.username = username

    async def sendtext(self, message : ServerSideClientTextInfo):
        await self.websocket.send_text(message.jsonstr())

    async def receivedtext(self):
        return await self.websocket.receive_text()

server.fastapi.mount("/images", StaticFiles(directory="images"), name="images")

@server.fastapi.get("/")
def homepage():
    with open("index.html") as f:
        return HTMLResponse(f.read())

async def clientremovedcb(client : Client):
    message = ServerSideClientTextInfo("userlist", {"oldusername": client.username, "newusername": "", "mode": "left"})
    if client.username in server.application.userlist:
        server.application.userlist.remove(client.username)
    await server.sendtexteachclient(message)

server.clientremoved.connect(clientremovedcb)

@server.fastapi.websocket("/ws")
async def chat_endpoint(websocket: WebSocket):
    await websocket.accept()
    client = Client(websocket, 0, "User")
    await server.connectclient(client)

    for oldmessage in server.application.messagehistory:
        await client.sendtext(oldmessage)

    for username in server.application.userlist:
        message = ServerSideClientTextInfo("userlist", {"oldusername": "", "newusername": username, "mode": "joined"})
        await client.sendtext(message)

    server.application.userlist.append("User")

    message = ServerSideClientTextInfo("userlist", {"oldusername": "", "newusername": "User", "mode": "joined"})
    await server.sendtexteachclient(message)

    try:
        while True:
            strdata = await client.receivedtext()
            parsed = json.loads(strdata)

            if parsed["type"] == "onopen":
                client.uuid = parsed["uuid"]
            if parsed["type"] == "nameset":
                before = client.username
                client.username = parsed["newname"]
                message = ServerSideClientTextInfo("userlist", {"oldusername": before, "newusername": client.username, "mode": "changed"})
                server.application.userlist[server.application.userlist.index(before)] = client.username
                await server.sendtexteachclient(message)
            if parsed["type"] == "chat":
                message = ServerSideClientTextInfo("chat", {"sender": client.username, "body": parsed["body"]})
                server.application.messagehistory.append(message)
                await server.sendtexteachclient(message)

            await server.cleanclients()
    except WebSocketDisconnect:
        await server.disconnectclient(client)
