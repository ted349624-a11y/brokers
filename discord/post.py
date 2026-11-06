"""Post a message as the bot. CHANNEL=x-raids TEXT='...' python3 discord/post.py  (@everyone in TEXT pings everyone)"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from setup import call, base

gid = call("GET", "/users/@me/guilds")[0]["id"]
name = os.environ["CHANNEL"].strip().lstrip("#").lower()
chans = {base(c["name"]): c for c in call("GET", f"/guilds/{gid}/channels") if c["type"] in (0, 5)}
c = chans.get(name)
if not c:
    sys.exit(f"Channel '{name}' not found. Channels: {sorted(chans)}")
text = os.environ["TEXT"].replace("\\n", "\n")
call("POST", f"/channels/{c['id']}/messages", {"content": text, "allowed_mentions": {"parse": ["everyone", "users", "roles"]}})
print(f"Posted in {c['name']}")
