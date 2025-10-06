"""Simple bridge between serial clients and Unity.

This script exposes a TCP line-based endpoint for Arduino-style boards and a
WebSocket endpoint for the Unity visualiser. Both sides see the same messages
so Unity always reflects the freshest device state.
"""

import asyncio
import json
import time
from typing import Set

import websockets

client_writers: Set[asyncio.StreamWriter] = set()
unity_clients: Set[websockets.WebSocketServerProtocol] = set()
state = {
    "last_hello": None,
    "detections": [],
    "last_message": None,
}
lock = asyncio.Lock()

async def broadcast_to_unity(message: dict) -> None:
    """Send a JSON payload to every Unity WebSocket client."""
    if not unity_clients:
        return
    data = json.dumps(message)
    stale = []
    for client in unity_clients:
        try:
            await client.send(data)
        except Exception:
            stale.append(client)
    for client in stale:
        unity_clients.discard(client)

async def send_to_client(payload: dict) -> None:
    """Send the JSON payload to all connected serial clients."""
    if not client_writers:
        return
    line = json.dumps(payload) + "\n"
    data = line.encode()
    for writer in list(client_writers):
        try:
            writer.write(data)
            await writer.drain()
        except Exception:
            client_writers.discard(writer)

async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    """Receive newline-delimited JSON from a microcontroller and rebroadcast it."""
    client_writers.add(writer)
    peer = writer.get_extra_info("peername")
    print(json.dumps({"event": "device_connected", "peer": peer}), flush=True)
    try:
        while True:
            raw = await reader.readline()
            if not raw:
                break
            line = raw.decode().strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            async with lock:
                state["last_message"] = payload
                if payload.get("type") == "hello":
                    state["last_hello"] = time.time()
                if payload.get("type") == "detection":
                    state["detections"] = [payload]
            print(json.dumps({"source": "client", "payload": payload}), flush=True)
            await broadcast_to_unity({"source": "client", "payload": payload})
    finally:
        client_writers.discard(writer)
        print(json.dumps({"event": "device_disconnected", "peer": peer}), flush=True)
        writer.close()
        await writer.wait_closed()

async def handle_unity(websocket: websockets.WebSocketServerProtocol) -> None:
    """Mirror Unity messages back to the device stream and keep state in sync."""
    unity_clients.add(websocket)
    print(json.dumps({"event": "unity_connected", "peer": websocket.remote_address}), flush=True)
    try:
        async with lock:
            await websocket.send(json.dumps({"source": "snapshot", "payload": state}))
        try:
            async for message in websocket:
                try:
                    payload = json.loads(message)
                except json.JSONDecodeError:
                    continue
                await send_to_client(payload)
        except websockets.exceptions.ConnectionClosed as exc:
            print(json.dumps({"event": "unity_connection_closed", "peer": websocket.remote_address, "code": exc.code, "reason": exc.reason}), flush=True)
            return
    finally:
        unity_clients.discard(websocket)
        print(json.dumps({"event": "unity_disconnected", "peer": websocket.remote_address}), flush=True)

async def main() -> None:
    """Start the TCP and WebSocket endpoints and block forever."""
    server = await asyncio.start_server(handle_client, "0.0.0.0", 9000)
    async with server:
        async with websockets.serve(handle_unity, "0.0.0.0", 8765):
            await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
