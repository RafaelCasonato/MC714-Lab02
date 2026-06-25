import os

from fastapi import FastAPI


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
    }

