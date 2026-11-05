"""One-off: Broker -> WL, then User -> Broker. Also renames the lounge to WL Lounge."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from setup import call, base, SEP, LINE

gid = call("GET", "/users/@me/guilds")[0]["id"]
roles = {r["name"]: r["id"] for r in call("GET", f"/guilds/{gid}/roles")}
if "User" in roles and "Broker" in roles and "WL" not in roles:
    call("PATCH", f"/guilds/{gid}/roles/{roles['Broker']}", {"name": "WL"})
    print("Role renamed: Broker -> WL")
    call("PATCH", f"/guilds/{gid}/roles/{roles['User']}", {"name": "Broker"})
    print("Role renamed: User -> Broker")
else:
    print("Roles already renamed:", sorted(roles))

for c in call("GET", f"/guilds/{gid}/channels"):
    b = base(c["name"])
    new = {"broker-lounge": "💎" + SEP + "wl-lounge", "broker lounge": "WL Lounge " + LINE * 10}.get(b)
    if new:
        call("PATCH", f"/channels/{c['id']}", {"name": new})
        print(f"Channel renamed: {c['name']} -> {new}")
