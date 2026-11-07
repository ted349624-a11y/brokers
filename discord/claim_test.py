"""Live test of /api/claim: compares the API with balanceOf read directly from HyperEVM. Prints no addresses."""
import json, urllib.request
CA = "0xa84F624482246fa94A1D787FF36dcfBC5F1514a7"; RPC = "https://rpc.hyperliquid.xyz/evm"; SITE = "https://www.elysiumbroker.xyz"
def rpc(m, p):
    req = urllib.request.Request(RPC, data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": m, "params": p}).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r: return json.loads(r.read()).get("result")
def api(w):
    with urllib.request.urlopen(urllib.request.Request(f"{SITE}/api/claim?wallet={w}", headers={"User-Agent": "eb"}), timeout=30) as r: return json.loads(r.read())
print("random wallet ->", api("0x" + "0" * 39 + "7"))
for tid in (1, 2, 3):
    o = rpc("eth_call", [{"to": CA, "data": "0x6352211e" + hex(tid)[2:].rjust(64, "0")}, "latest"])
    if not o or o == "0x": print(f"token {tid}: no owner"); continue
    owner = "0x" + o[-40:]
    bal = int(rpc("eth_call", [{"to": CA, "data": "0x70a08231" + owner[2:].rjust(64, "0")}, "latest"]), 16)
    a = api(owner)
    print(f"holder of token {tid}: chain balance {bal} -> api held {a.get('held')} allocation {a.get('allocation'):,}")
