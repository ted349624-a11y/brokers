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

# Order: OG sits directly above Broker, so members who have both show in the OG group.
ABOVE = [("OG", "Broker")]
for top, below in ABOVE:
    rs = sorted((r for r in call("GET", f"/guilds/{gid}/roles") if r["id"] != gid), key=lambda r: r["position"])
    names = [r["name"] for r in rs]
    if top not in names or below not in names:
        continue
    if names.index(top) == names.index(below) + 1:
        print(f"{top} already directly above {below}")
        continue
    moving = rs.pop(names.index(top))
    rs.insert([r["name"] for r in rs].index(below) + 1, moving)
    changes = [{"id": r["id"], "position": i + 1} for i, r in enumerate(rs) if r["position"] != i + 1]
    call("PATCH", f"/guilds/{gid}/roles", changes)
    print(f"Moved {top} directly above {below}")
print("Order (top first):", [r["name"] for r in sorted(call("GET", f"/guilds/{gid}/roles"), key=lambda r: -r["position"])])
