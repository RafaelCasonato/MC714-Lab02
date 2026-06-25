import os

from fastapi import FastAPI
from pydantic import BaseModel

from app.client import send_message


class Message(BaseModel):
    sender_id: str | None = None
    text: str
    clock: int | None = None


class LocalEvent(BaseModel):
    text: str = "evento local"


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
CLOCK = 0
CLOCK_HISTORY = []

app = FastAPI(title=f"MC714 node {NODE_ID}")


def local_event(description):
    global CLOCK

    CLOCK += 1

    CLOCK_HISTORY.append({
        "type": "local",
        "clock": CLOCK,
        "description": description,
    })

    return CLOCK


def receive_event(received_clock, description):
    global CLOCK

    old_clock = CLOCK
    CLOCK = max(CLOCK, received_clock) + 1

    CLOCK_HISTORY.append({
        "type": "receive",
        "old_clock": old_clock,
        "received_clock": received_clock,
        "clock": CLOCK,
        "description": description,
    })

    return CLOCK


@app.get("/status")
def status():
    return {
        "node_id": NODE_ID,
        "peers": PEERS,
        "clock": CLOCK,
        "clock_history": CLOCK_HISTORY,
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
    received_clock = message.clock or 0
    new_clock = receive_event(received_clock, f"mensagem recebida de {message.sender_id}")

    data = {
        "sender_id": message.sender_id,
        "text": message.text,
        "received_clock": received_clock,
        "local_clock": new_clock,
    }
    MESSAGES.append(data)

    print(f"node {NODE_ID} recebeu mensagem de {message.sender_id}: {message.text} clock={new_clock}")

    return {
        "received_by": NODE_ID,
        "clock": new_clock,
        "message": data,
    }


@app.post("/clock/local")
def create_local_event(event: LocalEvent):
    new_clock = local_event(event.text)

    return {
        "node_id": NODE_ID,
        "clock": new_clock,
        "description": event.text,
    }


@app.post("/send/{peer_id}")
async def send_to_peer(peer_id: str, message: Message):
    if peer_id not in PEERS:
        return {
            "ok": False,
            "error": "peer not found",
            "peer_id": peer_id,
        }

    new_clock = local_event(f"envio para node {peer_id}")
    data = {
        "sender_id": NODE_ID,
        "text": message.text,
        "clock": new_clock,
    }

    result = await send_message(PEERS[peer_id], data)

    return {
        "ok": True,
        "sent_by": NODE_ID,
        "sent_to": peer_id,
        "clock": new_clock,
        "response": result,
    }


@app.post("/broadcast")
async def broadcast(message: Message):
    results = {}

    for peer_id, peer_url in PEERS.items():
        if peer_id == NODE_ID:
            continue

        new_clock = local_event(f"broadcast para node {peer_id}")
        data = {
            "sender_id": NODE_ID,
            "text": message.text,
            "clock": new_clock,
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
