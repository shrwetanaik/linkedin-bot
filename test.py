import os
import http.client
import urllib.parse

PUSHOVER_USER = os.getenv("PUSHOVER_USER")
PUSHOVER_TOKEN = os.getenv("PUSHOVER_TOKEN")

def pushover_test():
    conn = http.client.HTTPSConnection("api.pushover.net", 443)
    post_data = urllib.parse.urlencode({
        "user": PUSHOVER_USER,
        "token": PUSHOVER_TOKEN,
        "message": "Manual test from FastAPI"
    })
    conn.request("POST", "/1/messages.json",  # <--- Only the path here!
  urllib.parse.urlencode({
    "token": "your_app_token_here",
    "user": "your_user_key_here",
    "message": "Manual test, hardcoded"
  }), { "Content-type": "application/x-www-form-urlencoded" })
    resp = conn.getresponse()
    print(resp.status, resp.reason)
    print(resp.read().decode())
    conn.close()

pushover_test()
