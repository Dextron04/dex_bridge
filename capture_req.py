# save_and_parse_chatgpt_stream.py
import re
import os
import json
import time
import subprocess
from mitmproxy import http, ctx

HOST_RE = re.compile(r"(?:^|\.)chatgpt\.com$", re.IGNORECASE)
PATH_RE = re.compile(r"^/backend-api/f/conversation$", re.IGNORECASE)
OUT_DIR = "./parsed_matches"
os.makedirs(OUT_DIR, exist_ok=True)


def try_json_load(s):
    try:
        return json.loads(s)
    except Exception:
        return None


def extract_text_from_event(obj):
    """
    Extract streaming text pieces from a typical event JSON shape.
    Returns a list of text pieces (may be empty).
    Handles variants like:
      - {"choices":[{"delta":{"content":"..."}}, ...]}
      - {"choices":[{"text":"..."}, ...]}
      - {"message": {"content": {"parts":[...]}}}
    """
    pieces = []

    if not isinstance(obj, dict):
        return pieces

    # 1) top-level typical 'choices' streaming format
    choices = obj.get("choices")
    if isinstance(choices, list):
        for c in choices:
            # delta.content (streaming API)
            delta = c.get("delta", {})
            if isinstance(delta, dict):
                cont = delta.get("content")
                if isinstance(cont, str):
                    pieces.append(cont)
            # older shape: "text"
            text = c.get("text")
            if isinstance(text, str):
                pieces.append(text)
            # sometimes nested fields:
            msg = c.get("message")
            if isinstance(msg, dict):
                msg_content = msg.get("content")
                if isinstance(msg_content, dict):
                    parts = msg_content.get("parts")
                    if isinstance(parts, list):
                        for p in parts:
                            if isinstance(p, str):
                                pieces.append(p)
    # 2) chat.completions-like full object
    # e.g., {"message":{"content":{"parts":["..."]}}}
    message = obj.get("message")
    if isinstance(message, dict):
        content = message.get("content")
        if isinstance(content, dict):
            parts = content.get("parts")
            if isinstance(parts, list):
                for p in parts:
                    if isinstance(p, str):
                        pieces.append(p)

    # 3) direct top-level "text" / "content"
    if isinstance(obj.get("text"), str):
        pieces.append(obj.get("text"))
    if isinstance(obj.get("content"), str):
        pieces.append(obj.get("content"))

    return pieces


def parse_sse_like(text):
    """
    Parse SSE-like text into a list of JSON-parsed events.
    SSE typically looks like:
      data: {"choices":[...]}
      data: {"choices":[...]}
      data: [DONE]
    We split into blocks separated by blank lines and look for `data:` lines.
    """
    events = []
    for block in text.split("\n\n"):
        block = block.strip()
        if not block:
            continue
        # collect data: lines (multiple lines possible per block)
        data_lines = []
        for line in block.splitlines():
            if line.startswith("data:"):
                data_lines.append(line[len("data:"):].strip())
            # some servers don't prefix 'data:' — try to treat the whole block as json
        if not data_lines:
            # fallback: try to parse the whole block as json
            obj = try_json_load(block)
            if obj is not None:
                events.append(obj)
            continue
        for d in data_lines:
            if d == "[DONE]":
                continue
            obj = try_json_load(d)
            if obj is not None:
                events.append(obj)
            else:
                # if it's not JSON, stash the raw text
                events.append({"_raw": d})
    return events


def parse_ndjson_like(text):
    """
    Parse NDJSON where each newline is a JSON object.
    """
    events = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line == "[DONE]":
            continue
        obj = try_json_load(line)
        if obj is not None:
            events.append(obj)
        else:
            events.append({"_raw": line})
    return events


class StreamParserAddon:
    def __init__(self):
        self.response_buffers = {}
    
    def responseheaders(self, flow: http.HTTPFlow) -> None:
        """
        Called when response headers are received, before the body.
        Disable streaming for responses we want to capture.
        """
        try:
            host = getattr(flow.request, "host", None) or getattr(flow.request, "pretty_host", "")
            path = getattr(flow.request, "path", None)
            if path is None:
                url = getattr(flow.request, "pretty_url", "")
                path = re.sub(r"^https?://[^/]+", "", url)
        except Exception:
            return

        if HOST_RE.search(host) and PATH_RE.search(path):
            # Disable streaming for this response so we can capture the full content
            flow.response.stream = False
            ctx.log.info(f"[PARSER] disabled streaming for {host}{path}")
    
    def response(self, flow: http.HTTPFlow) -> None:
        # Only operate on matching host/path
        try:
            host = getattr(flow.request, "host", None) or getattr(flow.request, "pretty_host", "")
            path = getattr(flow.request, "path", None)
            if path is None:
                url = getattr(flow.request, "pretty_url", "")
                path = re.sub(r"^https?://[^/]+", "", url)
        except Exception:
            return

        if not (HOST_RE.search(host) and PATH_RE.search(path)):
            return

        ctx.log.info(f"[PARSER] matched response for {host}{path}")

        # Try multiple ways to get response bytes/text:
        text = None
        try:
            # raw_content is bytes; flow.response.content may be bytes too
            if getattr(flow.response, "raw_content", None) is not None:
                text = flow.response.raw_content.decode("utf-8", errors="replace")
            elif getattr(flow.response, "content", None) is not None:
                text = flow.response.content.decode("utf-8", errors="replace")
            else:
                # fallback to get_text()
                text = flow.response.get_text(strict=False)
        except Exception as e:
            ctx.log.warn(f"[PARSER] failed to decode response content: {e}")
            try:
                text = flow.response.get_text(strict=False)
            except Exception:
                text = None

        if not text:
            ctx.log.warn("[PARSER] no response text to parse (response might be streamed and not buffered).")
            # You may need to use mitmproxy's streaming hooks or dump raw TCP if responses are truly unbuffered.
            return

        # Heuristic: try SSE -> NDJSON -> full JSON
        events = parse_sse_like(text)
        if not events:
            events = parse_ndjson_like(text)
        if not events:
            # try full JSON parse
            obj = try_json_load(text)
            if obj is not None:
                events = [obj]

        # Extract textual pieces from each event
        pieces = []
        parsed_events = []
        for e in events:
            parsed_events.append(e)
            extracted = extract_text_from_event(e)
            if extracted:
                pieces.extend(extracted)

        reconstructed_text = "".join(pieces).strip()

        # Extract conversation_id from events
        conversation_id = None
        for e in parsed_events:
            if isinstance(e, dict) and "conversation_id" in e:
                conversation_id = e["conversation_id"]
                break

        # Build final JSON structure
        result = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "request_url": flow.request.url,
            "host": host,
            "path": path,
            "conversation_id": conversation_id,
            "reconstructed_text": reconstructed_text,
            "events_count": len(events),
            "parsed_events_preview": parsed_events,  # save all events, not just preview
        }

        # Create provider-specific subdirectory
        safe_host = re.sub(r"[^\w\-\_\.]", "_", host)
        provider_dir = os.path.join(OUT_DIR, safe_host)
        os.makedirs(provider_dir, exist_ok=True)

        # write pretty JSON using conversation_id and timestamp
        ts = time.strftime("%Y%m%dT%H%M%S")
        if conversation_id:
            fname = os.path.join(provider_dir, f"{conversation_id}__{ts}__conversation_parsed.json")
        else:
            fname = os.path.join(provider_dir, f"{ts}__conversation_parsed.json")
        
        try:
            with open(fname, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            ctx.log.info(f"[PARSER] wrote parsed JSON -> {fname}")
            
            # Auto-run merge script
            try:
                ctx.log.info("[PARSER] running merge script...")
                subprocess.Popen(
                    ["python", "merge_conversations.py"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            except Exception as e:
                ctx.log.warn(f"[PARSER] failed to run merge script: {e}")
                
        except Exception as e:
            ctx.log.warn(f"[PARSER] failed to write {fname}: {e}")


addons = [
    StreamParserAddon()
]
