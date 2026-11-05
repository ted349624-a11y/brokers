"""Keep role display settings in sync. hoist = shown as its own group in the member list."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from setup import call

ROLES = {
    "Team":   {"hoist": True},
    "Mod":    {"hoist": True},
    "WL":     {"hoist": True},
    "Broker": {"hoist": True},
}

gid = call("GET", "/users/@me/guilds")[0]["id"]
for r in call("GET", f"/guilds/{gid}/roles"):
    want = ROLES.get(r["name"])
    if want and any(r.get(k) != v for k, v in want.items()):
        call("PATCH", f"/guilds/{gid}/roles/{r['id']}", want)
        print(f"{r['name']}: updated {want}")
    elif want:
        print(f"{r['name']}: already set")
