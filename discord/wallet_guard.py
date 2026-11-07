"""
Enforce one message per person in #wallet-submit.
Keeps each member's first message that contains a valid wallet, deletes everything else,
and removes Send Messages for members whose wallet is recorded. Prints counts only (public logs).
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from setup import call, base

WALLET = re.compile(r"\b0x[a-fA-F0-9]{40}\b")
SEND = 1 << 11

gid = call("GET", "/users/@me/guilds")[0]["id"]
me = call("GET", "/users/@me")["id"]
owner = call("GET", f"/guilds/{gid}")["owner_id"]
staff = {r["id"] for r in call("GET", f"/guilds/{gid}/roles") if r["name"] in ("Team", "Mod")}
ch = next(c for c in call("GET", f"/guilds/{gid}/channels") if base(c["name"]) == "wallet-submit")
cid = ch["id"]
locked = {o["id"] for o in ch.get("permission_overwrites", []) if o["type"] == 1 and int(o["deny"]) & SEND}

msgs, before = [], None
while True:
    page = call("GET", f"/channels/{cid}/messages?limit=100" + (f"&before={before}" if before else ""))
    if not page:
        break
    msgs += page
    before = page[-1]["id"]
    if len(page) < 100:
        break
msgs.sort(key=lambda m: int(m["id"]))           # oldest first

# Safety: if user messages come back with no text, the bot can't read message content
# (Message Content Intent is off). Never delete anything in that case.
users = [m for m in msgs if not m["author"].get("bot") and m.get("type", 0) in (0, 19)]
if users and all(not m.get("content") and not m.get("attachments") for m in users):
    sys.exit("Message content is unreadable (enable Message Content Intent). Nothing was deleted.")

member_cache = {}
def is_staff(uid):
    if uid == owner: return True
    if uid not in member_cache:
        try: member_cache[uid] = set(call("GET", f"/guilds/{gid}/members/{uid}")["roles"])
        except SystemExit: member_cache[uid] = set()
    return bool(staff & member_cache[uid])

recorded, deleted, newly_locked = set(), 0, 0
for m in msgs:
    uid = m["author"]["id"]
    if m["author"].get("bot") or uid == me or is_staff(uid):
        continue
    if uid not in recorded and WALLET.search(m.get("content", "")):
        recorded.add(uid)
        continue
    call("DELETE", f"/channels/{cid}/messages/{m['id']}")
    deleted += 1

for uid in recorded - locked:
    call("PUT", f"/channels/{cid}/permissions/{uid}", {"type": 1, "allow": "0", "deny": str(SEND)})
    newly_locked += 1

print(f"wallets recorded: {len(recorded)} · extra messages removed: {deleted} · newly locked: {newly_locked}")
