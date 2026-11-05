"""
Who sees and types where.

- New members (@everyone) see ONLY #verify. They press ✅ and get the Broker role.
- Broker role: sees the server. Can write ONLY in OPEN channels; everything else is read-only.
- #gtd-lounge: GTD role only. Team channels: Team/Mod only.
- Nobody but Team/Mod/owner can post links or photos (AutoMod + no attach/embed rights).
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from setup import call, base, VIEW, SEND, REACT, HISTORY, THREADS_SEND, PUB_THREADS, CONNECT, SPEAK

PRIV_THREADS = 1 << 36
NO_WRITE = SEND | THREADS_SEND | PUB_THREADS | PRIV_THREADS
EMBED, ATTACH = 1 << 14, 1 << 15
NO_MEDIA = EMBED | ATTACH
READ = VIEW | HISTORY | REACT

OPEN = {"general", "gm", "support"}
HIDDEN = {"memes"}
STAFF_ONLY = {"team-chat", "mod-log", "team"}
BROKER_ONLY = {"gtd-lounge", "gtd lounge", "wl-lounge", "wl lounge", "broker-lounge", "broker lounge"}
OG_ONLY = {"og-lounge", "og lounge"}
GATE = "verify"


def ow(i, allow=0, deny=0):
    return {"id": i, "type": 0, "allow": str(allow), "deny": str(deny)}


def main():
    gid = call("GET", "/users/@me/guilds")[0]["id"]
    everyone = gid
    roles = {r["name"]: r for r in call("GET", f"/guilds/{gid}/roles")}
    user = roles.get("Broker", {}).get("id")   # verified members
    if not user:
        sys.exit("Broker role missing. Run 'Discord verify' first.")
    mod, team, broker = roles["Mod"]["id"], roles["Team"]["id"], roles["GTD"]["id"]   # broker = GTD lounge access

    # server-wide: no photos/files, no link previews for members
    ev = roles["@everyone"]
    call("PATCH", f"/guilds/{gid}/roles/{everyone}", {"permissions": str(int(ev["permissions"]) & ~NO_MEDIA)})

    staff = [ow(team, VIEW | SEND | HISTORY), ow(mod, VIEW | SEND | HISTORY)]
    for c in call("GET", f"/guilds/{gid}/channels"):
        name, kind = base(c["name"]), c["type"]
        if name == GATE:
            ows = [ow(everyone, READ, NO_WRITE | NO_MEDIA), ow(user, 0, VIEW)] + staff   # verified users don't need it
            label = "only new members see it"
        elif name in HIDDEN:
            ows = [ow(everyone, 0, VIEW), ow(user, 0, VIEW)] + staff
            label = "hidden"
        elif name in STAFF_ONLY:
            ows = [ow(everyone, 0, VIEW)] + staff
            label = "team only"
        elif name in OG_ONLY:
            og = roles.get("OG", {}).get("id")
            ows = [ow(everyone, 0, VIEW)] + ([ow(og, READ | SEND, NO_MEDIA)] if og else []) + staff
            label = "OG only"
        elif name in BROKER_ONLY:
            ows = [ow(everyone, 0, VIEW), ow(broker, READ | SEND, NO_MEDIA)] + staff
            label = "brokers only"
        elif kind == 2:  # voice
            ows = [ow(everyone, 0, VIEW), ow(user, VIEW | CONNECT | SPEAK)] + staff
            label = "verified users"
        elif kind == 4:  # category
            ows = [ow(everyone, 0, VIEW), ow(user, VIEW)] + staff
            label = "verified users"
        elif name in OPEN:
            ows = [ow(everyone, 0, VIEW), ow(user, READ | SEND, NO_MEDIA)] + staff
            label = "verified users can write"
        else:
            ows = [ow(everyone, 0, VIEW), ow(user, READ, NO_WRITE | NO_MEDIA)] + staff
            label = "verified users, read-only"
        call("PATCH", f"/channels/{c['id']}", {"permission_overwrites": ows})
        print(f"{c['name']}: {label}")
    print("\nDone.")


if __name__ == "__main__":
    main()
