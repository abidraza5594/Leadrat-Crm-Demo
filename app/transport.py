"""Reuse TLS connections during application lifespan; isolated callers own theirs."""
from contextlib import asynccontextmanager
import httpx

shared = None

async def start():
    global shared
    shared = httpx.AsyncClient(limits=httpx.Limits(max_connections=20, max_keepalive_connections=10))

async def close():
    global shared
    client, shared = shared, None
    if client: await client.aclose()

@asynccontextmanager
async def client():
    if shared is not None and not shared.is_closed:
        yield shared
    else:
        async with httpx.AsyncClient() as owned: yield owned
