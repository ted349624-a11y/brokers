"""
Download images of NFTs in a Solana wallet whose name/symbol matches a keyword.
Covers SPL Token + Token-2022 NFTs (Metaplex metadata or token-metadata extension) and Metaplex Core assets.
WALLET=... MATCH=liquid python3 tools/solana_nfts.py  -> out/*.png + out/manifest.csv
"""
import os, sys, json, time, base64, struct, re, urllib.request
from solders.pubkey import Pubkey

RPC = os.environ.get("SOL_RPC", "https://api.mainnet-beta.solana.com")
WALLET = os.environ["WALLET"].strip()
MATCH = os.environ.get("MATCH", "liquid").lower()
TOKEN = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
TOKEN22 = "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"
META = Pubkey.from_string("metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s")
CORE = "CoREENxT6tW1HoK8ypY1SxRMZTcVPm7R94rH4PZNhX7d"
os.makedirs("out", exist_ok=True)

def rpc(method, params):
    for i in range(6):
        try:
            req = urllib.request.Request(RPC, data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode(),
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as r:
                j = json.loads(r.read())
            if "error" in j: raise RuntimeError(j["error"])
            return j["result"]
        except Exception as e:
            print("rpc retry", method, str(e)[:120]); time.sleep(2 + 3 * i)
    raise SystemExit("RPC failed")

def borsh_str(b, o):
    n = struct.unpack_from("<I", b, o)[0]; o += 4
    return b[o:o + n].decode("utf-8", "replace").rstrip("\x00").strip(), o + n

items = []   # (mint/asset, name, symbol, uri)

# --- SPL / Token-2022 NFTs
mints = []
for prog in (TOKEN, TOKEN22):
    res = rpc("getTokenAccountsByOwner", [WALLET, {"programId": prog}, {"encoding": "jsonParsed"}])
    for a in res["value"]:
        info = a["account"]["data"]["parsed"]["info"]; amt = info["tokenAmount"]
        if amt["decimals"] == 0 and amt["amount"] == "1":
            mints.append((info["mint"], prog))
print("token NFTs found:", len(mints))
pdas = [str(Pubkey.find_program_address([b"metadata", bytes(META), bytes(Pubkey.from_string(m))], META)[0]) for m, _ in mints]
missing = []
for i in range(0, len(pdas), 100):
    accs = rpc("getMultipleAccounts", [pdas[i:i + 100], {"encoding": "base64"}])["value"]
    for (m, prog), acc in zip(mints[i:i + 100], accs):
        if not acc: missing.append(m); continue
        b = base64.b64decode(acc["data"][0]); o = 1 + 32 + 32
        name, o = borsh_str(b, o); sym, o = borsh_str(b, o); uri, o = borsh_str(b, o)
        items.append((m, name, sym, uri))
for m in missing:   # Token-2022 metadata extension
    acc = rpc("getAccountInfo", [m, {"encoding": "jsonParsed"}])["value"]
    for ext in (acc or {}).get("data", {}).get("parsed", {}).get("info", {}).get("extensions", []) or []:
        if ext.get("extension") == "tokenMetadata":
            s = ext["state"]; items.append((m, s.get("name", ""), s.get("symbol", ""), s.get("uri", "")))

# --- Metaplex Core assets owned by the wallet
try:
    core = rpc("getProgramAccounts", [CORE, {"encoding": "base64", "filters": [{"memcmp": {"offset": 1, "bytes": WALLET}}]}])
    print("core assets found:", len(core))
    for a in core:
        b = base64.b64decode(a["account"]["data"][0])
        if b[0] != 1: continue                       # AssetV1
        o = 1 + 32
        tag = b[o]; o += 1
        if tag in (1, 2): o += 32                    # Address / Collection
        name, o = borsh_str(b, o); uri, o = borsh_str(b, o)
        items.append((a["pubkey"], name, "", uri))
except SystemExit:
    print("core scan skipped (RPC refused getProgramAccounts)")

print("all NFTs with metadata:", len(items))
hits = [x for x in items if MATCH in x[1].lower() or MATCH in x[2].lower()]
print(f"matching '{MATCH}':", len(hits))

GW = ["https://ipfs.io/ipfs/", "https://cloudflare-ipfs.com/ipfs/", "https://gateway.pinata.cloud/ipfs/"]
def fetch(url, binary=False):
    urls = [url]
    if url.startswith("ipfs://"):
        cid = url[7:].replace("ipfs/", ""); urls = [g + cid for g in GW]
    elif url.startswith("ar://"):
        urls = ["https://arweave.net/" + url[5:]]
    last = None
    for u in urls:
        for i in range(3):
            try:
                with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=60) as r:
                    data = r.read(); ct = r.headers.get("Content-Type", "")
                    return (data, ct) if binary else json.loads(data)
            except Exception as e:
                last = e; time.sleep(1 + i)
    raise RuntimeError(str(last)[:120])

rows = ["file,name,mint,image_url"]
ok = 0
for m, name, sym, uri in hits:
    try:
        meta = fetch(uri)
        img = meta.get("image") or (meta.get("properties", {}).get("files") or [{}])[0].get("uri")
        data, ct = fetch(img, binary=True)
        ext = {"image/png": "png", "image/jpeg": "jpg", "image/gif": "gif", "image/webp": "webp", "image/svg+xml": "svg"}.get(ct.split(";")[0], "png")
        num = re.findall(r"\d+", name)
        fn = f"liquids-{num[-1] if num else m[:8]}.{ext}"
        open(os.path.join("out", fn), "wb").write(data)
        rows.append(f'{fn},"{name}",{m},{img}'); ok += 1
        print("saved", fn)
    except Exception as e:
        print("failed", name, str(e)[:100])
open("out/manifest.csv", "w").write("\n".join(rows) + "\n")
print(f"downloaded {ok}/{len(hits)}")
