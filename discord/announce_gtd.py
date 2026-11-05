"""One-off announcement in #announcements: the first GTD winners."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from setup import call, base

gid = call("GET", "/users/@me/guilds")[0]["id"]
gtd = next(r["id"] for r in call("GET", f"/guilds/{gid}/roles") if r["name"] == "GTD")
chans = {base(c["name"]): c["id"] for c in call("GET", f"/guilds/{gid}/channels") if c["type"] != 4}

# winners = members with GTD, earliest join first
import string, urllib.parse
seen = {}
for ch in string.ascii_lowercase + string.digits + "_.":
    for m in call("GET", f"/guilds/{gid}/members/search?limit=1000&query=" + urllib.parse.quote(ch)):
        seen[m["user"]["id"]] = m
winners = sorted((m for m in seen.values() if gtd in m["roles"]), key=lambda m: m["joined_at"])
print(f"Winners: {len(winners)}")

text = (
    "@everyone\n\n"
    "## 🎟️ The first GTD spots are in!\n\n"
    "To thank the earliest members of the Elysium Broker desk, the **first 25 people who joined the server** "
    "have received a **GTD (Guaranteed) whitelist** spot:\n\n"
    + " ".join(f"<@{m['user']['id']}>" for m in winners) + "\n\n"
    f"Congrats, brokers. Your GTD role is live and <#{chans['gtd-lounge']}> is now open for you.\n\n"
    "**Missed it?**\n"
    "• The website whitelist is still open (FCFS): <https://www.elysiumbroker.xyz>\n"
    "• More GTD spots are coming through giveaways, collabs and community activity.\n\n"
    "Follow **@elysiumbroker** on X and turn on notifications so you don't miss the next drop: "
    "<https://x.com/elysiumbroker>"
)
print(len(text))
call("POST", f"/channels/{chans['announcements']}/messages", {
    "content": text,
    "allowed_mentions": {"parse": ["everyone", "users"]},
})
print("Posted in #announcements")
