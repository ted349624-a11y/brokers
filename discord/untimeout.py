"""Remove a timeout from a member. Usage: USERNAME=houla9434 python3 discord/untimeout.py"""
import os, sys, urllib.parse
sys.path.insert(0, os.path.dirname(__file__))
from setup import call

name = os.environ.get("USERNAME", "").strip().lstrip("@").lower()
if not name:
    sys.exit("USERNAME is empty.")
gid = call("GET", "/users/@me/guilds")[0]["id"]
hits = call("GET", f"/guilds/{gid}/members/search?limit=10&query=" + urllib.parse.quote(name))
m = next((x for x in hits if x["user"]["username"].lower() == name), None) or (hits[0] if len(hits) == 1 else None)
if not m:
    sys.exit(f"No member found for '{name}'. Found: {[x['user']['username'] for x in hits]}")
u = m["user"]["username"]
until = m.get("communication_disabled_until")
call("PATCH", f"/guilds/{gid}/members/{m['user']['id']}", {"communication_disabled_until": None})
print(f"Timeout removed for {u} (was until {until})" if until else f"{u} had no active timeout; nothing to remove.")
