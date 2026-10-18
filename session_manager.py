import hashlib
import time
import uuid
from typing import Any, Dict, List, Optional

class SessionManager:
    """
    Manages stable OpenCode session IDs (x-opencode-session).
    Ensures that multiple requests belonging to the same conversation
    or agent task reuse the exact same session ID, enabling proper
    upstream prompt caching and conversation routing.
    """

    def __init__(self, ttl_seconds: int = 3600):
        self.ttl_seconds = ttl_seconds
        # Map: anchor_hash -> {"session_id": str, "last_seen": float, "count": int}
        self._sessions: Dict[str, Dict[str, Any]] = {}

    def get_or_create_session(
        self,
        explicit_header: Optional[str] = None,
        body: Optional[Dict[str, Any]] = None,
    ) -> str:
        # 1. If client provided an explicit session header, honor it
        if explicit_header and explicit_header.strip():
            hdr = explicit_header.strip()
            if not hdr.startswith("ses_"):
                return f"ses_{hdr}"
            return hdr

        # 2. Derive stable anchor from conversation message history
        anchor = self._extract_conversation_anchor(body)
        now = time.time()

        if anchor in self._sessions:
            entry = self._sessions[anchor]
            entry["last_seen"] = now
            entry["count"] += 1
            return entry["session_id"]

        # 3. Create deterministic session ID based on anchor
        if anchor:
            anchor_hash = hashlib.sha256(anchor.encode("utf-8")).hexdigest()[:24]
            session_id = f"ses_{anchor_hash}"
        else:
            session_id = f"ses_{uuid.uuid4().hex[:24]}"

        self._sessions[anchor or session_id] = {
            "session_id": session_id,
            "last_seen": now,
            "count": 1,
        }
        self._cleanup()
        return session_id

    def _extract_conversation_anchor(self, body: Optional[Dict[str, Any]]) -> str:
        """
        Extracts the initial user message or system seed from the messages list.
        In multi-turn agent execution, the first user message is the user's task
        and remains invariant throughout the entire turn history.
        """
        if not body or not isinstance(body, dict):
            return ""

        messages = body.get("messages")
        if not isinstance(messages, list) or not messages:
            return ""

        # Strategy A: Find first 'user' role message
        for msg in messages:
            if isinstance(msg, dict) and msg.get("role") == "user":
                content = msg.get("content")
                if isinstance(content, str) and content.strip():
                    return f"user:{content.strip()}"
                elif isinstance(content, list):
                    # Multimodal parts: extract text
                    texts = [
                        p.get("text", "")
                        for p in content
                        if isinstance(p, dict) and p.get("type") == "text"
                    ]
                    if texts:
                        return f"user:{' '.join(texts).strip()}"

        # Strategy B: If no user message yet (e.g. system test), use first message
        first = messages[0]
        if isinstance(first, dict):
            role = first.get("role", "unknown")
            content = str(first.get("content", "")).strip()
            return f"{role}:{content[:100]}"

        return ""

    def _cleanup(self):
        """Remove sessions inactive for longer than TTL."""
        now = time.time()
        expired = [
            k
            for k, v in self._sessions.items()
            if now - v["last_seen"] > self.ttl_seconds
        ]
        for k in expired:
            del self._sessions[k]
