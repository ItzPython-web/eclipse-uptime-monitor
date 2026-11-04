import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


STATE_FILE = Path(__file__).with_name("state.json")


def request_ok(url, check_json=False):
    for attempt in range(3):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 EclipseMonitor"})
            with urllib.request.urlopen(request, timeout=8) as response:
                if response.status != 200:
                    raise ValueError("Unexpected status")
                if not check_json or json.load(response).get("ok") is True:
                    return True
        except (OSError, ValueError):
            if attempt < 2:
                time.sleep(2)
    return False


def notify(service):
    channel = os.environ["DISCORD_CHANNEL_ID"]
    owner = os.environ["DISCORD_OWNER_ID"]
    token = os.environ["DISCORD_TOKEN"]
    payload = json.dumps({
        "content": f"<@{owner}> Eclipse {service} is down. The external monitor cannot reach it.",
        "allowed_mentions": {"parse": [], "users": [owner]},
    }).encode()
    request = urllib.request.Request(
        f"https://discord.com/api/v10/channels/{channel}/messages",
        data=payload,
        headers={"Authorization": f"Bot {token}", "Content-Type": "application/json",
                 "User-Agent": "Eclipse-Uptime/1.0"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=12) as response:
        if response.status not in (200, 201):
            raise ValueError("Discord alert failed")


def main():
    try:
        state = json.loads(STATE_FILE.read_text())
    except (OSError, ValueError):
        state = {}
    vps = request_ok("https://eclipse.style/api/verify")
    chat = vps and request_ok("https://eclipse.style/api/health/chat", True)
    latest = {"vps": vps, "chat": chat}
    for service in ("vps", "chat"):
        if not latest[service] and state.get(service) is not False:
            if service == "chat" and not vps:
                continue
            notify(service)
    state.update(latest)
    state["last_day"] = datetime.now(timezone.utc).date().isoformat()
    STATE_FILE.write_text(json.dumps(state, sort_keys=True) + "\n")
    print("VPS:", "up" if vps else "down", "Chat:", "up" if chat else "down")


if __name__ == "__main__":
    main()
