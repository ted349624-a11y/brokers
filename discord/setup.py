"""
Elysium Broker — one-shot Discord server setup.

Runs from GitHub Actions (see .github/workflows/discord-setup.yml).
Needs one secret: DISCORD_TOKEN (the bot token). The bot must already be in
exactly one server (the new, empty Elysium Broker server) with Administrator.

Safe to run again: existing roles/channels with the same name are reused,
and the pinned info messages are only posted into empty channels.
"""
import base64, json, os, sys, time, urllib.request, urllib.error

API = "https://discord.com/api/v10"
TOKEN = os.environ.get("DISCORD_TOKEN", "").strip()
SITE = os.environ.get("SITE_URL", "https://www.elysiumbroker.xyz").strip()
X_URL = "https://x.com/elysiumbroker"
TIE_RED = 0xA51C1C

# permission bits
VIEW, SEND, REACT = 1 << 10, 1 << 11, 1 << 6
HISTORY, CONNECT, SPEAK = 1 << 16, 1 << 20, 1 << 21
THREADS_SEND, PUB_THREADS = 1 << 38, 1 << 35
ADMIN = 1 << 3
KICK, BAN, MANAGE_MSG, AUDIT = 1 << 1, 1 << 2, 1 << 13, 1 << 7
NICKS, TIMEOUT = 1 << 27, 1 << 40


# Channels get decorated names ("💬｜general", "The Desk ════"); scripts match on the plain part.
SEP = "｜"   # ｜
LINE = "═"  # ═
def base(name):
    n = name.split(SEP)[-1].split(LINE)[0].strip().lower()
    while n and not (n[0].isalnum()):   # drop a leading emoji like "📈 "
        n = n[1:].lstrip()
    return n

PRETTY = {
    # categories
    "start here": "Start Here " + LINE * 10,
    "the desk": "The Desk " + LINE * 10,
    "broker lounge": "GTD Lounge " + LINE * 10,
    "wl lounge": "GTD Lounge " + LINE * 10,
    "gtd lounge": "GTD Lounge " + LINE * 10,
    "support": None,  # filled below (same word is a channel too)
    "team": "Team " + LINE * 12,
    "voice": "Voice " + LINE * 12,
    # text channels
    "welcome": "👋" + SEP + "welcome",
    "rules": "📜" + SEP + "rules",
    "announcements": "📢" + SEP + "announcements",
    "whitelist": "🎟️" + SEP + "whitelist",
    "official-links": "🔗" + SEP + "official-links",
    "general": "💬" + SEP + "general",
    "gm": "☕" + SEP + "gm",
    "x-raids": "🚀" + SEP + "x-raids",
    "memes": "😂" + SEP + "memes",
    "broker-lounge": "💎" + SEP + "gtd-lounge",
    "wl-lounge": "💎" + SEP + "gtd-lounge",
    "gtd-lounge": "💎" + SEP + "gtd-lounge",
    "team-chat": "🔒" + SEP + "team-chat",
    "mod-log": "🛡️" + SEP + "mod-log",
    "trading floor": "📈 Trading Floor",
    "og lounge": "OG Lounge " + LINE * 10,
    "og-lounge": "🌸" + SEP + "og-lounge",
    "wallet-submit": "👛" + SEP + "wallet-submit",
}
CATEGORY_SUPPORT = "Support " + LINE * 10
CHANNEL_SUPPORT = "🎫" + SEP + "support"


def pretty(name, is_category):
    b = base(name)
    if b == "support":
        return CATEGORY_SUPPORT if is_category else CHANNEL_SUPPORT
    return PRETTY.get(b) or name


def call(method, path, body=None):
    for attempt in range(6):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(API + path, data=data, method=method, headers={
            "Authorization": f"Bot {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "ElysiumBrokerSetup (https://www.elysiumbroker.xyz, 1.0)",
        })
        try:
            with urllib.request.urlopen(req) as r:
                raw = r.read()
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as e:
            txt = e.read().decode(errors="replace")
            if e.code == 429:
                wait = json.loads(txt).get("retry_after", 2)
                time.sleep(float(wait) + 0.3)
                continue
            sys.exit(f"Discord API error {e.code} on {method} {path}: {txt}")
    sys.exit("Rate limited too many times, run the workflow again in a minute.")


def main():
    if not TOKEN:
        sys.exit("DISCORD_TOKEN secret is missing. Add it in GitHub → Settings → Secrets and variables → Actions.")

    guilds = call("GET", "/users/@me/guilds")
    if not guilds:
        sys.exit("The bot is not in any server yet. Open the invite link and add it to your server first.")
    if len(guilds) > 1:
        names = ", ".join(g["name"] for g in guilds)
        sys.exit(f"The bot is in {len(guilds)} servers ({names}). Remove it from all but the Elysium Broker server.")
    gid = guilds[0]["id"]
    print(f"Setting up server: {guilds[0]['name']} ({gid})")

    # ---------- server basics ----------
    icon = base64.b64encode(open(os.path.join(os.path.dirname(__file__), "icon.png"), "rb").read()).decode()
    call("PATCH", f"/guilds/{gid}", {
        "name": "Elysium Broker",
        "icon": "data:image/png;base64," + icon,
        "verification_level": 2,           # members need an account older than 5 minutes
        "explicit_content_filter": 2,      # scan media from everyone
        "default_message_notifications": 1 # mentions only
    })
    print("Server name, icon and safety settings updated")

    # ---------- roles ----------
    existing = {r["name"]: r for r in call("GET", f"/guilds/{gid}/roles")}
    everyone = gid  # @everyone role id == guild id

    def role(name, color=0, perms=0, hoist=False):
        if name in existing:
            print(f"Role exists: {name}")
            return existing[name]["id"]
        r = call("POST", f"/guilds/{gid}/roles", {
            "name": name, "color": color, "permissions": str(perms), "hoist": hoist, "mentionable": False})
        print(f"Role created: {name}")
        return r["id"]

    team = role("Team", 0xF2F1EF, ADMIN, hoist=True)
    mod = role("Mod", 0x8A8986, KICK | BAN | MANAGE_MSG | AUDIT | NICKS | TIMEOUT, hoist=True)
    broker = role("GTD", TIE_RED, 0, hoist=True)  # guaranteed whitelist winners

    # ---------- channels ----------
    allc = call("GET", f"/guilds/{gid}/channels")
    chans = {base(c["name"]): c for c in allc if c["type"] != 4}
    cats = {base(c["name"]): c for c in allc if c["type"] == 4}

    def ow(target, allow=0, deny=0):
        return {"id": target, "type": 0, "allow": str(allow), "deny": str(deny)}

    read_only = [ow(everyone, VIEW | HISTORY | REACT, SEND | PUB_THREADS | THREADS_SEND),
                 ow(team, VIEW | SEND), ow(mod, VIEW | SEND)]
    open_chat = [ow(everyone, VIEW | SEND | HISTORY | REACT)]
    team_only = [ow(everyone, 0, VIEW), ow(team, VIEW | SEND | HISTORY), ow(mod, VIEW | SEND | HISTORY)]
    broker_only = [ow(everyone, 0, VIEW), ow(broker, VIEW | SEND | HISTORY | REACT),
                   ow(team, VIEW | SEND), ow(mod, VIEW | SEND)]

    def category(name, overwrites=None):
        if base(name) in cats:
            return cats[base(name)]["id"]
        c = call("POST", f"/guilds/{gid}/channels", {"name": pretty(name, True), "type": 4,
                                                      "permission_overwrites": overwrites or []})
        print(f"Category created: {name}")
        return c["id"]

    def channel(name, parent, overwrites, topic="", kind=0, slowmode=0):
        if base(name) in chans:
            print(f"Channel exists: #{name}")
            return chans[base(name)]["id"], False
        body = {"name": pretty(name, False), "type": kind, "parent_id": parent, "permission_overwrites": overwrites}
        if kind == 0:
            body["topic"] = topic
            body["rate_limit_per_user"] = slowmode
        c = call("POST", f"/guilds/{gid}/channels", body)
        print(f"Channel created: #{name}")
        return c["id"], True

    start = category("START HERE")
    welcome, new_w = channel("welcome", start, read_only, "Welcome to the Elysium Broker desk.")
    rules, new_r = channel("rules", start, read_only, "Read before you trade.")
    ann, new_a = channel("announcements", start, read_only, "Official news only.")
    wl, new_wl = channel("whitelist", start, read_only, f"Apply at {SITE}")
    links, new_l = channel("official-links", start, read_only, "The only links we will ever share.")

    comm = category("THE DESK")
    channel("general", comm, open_chat, "Talk Elysium, Hyperliquid and brokers.", slowmode=3)
    channel("gm", comm, open_chat, "gm brokers.", slowmode=10)
    channel("x-raids", comm, open_chat, "Share our posts on X and support them.", slowmode=30)

    vip = category("GTD LOUNGE", [ow(everyone, 0, VIEW), ow(broker, VIEW), ow(team, VIEW), ow(mod, VIEW)])
    channel("gtd-lounge", vip, broker_only, "GTD whitelist holders only.")

    sup = category("SUPPORT")
    channel("support", sup, open_chat, "Questions about the whitelist or mint. The team will never DM you first.",
            slowmode=15)

    staff = category("TEAM", [ow(everyone, 0, VIEW), ow(team, VIEW), ow(mod, VIEW)])
    channel("team-chat", staff, team_only, "Private.")
    channel("mod-log", staff, team_only, "Moderation notes.")

    voice = category("VOICE")
    channel("Trading Floor", voice,
            [ow(everyone, VIEW | CONNECT | SPEAK)], kind=2)

    # ---------- info messages (only into freshly created channels) ----------
    def embed(cid, title, desc, fields=None):
        call("POST", f"/channels/{cid}/messages", {"embeds": [{
            "title": title, "description": desc, "color": TIE_RED,
            "fields": fields or [], "footer": {"text": "Elysium Broker"}}]})

    if new_w:
        embed(welcome, "Welcome to the desk",
              "Elysium Broker is an NFT collection built on **Elysium**, Kinetiq's 100ms L2 for Hyperliquid.\n\n"
              f"1. Read <#{rules}>\n2. Apply for the whitelist in <#{wl}>\n3. Say gm in the desk")
    if new_r:
        embed(rules, "Rules",
              "**1.** Respect everyone. No hate, harassment or spam.\n"
              "**2.** No self-promotion or links to other projects.\n"
              "**3.** The team will **never** DM you first, ask for your seed phrase or send you a mint link in DMs.\n"
              "**4.** Only trust links posted in "
              f"<#{links}>.\n"
              "**5.** English in the main channels.\n"
              "**6.** Mods have the final word.\n\n"
              "Breaking a rule can get you muted or banned without warning.")
    if new_wl:
        embed(wl, "Whitelist is open",
              f"Apply here: **{SITE}**\n\n"
              "Complete five quick tasks on X (follow, like, repost, notifications, your own comment), "
              "submit your EVM wallet, and get your personal broker pass.\n\n"
              "One entry per wallet and per X account. Bot or copy-paste comments are removed.")
    if new_l:
        embed(links, "Official links",
              "These are the only official links.",
              [{"name": "Website", "value": SITE, "inline": False},
               {"name": "X", "value": X_URL, "inline": False}])
    if new_a:
        embed(ann, "Elysium Broker", f"The desk is open. Whitelist: {SITE}")

    print("\nDone. Your server is ready.")
    print("Give yourself the Team role, and give GTD winners the GTD role.")


if __name__ == "__main__":
    main()
