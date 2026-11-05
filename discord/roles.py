"""Keep role display settings in sync. hoist = shown as its own group in the member list."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from setup import call

ROLES = {
    "Team":   {"hoist": True},
    "Mod":    {"hoist": True},
    "GTD":    {"hoist": True},
    "Broker": {"hoist": True},
    "OG":     {"hoist": True},
}

gid = call("GET", "/users/@me/guilds")[0]["id"]
for r in call("GET", f"/guilds/{gid}/roles"):
    want = ROLES.get(r["name"])
    if want and any(r.get(k) != v for k, v in want.items()):
        call("PATCH", f"/guilds/{gid}/roles/{r['id']}", want)
        print(f"{r['name']}: updated {want}")
    elif want:
        print(f"{r['name']}: already set")

# Order (bottom to top) for the roles we manage. Positions are set explicitly so ties can't
# leave OG under Broker. Members show in the group of their highest hoisted role.
ORDER = ["Broker", "OG", "GTD", "Mod", "Team"]
allr = call("GET", f"/guilds/{gid}/roles")
byname = {r["name"]: r for r in allr}
for r in allr:
    print(f"  before: {r['name']:15} position {r['position']}")
managed = [byname[n] for n in ORDER if n in byname]
changes = [{"id": r["id"], "position": i + 1} for i, r in enumerate(managed)]
try:
    call("PATCH", f"/guilds/{gid}/roles", changes)
except SystemExit as e:
    print("Could not reorder roles (the bot's own role must be at the top of the list):", e)
print("Order (top first):", [r["name"] for r in sorted(call("GET", f"/guilds/{gid}/roles"), key=lambda r: (-r["position"], r["id"]))])
