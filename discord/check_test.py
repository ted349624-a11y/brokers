"""Smoke-test the live checker. Prints results only, never wallet addresses (logs are public)."""
import os, re, sys, json, urllib.request
sys.path.insert(0, os.path.dirname(__file__))
from setup import call, base

SITE = "https://www.elysiumbroker.xyz"
def check(w):
    req = urllib.request.Request(f"{SITE}/api/check?wallet={w}", headers={"User-Agent": "eb-smoke-test"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

r = check("0x" + "0" * 39 + "1")
print("random wallet ->", {k: r.get(k) for k in ("ok", "tiers", "partial", "error")})

gid = call("GET", "/users/@me/guilds")[0]["id"]
roles = {r["id"]: r["name"] for r in call("GET", f"/guilds/{gid}/roles")}
ch = next(c for c in call("GET", f"/guilds/{gid}/channels") if base(c["name"]) == "wallet-submit")
msgs = sorted(call("GET", f"/channels/{ch['id']}/messages?limit=100"), key=lambda m: int(m["id"]))
tested = 0
seen = set()
for m in msgs:
    w = re.search(r"\b0x[a-fA-F0-9]{40}\b", m.get("content", ""))
    if m["author"].get("bot") or not w or m["author"]["id"] in seen:
        continue
    seen.add(m["author"]["id"])
    mem = call("GET", f"/guilds/{gid}/members/{m['author']['id']}")
    expected = sorted(n for n in (roles[i] for i in mem["roles"]) if n in ("GTD", "OG"))
    got = check(w.group(0))
    print(f"submitted wallet #{tested + 1}: discord roles {expected} -> checker {got.get('tiers')} partial={got.get('partial')}")
    tested += 1
    if tested >= 3:
        break
print(f"wallets in #wallet-submit tested: {tested}")
