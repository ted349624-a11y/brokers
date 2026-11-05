"""Give a role to a member. Usage: USERNAME=houla9434 ROLE=Team python3 discord/add_role.py"""
import os, sys, urllib.parse
sys.path.insert(0, os.path.dirname(__file__))
from setup import call

name = os.environ.get("USERNAME", "").strip().lstrip("@").lower()
role_name = os.environ.get("ROLE", "").strip()
gid = call("GET", "/users/@me/guilds")[0]["id"]
role = next((r for r in call("GET", f"/guilds/{gid}/roles") if r["name"].lower() == role_name.lower()), None)
if not role:
    sys.exit(f"Role '{role_name}' not found.")
hits = call("GET", f"/guilds/{gid}/members/search?limit=10&query=" + urllib.parse.quote(name))
m = next((x for x in hits if x["user"]["username"].lower() == name), None)
if not m:
    sys.exit(f"No member named '{name}'. Found: {[x['user']['username'] for x in hits]}")
if role["id"] in m["roles"]:
    print(f"{m['user']['username']} already has {role['name']}")
else:
    call("PUT", f"/guilds/{gid}/members/{m['user']['id']}/roles/{role['id']}")
    print(f"Gave {role['name']} to {m['user']['username']}")
