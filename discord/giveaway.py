"""
Reaction giveaways in #announcements.

MODE=start PRIZE="GTD" WINNERS=25 HOURS=24  -> posts the giveaway and adds 🎉
MODE=draw                                   -> draws every giveaway whose time is up (run every 10 min)

Valid entries: reacted 🎉, still in the server, verified (Broker role), not already holding the prize role,
not a bot / the owner / Team / Mod. Winners are drawn with a cryptographically secure RNG.
"""
import os, sys, time, random, urllib.parse
sys.path.insert(0, os.path.dirname(__file__))
from setup import call, base, TIE_RED

EMOJI = "🎉"
TAG = "EB-GIVEAWAY"
gid = call("GET", "/users/@me/guilds")[0]["id"]
me = call("GET", "/users/@me")["id"]
roles = {r["name"]: r["id"] for r in call("GET", f"/guilds/{gid}/roles")}
chans = {base(c["name"]): c["id"] for c in call("GET", f"/guilds/{gid}/channels") if c["type"] != 4}
cid = chans["announcements"]


def start():
    prize = os.environ.get("PRIZE", "GTD").strip()
    n = int(os.environ.get("WINNERS", "25"))
    end = int(time.time() + float(os.environ.get("HOURS", "24")) * 3600)
    embed = {
        "title": f"{EMOJI} GIVEAWAY: {n}× {prize} Whitelist",
        "description": (f"React with {EMOJI} below to enter.\n\n"
                        f"**Prize:** {n}× {prize} whitelist spot{'s' if n > 1 else ''}\n"
                        f"**Ends:** <t:{end}:F> (<t:{end}:R>)\n\n"
                        "**Rules**\n"
                        "• You must be verified (Broker role)\n"
                        f"• Members who already have {prize} can't win again\n"
                        "• One entry per person, winners are picked at random by the bot\n"
                        f"• Winners get the {prize} role automatically"),
        "color": TIE_RED,
        "footer": {"text": f"{TAG}|{end}|{n}|{prize}"},
    }
    m = call("POST", f"/channels/{cid}/messages", {"content": "@everyone", "embeds": [embed],
                                                   "allowed_mentions": {"parse": ["everyone"]}})
    call("PUT", f"/channels/{cid}/messages/{m['id']}/reactions/{urllib.parse.quote(EMOJI)}/@me")
    print(f"Giveaway started: {n}x {prize}, ends {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime(end))}, message {m['id']}")


def reactors(mid):
    users, after = [], "0"
    while True:
        page = call("GET", f"/channels/{cid}/messages/{mid}/reactions/{urllib.parse.quote(EMOJI)}?limit=100&after={after}")
        if not page:
            return users
        users += page
        after = page[-1]["id"]
        if len(page) < 100:
            return users


def draw():
    owner = call("GET", f"/guilds/{gid}")["owner_id"]
    staff = {roles.get("Team"), roles.get("Mod")}
    now = time.time()
    found = False
    for m in call("GET", f"/channels/{cid}/messages?limit=100"):
        if m["author"]["id"] != me or not m.get("embeds"):
            continue
        foot = (m["embeds"][0].get("footer") or {}).get("text", "")
        if not foot.startswith(TAG + "|"):
            continue
        _, end, n, prize = foot.split("|", 3)
        if now < int(end):
            print(f"Giveaway {m['id']} still running ({int(int(end) - now) // 60} min left)")
            continue
        found = True
        prize_role = roles.get(prize)
        valid = []
        for u in reactors(m["id"]):
            if u.get("bot") or u["id"] == owner:
                continue
            try:
                mem = call("GET", f"/guilds/{gid}/members/{u['id']}")
            except SystemExit:
                continue  # left the server
            r = set(mem["roles"])
            if roles.get("Broker") not in r or (staff & r) or (prize_role and prize_role in r):
                continue
            valid.append(u)
        winners = random.SystemRandom().sample(valid, min(int(n), len(valid)))
        print(f"Giveaway {m['id']}: {len(valid)} valid entries, {len(winners)} winners")
        for w in winners:
            if prize_role:
                call("PUT", f"/guilds/{gid}/members/{w['id']}/roles/{prize_role}")
            print(f"  winner: {w['username']}")
        mentions = " ".join(f"<@{w['id']}>" for w in winners) or "No valid entries."
        call("POST", f"/channels/{cid}/messages", {
            "content": f"{EMOJI} **Giveaway ended: {n}× {prize} Whitelist**\n\n"
                       f"Congrats to the winners! Your {prize} role has been added.\n\n{mentions}\n\n"
                       f"Valid entries: {len(valid)}. Winners were drawn at random by the bot.",
            "message_reference": {"message_id": m["id"]},
            "allowed_mentions": {"parse": ["users"]}})
        e = m["embeds"][0]
        e["title"] = f"{EMOJI} GIVEAWAY ENDED: {n}× {prize} Whitelist"
        e["footer"] = {"text": f"Ended · {len(valid)} valid entries · {len(winners)} winners"}
        e["color"] = 0x555555
        call("PATCH", f"/channels/{cid}/messages/{m['id']}", {"embeds": [e]})
    if not found:
        print("Nothing to draw.")


(start if os.environ.get("MODE") == "start" else draw)()
