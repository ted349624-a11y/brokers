"""Create the pink OG role + OG Lounge, and give OG to every current (human) member."""
import os, sys, string, urllib.parse
sys.path.insert(0, os.path.dirname(__file__))
from setup import call, base, pretty
import permissions

PINK = 0xFF69B4
gid = call("GET", "/users/@me/guilds")[0]["id"]

roles = {r["name"]: r for r in call("GET", f"/guilds/{gid}/roles")}
if "OG" in roles:
    og = roles["OG"]["id"]
    call("PATCH", f"/guilds/{gid}/roles/{og}", {"color": PINK, "hoist": True})
    print("Role exists: OG (colour set to pink)")
else:
    og = call("POST", f"/guilds/{gid}/roles", {"name": "OG", "color": PINK, "hoist": True, "permissions": "0"})["id"]
    print("Role created: OG (pink)")

allc = call("GET", f"/guilds/{gid}/channels")
cats = {base(c["name"]): c["id"] for c in allc if c["type"] == 4}
chans = {base(c["name"]): c["id"] for c in allc if c["type"] != 4}
cat = cats.get("og lounge") or call("POST", f"/guilds/{gid}/channels", {"name": pretty("og lounge", True), "type": 4})["id"]
if "og-lounge" not in chans:
    call("POST", f"/guilds/{gid}/channels", {"name": pretty("og-lounge", False), "type": 0, "parent_id": cat,
                                              "topic": "For the OGs who were here first."})
    print("Channel created: #og-lounge")

# lock it down before anyone gets the role
permissions.main()

# every current member (humans only)
members = {}
try:
    after = "0"
    while True:
        page = call("GET", f"/guilds/{gid}/members?limit=1000&after={after}")
        if not page:
            break
        for m in page:
            members[m["user"]["id"]] = m
        after = page[-1]["user"]["id"]
        if len(page) < 1000:
            break
except SystemExit:
    # Server Members intent off: fall back to searching every starting character
    for ch in string.ascii_lowercase + string.digits + "_.":
        for m in call("GET", f"/guilds/{gid}/members/search?limit=1000&query=" + urllib.parse.quote(ch)):
            members[m["user"]["id"]] = m

given = 0
for m in members.values():
    if m["user"].get("bot"):
        continue
    if og not in m["roles"]:
        call("PUT", f"/guilds/{gid}/members/{m['user']['id']}/roles/{og}")
        given += 1
        print(f"OG -> {m['user']['username']}")
print(f"\nMembers checked: {len(members)}, OG given: {given}")
