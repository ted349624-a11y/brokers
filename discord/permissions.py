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
EMBED, ATTACH = 1 << 14, 1 << 15
NO_MEDIA = EMBED | ATTACH          # no link previews, no photos/files
OPEN = {"general", "gm", "memes", "support"}
SKIP = {"broker-lounge", "team-chat", "mod-log"}   # handled by their own role rules


def main():
    gid = call("GET", "/users/@me/guilds")[0]["id"]
    everyone = gid
    # server-wide: @everyone can't attach files or embed links (covers #broker-lounge too)
    role = next(r for r in call("GET", f"/guilds/{gid}/roles") if r["id"] == everyone)
    perms = int(role["permissions"]) & ~NO_MEDIA
    call("PATCH", f"/guilds/{gid}/roles/{everyone}", {"permissions": str(perms)})
    print("@everyone: no photos/files, no link previews")
    for c in call("GET", f"/guilds/{gid}/channels"):
        if c["type"] not in (0, 5, 15):          # text, announcement, forum
            continue
        name = base(c["name"])
        if name in SKIP:
            print(f"Unchanged: #{name}")
            continue
        if name in OPEN:
            allow, deny = VIEW | HISTORY | REACT | SEND, NO_MEDIA
            state = "members can write"
        else:
            allow, deny = VIEW | HISTORY | REACT, NO_WRITE | NO_MEDIA
            state = "read-only"
        call("PUT", f"/channels/{c['id']}/permissions/{everyone}", {"type": 0, "allow": str(allow), "deny": str(deny)})
        print(f"#{name}: {state}")
    print("\nDone.")


if __name__ == "__main__":
    main()
