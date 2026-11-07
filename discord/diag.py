"""Diagnose #wallet-submit without printing any wallet or text (logs are public)."""
import os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from setup import call, base
gid = call("GET", "/users/@me/guilds")[0]["id"]
ch = next(c for c in call("GET", f"/guilds/{gid}/channels") if base(c["name"]) == "wallet-submit")
msgs = call("GET", f"/channels/{ch['id']}/messages?limit=100")
print("messages:", len(msgs))
for m in sorted(msgs, key=lambda m: int(m["id"])):
    c = m.get("content", "")
    print(f"bot={m['author'].get('bot', False)} content_len={len(c)} has_wallet={bool(re.search(r'0x[a-fA-F0-9]{40}', c))} embeds={len(m.get('embeds', []))} attachments={len(m.get('attachments', []))}")
