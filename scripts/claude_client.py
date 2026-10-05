"""Thin wrapper around the Claude API for this project. Expects the
ANTHROPIC_API_KEY env var. Always asks for JSON-only output and parses it."""
import os
import json
import re
import requests

API_URL = "https://api.anthropic.com/v1/messages"


def ask_claude_json(model, system_prompt, user_prompt, max_tokens=2000, attempts=3):
    """Asks for JSON and parses it. The model occasionally returns slightly
    malformed JSON (this failed the 2026-10-05 6:45 AM run), so a parse
    failure is retried with a fresh response before giving up."""
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            return _ask_once(model, system_prompt, user_prompt, max_tokens)
        except json.JSONDecodeError as exc:
            last_error = exc
            print(f"Claude returned malformed JSON (attempt {attempt}/{attempts}): {exc}")
    raise last_error


def _ask_once(model, system_prompt, user_prompt, max_tokens):
    headers = {
        "x-api-key": os.environ["ANTHROPIC_API_KEY"],
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    body = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_prompt}],
    }
    resp = requests.post(API_URL, headers=headers, json=body, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    text = "".join(block["text"] for block in data["content"] if block["type"] == "text")

    # Strip markdown code fences if the model added them despite instructions
    cleaned = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    return json.loads(cleaned)
