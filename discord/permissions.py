"""
Who can type where. Members can write ONLY in the channels listed in OPEN.
Every other text channel is read-only for members (they can still read and react).
#broker-lounge stays writable for the Broker role (only Brokers can see it).
Team (admin), Mod and the server owner can always post.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from setup import call, base, VIEW, SEND, REACT, HISTORY, THREADS_SEND, PUB_THREADS

PRIV_THREADS = 1 << 36
NO_WRITE = SEND | THREADS_SEND | PUB_THREADS | PRIV_THREADS
OPEN = {"general", "gm", "memes", "support"}
SKIP = {"broker-lounge", "team-chat", "mod-log"}   # handled by their own role rules


def main():
    gid = call("GET", "/users/@me/guilds")[0]["id"]
    everyone = gid
    for c in call("GET", f"/guilds/{gid}/channels"):
        if c["type"] not in (0, 5, 15):          # text, announcement, forum
            continue
        name = base(c["name"])
        if name in SKIP:
            print(f"Unchanged: #{name}")
            continue
        if name in OPEN:
            allow, deny = VIEW | HISTORY | REACT | SEND, 0
            state = "members can write"
        else:
            allow, deny = VIEW | HISTORY | REACT, NO_WRITE
            state = "read-only"
        call("PUT", f"/channels/{c['id']}/permissions/{everyone}", {"type": 0, "allow": str(allow), "deny": str(deny)})
        print(f"#{name}: {state}")
    print("\nDone.")


if __name__ == "__main__":
    main()
