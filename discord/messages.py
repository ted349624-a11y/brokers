"""Keep the info posts in channels up to date. Edits the bot's existing post, or posts it if missing."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from setup import call, base, TIE_RED, SITE

X = "https://x.com/elysiumbroker"

POSTS = {
    "whitelist": {
        "title": "Whitelist is open",
        "description": (
            f"**Apply here:** {SITE}\n\n"
            "**Website whitelist is FCFS**\n"
            "Spots from the website are **First Come, First Served**. Your spot gets you into the "
            "whitelist mint phase, but it does not guarantee a mint. When the supply runs out, it's gone, "
            "so be early on mint day.\n\n"
            "**Want a GTD spot?**\n"
            "**Guaranteed (GTD)** whitelist spots will be given out through giveaways, collabs and "
            "community activity. Turn on notifications for "
            f"[@elysiumbroker]({X}) on X and keep an eye on the announcements channel so you don't miss them.\n\n"
            "**How to apply**\n"
            "1. Complete five quick tasks on X: follow, like, repost, turn on notifications and leave your own comment.\n"
            "2. Submit your X username and EVM wallet.\n"
            "3. Get your personal broker pass.\n\n"
            "One entry per wallet and per X account. Bot or copy-paste comments are removed."
        ),
    },
}


def main():
    gid = call("GET", "/users/@me/guilds")[0]["id"]
    me = call("GET", "/users/@me")["id"]
    chans = {base(c["name"]): c["id"] for c in call("GET", f"/guilds/{gid}/channels") if c["type"] != 4}
    for key, post in POSTS.items():
        cid = chans.get(key)
        if not cid:
            print(f"#{key} not found, skipped")
            continue
        embed = {**post, "color": TIE_RED, "footer": {"text": "Elysium Broker"}}
        mine = [m for m in call("GET", f"/channels/{cid}/messages?limit=50")
                if m["author"]["id"] == me and m.get("embeds")]
        if mine:
            call("PATCH", f"/channels/{cid}/messages/{mine[-1]['id']}", {"embeds": [embed]})
            print(f"#{key}: message updated")
        else:
            call("POST", f"/channels/{cid}/messages", {"embeds": [embed]})
            print(f"#{key}: message posted")


if __name__ == "__main__":
    main()
