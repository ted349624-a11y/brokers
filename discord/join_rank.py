"""Where did a member land in the join order? USERNAME=someone python3 discord/join_rank.py"""
import os, sys, string, urllib.parse
sys.path.insert(0, os.path.dirname(__file__))
from setup import call
name = os.environ.get("USERNAME", "").strip().lstrip("@").lower()
gid = call("GET", "/users/@me/guilds")[0]["id"]
owner = call("GET", f"/guilds/{gid}")["owner_id"]
staff = {r["id"] for r in call("GET", f"/guilds/{gid}/roles") if r["name"] in ("Team", "Mod")}
seen = {}
for ch in string.ascii_lowercase + string.digits + "_.":
    for m in call("GET", f"/guilds/{gid}/members/search?limit=1000&query=" + urllib.parse.quote(ch)):
        seen[m["user"]["id"]] = m
people = sorted((m for m in seen.values() if not m["user"].get("bot") and m["user"]["id"] != owner
                 and not (staff & set(m["roles"]))), key=lambda m: m["joined_at"])
for i, m in enumerate(people, 1):
    if m["user"]["username"].lower() == name:
        print(f"RESULT {m['user']['username']}: #{i} of {len(people)}, joined {m['joined_at']}")
        for j in range(max(0, i - 3), min(len(people), i + 2)):
            p = people[j]
            print(f"  #{j+1:<3} {p['user']['username']:22} {p['joined_at'][:19]}")
        break
else:
    print(f"RESULT no member named {name}")
