"""
Elysium Broker — Discord AutoMod rules.

Discord enforces these rules itself, 24/7, even when no bot is running.
Run from GitHub Actions ("Discord moderation"). Safe to run again: rules are
updated in place by name.

Team and Mod roles are exempt. Discord also never applies AutoMod to the
server owner or to members with Administrator / Manage Server.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from setup import call, base  # same authenticated Discord client

DAY = 24 * 60 * 60
HERE = os.path.dirname(__file__)


def _lines():
    for line in open(os.path.join(HERE, "banned_words.txt"), encoding="utf-8"):
        w = line.strip()
        if w and not w.startswith("#"):
            yield w


def words():
    return sorted({w.lower() for w in _lines() if not w.startswith("re:")})


def patterns():
    return [w[3:] for w in _lines() if w.startswith("re:")][:10]   # Discord allows 10 per rule


def main():
    guilds = call("GET", "/users/@me/guilds")
    if len(guilds) != 1:
        sys.exit("The bot must be in exactly one server (the Elysium Broker server).")
    gid = guilds[0]["id"]

    roles = {r["name"]: r["id"] for r in call("GET", f"/guilds/{gid}/roles")}
    chans = {base(c["name"]): c["id"] for c in call("GET", f"/guilds/{gid}/channels") if c["type"] != 4}
    exempt = [roles[n] for n in ("Team", "Mod") if n in roles]
    log = chans.get("mod-log")
    if not log:
        sys.exit("#mod-log channel not found. Run 'Discord server setup' first.")

    def block(msg):
        return {"type": 1, "metadata": {"custom_message": msg[:150]}}
    alert = {"type": 2, "metadata": {"channel_id": log}}

    def timeout(sec):
        return {"type": 3, "metadata": {"duration_seconds": sec}}

    rules = [
        {   # the user's priority rule
            "name": "EB · Banned words",
            "trigger_type": 1,
            "trigger_metadata": {"keyword_filter": words(), "regex_patterns": patterns()},
            "actions": [block("Message removed: banned word. You are timed out for 24 hours."),
                        alert, timeout(DAY)],
        },
        {
            "name": "EB · Scam phrases",
            "trigger_type": 1,
            "trigger_metadata": {"keyword_filter": [
                "seed phrase", "secret phrase", "recovery phrase", "private key", "privatekey",
                "wallet connect", "walletconnect", "validate your wallet", "sync your wallet",
                "claim your airdrop", "claim airdrop", "free mint link", "mint is live here",
                "dm me for", "dm for wl", "check your dm", "check dm", "support ticket dm",
                "double your", "guaranteed profit"]},
            "actions": [block("Message removed: this looks like a scam. You are timed out for 24 hours."),
                        alert, timeout(DAY)],
        },
        {   # members can't post links at all; Team and Mod are exempt
            "name": "EB · No links",
            "trigger_type": 1,
            "trigger_metadata": {
                "regex_patterns": [
                    r"https?://",
                    r"\bwww\.",
                    r"discord(?:app)?\.(?:gg|com/invite|io|me|li)/",
                    r"\b[a-z0-9-]{2,}\.(?:com|net|org|io|xyz|gg|app|me|ly|co|fun|link|site|online|club|top|live|pro|vip|shop|art|dev|tv|finance|exchange|network|money)\b",
                ]},
            "actions": [block("Links are not allowed. Official links are in #official-links."), alert],
        },
        {   # wallet addresses in chat: delete only, no timeout
            "name": "EB · Wallet addresses",
            "trigger_type": 1,
            "trigger_metadata": {"regex_patterns": [r"0x[a-f0-9]{40}"]},
            "actions": [block("Don't post wallet addresses in Discord. Submit your wallet on elysiumbroker.xyz."), alert],
        },
        {
            "name": "EB · Mass mentions",
            "trigger_type": 5,
            "trigger_metadata": {"mention_total_limit": 5, "mention_raid_protection_enabled": True},
            "actions": [block("Too many mentions. You are timed out for 24 hours."), alert, timeout(DAY)],
        },
        {
            "name": "EB · Spam",
            "trigger_type": 3,
            "actions": [block("Message removed as spam."), alert],
        },
    ]

    existing = {r["name"]: r for r in call("GET", f"/guilds/{gid}/auto-moderation/rules")}
    RENAMED = {"EB · Invite and shady links": "EB · No links"}
    for o, n in RENAMED.items():
        if o in existing and n not in existing:
            existing[n] = existing.pop(o)
    for r in rules:
        body = {"name": r["name"], "event_type": 1, "trigger_type": r["trigger_type"],
                "actions": r["actions"], "enabled": True, "exempt_roles": exempt}
        if "trigger_metadata" in r:
            body["trigger_metadata"] = r["trigger_metadata"]
        if r["name"] in existing:
            body.pop("trigger_type")  # can't change type on update
            call("PATCH", f"/guilds/{gid}/auto-moderation/rules/{existing[r['name']]['id']}", body)
            print(f"Updated: {r['name']}")
        else:
            # Discord allows only one spam / mention rule per server; skip if a non-EB one exists
            clash = [x for x in existing.values() if x["trigger_type"] == r["trigger_type"] and r["trigger_type"] in (3, 5)]
            if clash:
                print(f"Skipped (server already has one): {r['name']}")
                continue
            call("POST", f"/guilds/{gid}/auto-moderation/rules", body)
            print(f"Created: {r['name']}")

    print(f"\nBanned words active: {len(words())}")
    print("Done. Discord now enforces these rules 24/7. Reports go to #mod-log.")


if __name__ == "__main__":
    main()
