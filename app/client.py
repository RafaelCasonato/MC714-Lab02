import httpx


async def post_json(url, data):
    async with httpx.AsyncClient(timeout=5) as client:
        response = await client.post(url, json=data)
        response.raise_for_status()
        return response.json()


async def send_message(peer_url, message):
    return await post_json(peer_url + "/messages", message)
