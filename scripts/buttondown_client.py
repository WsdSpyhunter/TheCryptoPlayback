"""Thin wrapper around Buttondown's API. Always creates a DRAFT — this
script never sends. Sending is a manual click in the Buttondown dashboard,
by design, so nothing goes to subscribers without you reviewing it there."""
import os
import requests

API_URL = "https://api.buttondown.com/v1/emails"


def create_draft(subject, body_html):
    headers = {
        "Authorization": f"Token {os.environ['BUTTONDOWN_API_KEY']}",
        "Content-Type": "application/json",
    }
    payload = {"subject": subject, "body": body_html, "status": "draft"}
    resp = requests.post(API_URL, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()
