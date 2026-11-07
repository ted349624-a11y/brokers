"""Create #wallet-submit (OG + GTD only), post the instructions, then re-apply permissions and AutoMod."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from setup import call, base, pretty, TIE_RED
import permissions, automod

SLOWMODE = 15 * 60   # backs up the one-message rule between guard runs
gid = call("GET", "/users/@me/guilds")[0]["id"]
allc = call("GET", f"/guilds/{gid}/channels")
cats = {base(c["name"]): c["id"] for c in allc if c["type"] == 4}
chans = {base(c["name"]): c["id"] for c in allc if c["type"] != 4}
if "wallet-submit" in chans:
    cid = chans["wallet-submit"]
    print("Channel exists: #wallet-submit")
else:
    cid = call("POST", f"/guilds/{gid}/channels", {
        "name": pretty("wallet-submit", False), "type": 0, "parent_id": cats.get("gtd lounge"),
        "topic": "OG and GTD: post your EVM wallet address once. One message per person.",
        "rate_limit_per_user": SLOWMODE})["id"]
    print("Channel created: #wallet-submit")
call("PATCH", f"/channels/{cid}", {"rate_limit_per_user": SLOWMODE})

permissions.main()
automod.main()

me = call("GET", "/users/@me")["id"]
if not any(m["author"]["id"] == me for m in call("GET", f"/channels/{cid}/messages?limit=20")):
    m = call("POST", f"/channels/{cid}/messages", {"embeds": [{
        "title": "Submit your wallet",
        "description": ("This channel is for **OG** and **GTD** holders.\n\n"
                        "Post your **EVM wallet address** (0x…) in a single message.\n\n"
                        "• **One message per person.** After your wallet is recorded you can't post here again.\n"
                        "• Only the address, nothing else. Messages without a valid address are removed.\n"
                        "• Double-check it before sending. It can't be changed later.\n\n"
                        "Never share your seed phrase or private key. The team will never DM you first."),
        "color": TIE_RED, "footer": {"text": "Elysium Broker"}}]})
    call("PUT", f"/channels/{cid}/pins/{m['id']}")
    print("Instructions posted and pinned")
