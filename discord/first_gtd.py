"""Give GTD to the first N members who joined (by join time). Skips bots, the owner, Team and Mod."""
import os, sys, string, urllib.parse
sys.path.insert(0, os.path.dirname(__file__))
from setup import call

N = int(os.environ.get("COUNT", "25"))
gid = call("GET", "/users/@me/guilds")[0]["id"]
owner = call("GET", f"/guilds/{gid}")["owner_id"]
roles = {r["name"]: r["id"] for r in call("GET", f"/guilds/{gid}/roles")}
gtd = roles["GTD"]
staff = {roles.get("Team"), roles.get("Mod")}

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
    print("Member list: full list")
except SystemExit:
    for ch in string.ascii_lowercase + string.digits + "_.":
        for m in call("GET", f"/guilds/{gid}/members/search?limit=1000&query=" + urllib.parse.quote(ch)):
            members[m["user"]["id"]] = m
    print("Member list: via search")

people = [m for m in members.values()
          if not m["user"].get("bot") and m["user"]["id"] != owner and not (staff & set(m["roles"]))]
people.sort(key=lambda m: m["joined_at"])
print(f"Eligible members: {len(people)} (skipped bots, owner, Team, Mod)\n")
for i, m in enumerate(people[:N], 1):
    u = m["user"]["username"]
    if gtd in m["roles"]:
        print(f"{i:2}. {u:22} joined {m['joined_at'][:16]}  already GTD")
    else:
        call("PUT", f"/guilds/{gid}/members/{m['user']['id']}/roles/{gtd}")
        print(f"{i:2}. {u:22} joined {m['joined_at'][:16]}  -> GTD")
if len(people) > N:
    nxt = people[N]
    print(f"\nFirst one left out: {nxt['user']['username']} (joined {nxt['joined_at'][:16]})")
