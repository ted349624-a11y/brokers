"""List members who have a role, earliest join first. ROLE=GTD python3 discord/list_role.py"""
import os, sys, string, urllib.parse
sys.path.insert(0, os.path.dirname(__file__))
from setup import call
gid = call("GET", "/users/@me/guilds")[0]["id"]
rid = next(r["id"] for r in call("GET", f"/guilds/{gid}/roles") if r["name"].lower() == os.environ.get("ROLE", "GTD").lower())
seen = {}
for ch in string.ascii_lowercase + string.digits + "_.":
    for m in call("GET", f"/guilds/{gid}/members/search?limit=1000&query=" + urllib.parse.quote(ch)):
        seen[m["user"]["id"]] = m
ms = sorted((m for m in seen.values() if rid in m["roles"]), key=lambda m: m["joined_at"])
for i, m in enumerate(ms, 1):
    print(f"{i:2}. {m['user']['username']:22} joined {m['joined_at'][:16]}")
