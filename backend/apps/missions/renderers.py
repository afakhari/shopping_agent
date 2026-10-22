"""DRF renderer declaration for mission-turn Server-Sent Events responses."""
from __future__ import annotations

import json
from typing import Any

from rest_framework.renderers import BaseRenderer


class ServerSentEventRenderer(BaseRenderer):
    """Allow content negotiation for the mission-turn endpoint's SSE contract.

    Successful mission turns return StreamingHttpResponse directly, bypassing this
    renderer. It is used for DRF-generated error responses (validation, not found,
    etc.), which are encoded as a single SSE data frame containing the standard
    JSON error envelope so the browser can show the actual error message.
    """

    media_type = "text/event-stream"
    format = "event-stream"
    charset = "utf-8"
    render_style = "text"

    def render(
        self,
        data: Any,
        accepted_media_type: str | None = None,
        renderer_context: dict[str, Any] | None = None,
    ) -> bytes:
        if data is None:
            return b""
        payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        return f"data: {payload}\n\n".encode(self.charset)
