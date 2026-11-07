"""Smoke-test the live mint API from outside: status, RPC reachability per chain, treasury type. Prints no private data."""
import json, urllib.request
SITE = "https://www.elysiumbroker.xyz"
def get(u):
    with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "eb-smoke"}), timeout=40) as r: return json.loads(r.read())
def post(u, b):
    req = urllib.request.Request(u, data=json.dumps(b).encode(), headers={"Content-Type": "text/plain", "User-Agent": "eb-smoke"})
    with urllib.request.urlopen(req, timeout=40) as r: return json.loads(r.read())
s = get(SITE + "/api/mint")
print("status:", {k: s.get(k) for k in ("ok", "open", "supply", "minted", "treasury")}, "start_utc:", s.get("start"))
import secrets
for label, w in (("0x000…0001", "0x" + "0" * 39 + "1"), ("truly random", "0x" + secrets.token_hex(20))):
    p = get(SITE + "/api/mint?wallet=" + w)
    print(f"{label} tier:", p.get("tier"), "lists:", p.get("lists"), "partial:", p.get("partial"))
for ch in ("hyperevm", "ethereum", "base", "arbitrum"):
    r = post(SITE + "/api/mint", {"chain": ch, "tx": "0x" + "0" * 63 + "1"})
    print(f"{ch:9} rpc check ->", r.get("status") or r.get("error"), r.get("message", ""))
RPC = {"hyperevm": "https://rpc.hyperliquid.xyz/evm", "ethereum": "https://ethereum-rpc.publicnode.com",
       "base": "https://mainnet.base.org", "arbitrum": "https://arb1.arbitrum.io/rpc"}
for ch, url in RPC.items():
    req = urllib.request.Request(url, data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "eth_getCode", "params": [s["treasury"], "latest"]}).encode(),
                                 headers={"Content-Type": "application/json", "User-Agent": "eb-smoke"})
    with urllib.request.urlopen(req, timeout=40) as r: code = json.loads(r.read()).get("result")
    print(f"treasury on {ch:9}:", "regular wallet (EOA)" if code in ("0x", None) else f"CONTRACT ({len(code)//2} bytes)")
