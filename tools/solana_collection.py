"""
Whole-collection downloader for a Solana NFT collection, ranked by trait rarity.
SAMPLE=<one asset/mint of the collection>  TOP=555  python3 tools/solana_collection.py
Supports Metaplex Core collections (enumerated with getProgramAccounts) and prints what it finds.
"""
import os, sys, json, time, base64, struct, re, urllib.request, collections, concurrent.futures as cf
from solders.pubkey import Pubkey
RPC = os.environ.get("SOL_RPC", "https://api.mainnet-beta.solana.com")
SAMPLE = os.environ["SAMPLE"].strip(); TOP = int(os.environ.get("TOP", "555"))
CORE = "CoREENxT6tW1HoK8ypY1SxRMZTcVPm7R94rH4PZNhX7d"
META = Pubkey.from_string("metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s")
os.makedirs("out", exist_ok=True)
def rpc(method, params):
    for i in range(6):
        try:
            req = urllib.request.Request(RPC, data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode(), headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=120) as r: j = json.loads(r.read())
            if "error" in j: raise RuntimeError(j["error"])
            return j["result"]
        except Exception as e:
            print("rpc retry", method, str(e)[:150]); time.sleep(3 + 4 * i)
    raise SystemExit("RPC failed: " + method)
def bstr(b, o):
    n = struct.unpack_from("<I", b, o)[0]; o += 4
    return b[o:o + n].decode("utf-8", "replace").rstrip("\x00").strip(), o + n
def get(url, binary=False):
    last = None
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=60) as r:
                d = r.read(); return (d, r.headers.get("Content-Type", "")) if binary else json.loads(d)
        except Exception as e: last = e; time.sleep(1 + 2 * i)
    raise RuntimeError(str(last)[:100])

acc = rpc("getAccountInfo", [SAMPLE, {"encoding": "base64"}])["value"]
owner = acc["owner"]; print("sample account owner program:", owner)
assets = []   # (id, name, uri)
if owner == CORE:
    b = base64.b64decode(acc["data"][0])
    tag = b[33]
    if tag != 2: raise SystemExit(f"Core asset without collection (update authority tag {tag})")
    coll = str(Pubkey.from_bytes(b[34:66])); print("COLLECTION ADDRESS (Core):", coll)
    cacc = rpc("getAccountInfo", [coll, {"encoding": "base64"}])["value"]
    cb = base64.b64decode(cacc["data"][0]); cname, o = bstr(cb, 1 + 32); print("collection name:", cname)
    import base58
    res = rpc("getProgramAccounts", [CORE, {"encoding": "base64", "filters": [
        {"memcmp": {"offset": 0, "bytes": base58.b58encode(bytes([1])).decode()}},
        {"memcmp": {"offset": 33, "bytes": base58.b58encode(bytes([2])).decode()}},
        {"memcmp": {"offset": 34, "bytes": coll}}]}])
    for a in res:
        d = base64.b64decode(a["account"]["data"][0]); o = 66
        name, o = bstr(d, o); uri, o = bstr(d, o)
        assets.append((a["pubkey"], name, uri))
else:
    pda = str(Pubkey.find_program_address([b"metadata", bytes(META), bytes(Pubkey.from_string(SAMPLE))], META)[0])
    m = base64.b64decode(rpc("getAccountInfo", [pda, {"encoding": "base64"}])["value"]["data"][0])
    print("token-metadata NFT; update authority:", str(Pubkey.from_bytes(m[1:33])))
    raise SystemExit("Token-metadata collections need an indexer; stopping here.")
print("assets in collection:", len(assets))

def meta(a):
    try: return a, get(a[2])
    except Exception as e: return a, None
metas = []
with cf.ThreadPoolExecutor(24) as ex:
    for a, m in ex.map(meta, assets): metas.append((a, m))
good = [(a, m) for a, m in metas if m]
print("metadata fetched:", len(good), "/", len(assets))
# statistical rarity: sum of 1/frequency over every trait type (missing trait counts as "None")
types = sorted({t.get("trait_type") for _, m in good for t in m.get("attributes", []) if isinstance(t, dict)})
print("trait types:", types)
freq = collections.Counter()
def traits(m):
    d = {t.get("trait_type"): str(t.get("value")) for t in m.get("attributes", []) if isinstance(t, dict)}
    return {k: d.get(k, "None") for k in types}
for _, m in good:
    for k, v in traits(m).items(): freq[(k, v)] += 1
N = len(good)
scored = sorted(((sum(N / freq[(k, v)] for k, v in traits(m).items()), a, m) for a, m in good), key=lambda x: -x[0])
top = scored[:TOP]
rows = ["rank,file,name,asset,score,traits,image_url"]
def dl(item):
    rank, (score, a, m) = item
    img = m.get("image") or ""
    try:
        data, ct = get(img, binary=True)
        ext = {"image/png": "png", "image/jpeg": "jpg", "image/gif": "gif", "image/webp": "webp"}.get(ct.split(";")[0], "png")
        num = re.findall(r"\d+", a[1]); fn = f"{rank:03d}-liquid-{num[-1] if num else a[0][:8]}.{ext}"
        open(os.path.join("out", fn), "wb").write(data)
        t = "; ".join(f"{k}: {v}" for k, v in traits(m).items())
        return f'{rank},{fn},"{a[1]}",{a[0]},{score:.2f},"{t}",{img}'
    except Exception as e:
        return None
with cf.ThreadPoolExecutor(16) as ex:
    res = list(ex.map(dl, enumerate(top, 1)))
ok = [r for r in res if r]
open("out/rarity-top.csv", "w").write("\n".join(rows + ok) + "\n")
print(f"downloaded {len(ok)}/{len(top)}; rarest: {top[0][1][1]} score {top[0][0]:.1f}; cutoff #{TOP}: {top[-1][1][1]} score {top[-1][0]:.1f}")
