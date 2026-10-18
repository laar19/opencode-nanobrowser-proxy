import json
import logging
from typing import AsyncGenerator, Optional
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
import httpx
import uvicorn

from .config import (
    DEFAULT_MODEL,
    LOG_LEVEL,
    OPENCODE_API_KEY,
    OPENCODE_CHAT_ENDPOINT,
    OPENCODE_MODELS_ENDPOINT,
    PROXY_HOST,
    PROXY_PORT,
    mask_key,
)
from .session_manager import SessionManager

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("opencode_proxy")

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await http_client.aclose()

app = FastAPI(
    title="OpenCode Go Proxy for Nanobrowser",
    description="Local compatibility proxy bridging Nanobrowser and OpenCode Go",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware for Chrome Extension origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

session_manager = SessionManager()

# Global async HTTP client with connection pooling and TLS verification
http_client = httpx.AsyncClient(
    timeout=httpx.Timeout(connect=15.0, read=120.0, write=30.0, pool=30.0),
    verify=True,
)

@app.get("/")
@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "OpenCode Go Proxy for Nanobrowser",
        "version": "1.0.0",
        "api_key_configured": bool(OPENCODE_API_KEY),
        "api_key_masked": mask_key(OPENCODE_API_KEY),
        "endpoints": {
            "chat": OPENCODE_CHAT_ENDPOINT,
            "models": OPENCODE_MODELS_ENDPOINT,
        },
        "default_model": DEFAULT_MODEL,
    }

def get_auth_token(request: Request) -> str:
    """
    Extract token from request Authorization header or fallback to env.
    If the client sends 'local', dummy keys, or anything other than a valid
    oc_sk_... key, always enforce the verified OPENCODE_API_KEY from .env.
    """
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        client_token = auth_header[7:].strip()
        if client_token.startswith("oc_sk_"):
            logger.info("Using client-provided oc_sk_ key from Nanobrowser")
            return client_token
        else:
            logger.info(f"Client token '{client_token[:10]}...' ignored; using verified OPENCODE_API_KEY from .env")
    else:
        logger.info("No Bearer header from client; using verified OPENCODE_API_KEY from .env")
    return OPENCODE_API_KEY

@app.get("/v1/models")
@app.get("/models")
async def list_models(request: Request):
    """
    Proxies model listing to OpenCode Go models endpoint.
    OpenCode Go expects GET https://opencode.ai/inference/go/v1/models
    with a session header and auth header.
    """
    token = get_auth_token(request)
    session_id = request.headers.get("x-opencode-session") or "ses_discovery"

    headers = {
        "Authorization": f"Bearer {token}",
        "x-opencode-session": session_id,
        "User-Agent": "opencode-agent/1.0",
        "Accept": "application/json",
    }

    logger.info(f"Forwarding GET /models to {OPENCODE_MODELS_ENDPOINT}")
    try:
        upstream_resp = await http_client.get(OPENCODE_MODELS_ENDPOINT, headers=headers)
        logger.info(f"Models response from upstream: HTTP {upstream_resp.status_code}")
        
        return Response(
            content=upstream_resp.content,
            status_code=upstream_resp.status_code,
            media_type="application/json",
            headers={"Access-Control-Allow-Origin": "*"},
        )
    except httpx.RequestError as exc:
        logger.error(f"Error connecting to models upstream: {exc}")
        return JSONResponse(
            status_code=502,
            content={"error": {"message": f"Proxy connection error: {str(exc)}", "type": "proxy_error"}},
        )

@app.get("/v1/models/{model_id:path}")
@app.get("/models/{model_id:path}")
async def get_single_model(model_id: str, request: Request):
    """
    Handles single model lookup by Nanobrowser (e.g. GET /models/deepseek-v4.1-flash).
    """
    return JSONResponse(
        content={
            "id": model_id,
            "object": "model",
            "created": 1792349000,
            "owned_by": "opencode",
        },
        headers={"Access-Control-Allow-Origin": "*"},
    )

@app.post("/v1/chat/completions")
@app.post("/chat/completions")
async def chat_completions(request: Request):
    """
    Proxies chat completions requests from Nanobrowser to OpenCode Go.
    Handles streaming SSE (stream=True) and standard JSON completions,
    injecting stable x-opencode-session headers.
    """
    token = get_auth_token(request)
    try:
        body = await request.json()
    except Exception:
        body = {}

    explicit_session = request.headers.get("x-opencode-session") or request.headers.get("x-session-id")
    session_id = session_manager.get_or_create_session(explicit_session, body)

    model_requested = body.get("model", DEFAULT_MODEL)
    is_stream = bool(body.get("stream", False))

    logger.info(
        f"Chat request: model={model_requested}, stream={is_stream}, session={session_id[:16]}..."
    )

    upstream_headers = {
        "Authorization": f"Bearer {token}",
        "x-opencode-session": session_id,
        "User-Agent": "opencode-agent/1.0",
        "Content-Type": "application/json",
        "Accept": "text/event-stream" if is_stream else "application/json",
    }

    if is_stream:
        try:
            req = http_client.build_request(
                "POST",
                OPENCODE_CHAT_ENDPOINT,
                headers=upstream_headers,
                json=body,
                timeout=httpx.Timeout(connect=15.0, read=120.0, write=30.0, pool=30.0),
            )
            upstream_resp = await http_client.send(req, stream=True)

            if upstream_resp.status_code != 200:
                err_content = await upstream_resp.aread()
                await upstream_resp.aclose()
                logger.warning(
                    f"Upstream returned HTTP {upstream_resp.status_code} on stream request: {err_content.decode('utf-8', errors='replace')[:200]}"
                )
                return Response(
                    content=err_content,
                    status_code=upstream_resp.status_code,
                    media_type="application/json",
                    headers={
                        "Access-Control-Allow-Origin": "*",
                        "x-opencode-session": session_id,
                    },
                )

            async def stream_generator() -> AsyncGenerator[bytes, None]:
                try:
                    async for chunk in upstream_resp.aiter_bytes():
                        if chunk:
                            yield chunk
                finally:
                    await upstream_resp.aclose()

            return StreamingResponse(
                stream_generator(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Access-Control-Allow-Origin": "*",
                    "x-opencode-session": session_id,
                },
            )
        except httpx.RequestError as exc:
            logger.error(f"Streaming error: {exc}")
            return JSONResponse(
                status_code=502,
                content={"error": {"message": f"Proxy streaming error: {str(exc)}", "type": "proxy_error"}},
            )
    else:
        # Standard non-streaming completion
        try:
            upstream_resp = await http_client.post(
                OPENCODE_CHAT_ENDPOINT,
                headers=upstream_headers,
                json=body,
            )
            return Response(
                content=upstream_resp.content,
                status_code=upstream_resp.status_code,
                media_type="application/json",
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "x-opencode-session": session_id,
                },
            )
        except httpx.RequestError as exc:
            logger.error(f"Error connecting to chat upstream: {exc}")
            return JSONResponse(
                status_code=502,
                content={"error": {"message": f"Proxy connection error: {str(exc)}", "type": "proxy_error"}},
            )

def run():
    uvicorn.run(
        "opencode_proxy.main:app",
        host=PROXY_HOST,
        port=PROXY_PORT,
        log_level=LOG_LEVEL.lower(),
        access_log=True,
    )

if __name__ == "__main__":
    run()
