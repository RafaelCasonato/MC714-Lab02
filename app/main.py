import os
import asyncio

from fastapi import FastAPI
from pydantic import BaseModel

from app.client import post_json, send_message


class Message(BaseModel):
    sender_id: str | None = None
    text: str
    clock: int | None = None


class LocalEvent(BaseModel):
    text: str = "evento local"


class MutexEnter(BaseModel):
    hold_seconds: float = 2


class MutexMessage(BaseModel):
    sender_id: str
    clock: int


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
MUTEX_STATE = "released"
MUTEX_REQUEST_CLOCK = None
MUTEX_PENDING_REPLIES = set()
MUTEX_DEFERRED_REPLIES = []
MUTEX_HISTORY = []

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


def other_peers():
    peers = {}

    for peer_id, peer_url in PEERS.items():
        if peer_id != NODE_ID:
            peers[peer_id] = peer_url

    return peers


def mutex_log(event):
    MUTEX_HISTORY.append(event)
    print(f"node {NODE_ID} mutex: {event}")


def has_priority(sender_id, sender_clock):
    if MUTEX_REQUEST_CLOCK is None:
        return False

    local_request = (MUTEX_REQUEST_CLOCK, int(NODE_ID))
    other_request = (sender_clock, int(sender_id))

    return local_request < other_request


async def send_mutex_reply(peer_id):
    clock = local_event(f"mutex reply para node {peer_id}")
    data = {
        "sender_id": NODE_ID,
        "clock": clock,
    }

    return await post_json(PEERS[peer_id] + "/mutex/reply", data)


@app.get("/status")
def status():
    return {
        "node_id": NODE_ID,
        "peers": PEERS,
        "clock": CLOCK,
        "clock_history": CLOCK_HISTORY,
        "mutex": {
            "state": MUTEX_STATE,
            "request_clock": MUTEX_REQUEST_CLOCK,
            "pending_replies": sorted(MUTEX_PENDING_REPLIES),
            "deferred_replies": MUTEX_DEFERRED_REPLIES,
            "history": MUTEX_HISTORY,
        },
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


@app.post("/mutex/enter")
async def enter_critical_section(data: MutexEnter):
    global MUTEX_STATE
    global MUTEX_REQUEST_CLOCK
    global MUTEX_PENDING_REPLIES

    if MUTEX_STATE != "released":
        return {
            "ok": False,
            "error": "node already requested or entered critical section",
            "state": MUTEX_STATE,
        }

    clock = local_event("mutex request")
    MUTEX_STATE = "wanted"
    MUTEX_REQUEST_CLOCK = clock
    MUTEX_PENDING_REPLIES = set(other_peers().keys())
    mutex_log(f"request clock={clock}")

    request = {
        "sender_id": NODE_ID,
        "clock": clock,
    }

    for peer_id, peer_url in other_peers().items():
        try:
            await post_json(peer_url + "/mutex/request", request)
        except Exception as error:
            MUTEX_PENDING_REPLIES.discard(peer_id)
            mutex_log(f"node {peer_id} nao respondeu request: {error}")

    for _ in range(100):
        if len(MUTEX_PENDING_REPLIES) == 0:
            break
        await asyncio.sleep(0.1)

    if len(MUTEX_PENDING_REPLIES) > 0:
        old_pending = sorted(MUTEX_PENDING_REPLIES)
        MUTEX_STATE = "released"
        MUTEX_REQUEST_CLOCK = None
        MUTEX_PENDING_REPLIES = set()
        mutex_log(f"timeout esperando replies de {old_pending}")

        return {
            "ok": False,
            "error": "timeout waiting replies",
            "pending_replies": old_pending,
        }

    MUTEX_STATE = "held"
    mutex_log("entered critical section")

    await asyncio.sleep(data.hold_seconds)
    await leave_critical_section()

    return {
        "ok": True,
        "node_id": NODE_ID,
        "message": "entered and left critical section",
    }


@app.post("/mutex/request")
async def receive_mutex_request(data: MutexMessage):
    receive_event(data.clock, f"mutex request de node {data.sender_id}")

    should_defer = MUTEX_STATE == "held" or (
        MUTEX_STATE == "wanted" and has_priority(data.sender_id, data.clock)
    )

    if should_defer:
        if data.sender_id not in MUTEX_DEFERRED_REPLIES:
            MUTEX_DEFERRED_REPLIES.append(data.sender_id)
        mutex_log(f"deferred reply to node {data.sender_id}")
        return {
            "ok": True,
            "deferred": True,
        }

    await send_mutex_reply(data.sender_id)
    mutex_log(f"sent reply to node {data.sender_id}")

    return {
        "ok": True,
        "deferred": False,
    }


@app.post("/mutex/reply")
def receive_mutex_reply(data: MutexMessage):
    receive_event(data.clock, f"mutex reply de node {data.sender_id}")
    MUTEX_PENDING_REPLIES.discard(data.sender_id)
    mutex_log(f"received reply from node {data.sender_id}")

    return {
        "ok": True,
        "pending_replies": sorted(MUTEX_PENDING_REPLIES),
    }


async def leave_critical_section():
    global MUTEX_STATE
    global MUTEX_REQUEST_CLOCK
    global MUTEX_PENDING_REPLIES
    global MUTEX_DEFERRED_REPLIES

    local_event("mutex release")
    MUTEX_STATE = "released"
    MUTEX_REQUEST_CLOCK = None
    MUTEX_PENDING_REPLIES = set()
    deferred = MUTEX_DEFERRED_REPLIES
    MUTEX_DEFERRED_REPLIES = []
    mutex_log(f"leaving critical section, deferred={deferred}")

    for peer_id in deferred:
        try:
            await send_mutex_reply(peer_id)
        except Exception as error:
            mutex_log(f"erro enviando deferred reply para node {peer_id}: {error}")
