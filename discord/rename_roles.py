"""Role/channel renames. Safe to run again.
History: Broker -> WL -> GTD (whitelist winners), User -> Broker (verified)."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from setup import call, base, SEP, LINE

gid = call("GET", "/users/@me/guilds")[0]["id"]
roles = {r["name"]: r["id"] for r in call("GET", f"/guilds/{gid}/roles")}
if "WL" in roles and "GTD" not in roles:
    call("PATCH", f"/guilds/{gid}/roles/{roles['WL']}", {"name": "GTD"})
    print("Role renamed: WL -> GTD")
else:
    print("Roles already up to date:", sorted(roles))

NEW = {"broker-lounge": "💎" + SEP + "gtd-lounge", "wl-lounge": "💎" + SEP + "gtd-lounge",
       "broker lounge": "GTD Lounge " + LINE * 10, "wl lounge": "GTD Lounge " + LINE * 10}
for c in call("GET", f"/guilds/{gid}/channels"):
    new = NEW.get(base(c["name"]))
    if new and new != c["name"]:
        call("PATCH", f"/channels/{c['id']}", {"name": new})
        print(f"Channel renamed: {c['name']} -> {new}")
