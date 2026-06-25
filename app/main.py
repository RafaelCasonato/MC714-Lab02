import os

from fastapi import FastAPI
from pydantic import BaseModel

from app.client import send_message


class Message(BaseModel):
    sender_id: str | None = None
    text: str


def load_peers():
    peers_env = os.getenv("PEERS", "")
    peers = {}

    for item in peers_env.split(","):
        if not item:
            continue

        node_id, url = item.split("=", 1)
        peers[node_id] = url

    return peers


NODE_ID = os.getenv("NODE_ID", "1")
PEERS = load_peers()
MESSAGES = []

app = FastAPI(title=f"MC714 node {NODE_ID}")


@app.get("/")
def index():
    return {
        "message": "MC714 Lab02",
        "node_id": NODE_ID,
    }


@app.get("/health")
def health():
    return {
        "ok": True,
        "node_id": NODE_ID,
    }


@app.get("/status")
def status():
    return {
        "node_id": NODE_ID,
        "peers": PEERS,
        "messages_received": len(MESSAGES),
    }


@app.get("/peers")
def list_peers():
    return PEERS


@app.get("/messages")
def list_messages():
    return {
        "node_id": NODE_ID,
        "messages": MESSAGES,
    }


@app.post("/messages")
def receive_message(message: Message):
    data = {
        "sender_id": message.sender_id,
        "text": message.text,
    }
    MESSAGES.append(data)

    print(f"node {NODE_ID} recebeu mensagem de {message.sender_id}: {message.text}")

    return {
        "received_by": NODE_ID,
        "message": data,
    }


@app.post("/send/{peer_id}")
async def send_to_peer(peer_id: str, message: Message):
    if peer_id not in PEERS:
        return {
            "ok": False,
            "error": "peer not found",
            "peer_id": peer_id,
        }

    data = {
        "sender_id": NODE_ID,
        "text": message.text,
    }

    result = await send_message(PEERS[peer_id], data)

    return {
        "ok": True,
        "sent_by": NODE_ID,
        "sent_to": peer_id,
        "response": result,
    }


@app.post("/broadcast")
async def broadcast(message: Message):
    results = {}

    for peer_id, peer_url in PEERS.items():
        if peer_id == NODE_ID:
            continue

        data = {
            "sender_id": NODE_ID,
            "text": message.text,
        }

        try:
            results[peer_id] = await send_message(peer_url, data)
        except Exception as error:
            results[peer_id] = {
                "ok": False,
                "error": str(error),
            }

    return {
        "sent_by": NODE_ID,
        "results": results,
    }
