"""Find which chain the NFT contract lives on and read basic info."""
import json, urllib.request
CA = "0xa84F624482246fa94A1D787FF36dcfBC5F1514a7"
RPC = {"hyperevm": "https://rpc.hyperliquid.xyz/evm", "ethereum": "https://ethereum-rpc.publicnode.com",
       "base": "https://mainnet.base.org", "arbitrum": "https://arb1.arbitrum.io/rpc",
       "optimism": "https://mainnet.optimism.io", "polygon": "https://polygon-rpc.com", "abstract": "https://api.mainnet.abs.xyz",
       "apechain": "https://rpc.apechain.com", "zora": "https://rpc.zora.energy", "blast": "https://rpc.blast.io",
       "bsc": "https://bsc-dataseed.binance.org", "avalanche": "https://api.avax.network/ext/bc/C/rpc", "shape": "https://mainnet.shape.network",
       "monad": "https://rpc.monad.xyz", "sei": "https://evm-rpc.sei-apis.com", "unichain": "https://mainnet.unichain.org",
       "ink": "https://rpc-gel.inkonchain.com", "soneium": "https://rpc.soneium.org", "berachain": "https://rpc.berachain.com"}
def call(url, method, params):
    req = urllib.request.Request(url, data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode(),
                                 headers={"Content-Type": "application/json", "User-Agent": "eb-probe"})
    with urllib.request.urlopen(req, timeout=20) as r: return json.loads(r.read()).get("result")
def dec_str(h):
    try:
        b = bytes.fromhex(h[2:]); n = int.from_bytes(b[32:64], "big"); return b[64:64 + n].decode()
    except Exception: return "?"
for ch, url in RPC.items():
    try:
        code = call(url, "eth_getCode", [CA, "latest"])
        if code and code != "0x":
            name = dec_str(call(url, "eth_call", [{"to": CA, "data": "0x06fdde03"}, "latest"]) or "0x")
            ts = call(url, "eth_call", [{"to": CA, "data": "0x18160ddd"}, "latest"])
            i721 = call(url, "eth_call", [{"to": CA, "data": "0x01ffc9a780ac58cd" + "0" * 56}, "latest"])
            i1155 = call(url, "eth_call", [{"to": CA, "data": "0x01ffc9a7d9b67a26" + "0" * 56}, "latest"])
            print(f"FOUND on {ch}: name={name} totalSupply={int(ts,16) if ts and ts!='0x' else '?'} erc721={i721 and int(i721,16)==1} erc1155={i1155 and int(i1155,16)==1}")
        else:
            print(f"{ch}: no contract")
    except Exception as e:
        print(f"{ch}: error {str(e)[:60]}")
